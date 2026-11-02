"""API REST de SaludCerca (ASGI / Starlette).

La misma aplicación corre:
  - en Azure Functions, envuelta por `func.AsgiFunctionApp` (ver function_app.py);
  - en local, con uvicorn (ver dev_server.py).
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from pydantic import BaseModel, ValidationError
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from datetime import date, timedelta

from . import fhir, integrations
from .agenda import HORIZONTE_DIAS, es_turno_libre, turnos_libres
from .auth import AuthError, exigir_rol, usuario_actual
from .cifrado import Cifrador, build_cifrador
from .config import Settings, get_settings
from .historial import guardar_nota, leer_notas
from .messaging import LIMA, Publisher, build_notifier, build_publisher, publicar_cita_creada
from .models import (
    ESPECIALIDADES, Agenda, AgendaIn, PerfilIn, Cita, CitaIn, DocumentoIn, EstadoCita, EstadoSolicitud, MedicoIn, NotaClinica, NotaIn,
    Rol, SolicitudAviso, SolicitudAvisoIn, Usuario, new_id, now_utc,
)
from .repository import Repository, build_repository
from .seed import cargar_demo

log = logging.getLogger("saludcerca.api")
audit = logging.getLogger("saludcerca.audit")


@dataclass
class Services:
    settings: Settings
    repo: Repository
    publisher: Publisher
    cifrador: Cifrador


def _json(data, status: int = 200) -> JSONResponse:
    if isinstance(data, BaseModel):
        data = data.model_dump(mode="json")
    elif isinstance(data, list):
        data = [d.model_dump(mode="json") if isinstance(d, BaseModel) else d for d in data]
    return JSONResponse(data, status_code=status, headers={"Cache-Control": "private, no-store"})


async def _body(request: Request, model: type[BaseModel]) -> BaseModel:
    try:
        raw = await request.json()
    except json.JSONDecodeError as exc:
        raise AuthError(400, "El cuerpo debe ser JSON válido") from exc
    return model.model_validate(raw)


def _ip(request: Request) -> str | None:
    reenviada = request.headers.get("x-forwarded-for")  # la agrega Front Door / la plataforma de Functions
    if reenviada:
        return reenviada.split(",")[0].strip()
    return request.client.host if request.client else None


def _audit(request: Request, accion: str, usuario: Usuario | None, paciente_id: str, **extra) -> None:
    audit.info(json.dumps({"accion": accion, "usuario": usuario.id if usuario else None,
                           "rol": usuario.rol.value if usuario else "integracion", "paciente": paciente_id,
                           "ip": _ip(request), **extra}, ensure_ascii=False))


def _puede_ver_paciente(svc: Services, usuario: Usuario, paciente_id: str) -> bool:
    if usuario.rol == Rol.admin:
        return False  # la coordinación ve citas y avisos, no historias clínicas
    if usuario.rol == Rol.paciente:
        return usuario.id == paciente_id
    # un médico solo accede a pacientes con los que tiene una cita asignada
    return any(c.medico_id == usuario.id for c in svc.repo.list_citas(paciente_id=paciente_id))


def _cita_con_nombres(svc: Services, c: Cita) -> dict:
    d = c.model_dump(mode="json")
    pac, med = svc.repo.get_usuario(c.paciente_id), svc.repo.get_usuario(c.medico_id)
    d["paciente_nombre"] = pac.nombre if pac else None
    d["medico_nombre"] = med.nombre if med else None
    d["establecimiento"] = pac.establecimiento if pac else None
    return d


def create_app(settings: Settings | None = None, repo: Repository | None = None) -> Starlette:
    settings = settings or get_settings()
    repo = repo or build_repository(settings)
    notifier = build_notifier(settings)
    cifrador = build_cifrador(settings.record_enc_key, settings.es_local)
    svc = Services(settings, repo, build_publisher(settings, repo, notifier), cifrador)
    if settings.seed_demo_data and (settings.storage_backend == "memory" or settings.cosmos_key):
        cargar_demo(repo, cifrador)  # nunca en Azure: allí no hay COSMOS_KEY

    def handler(fn):
        async def wrapped(request: Request):
            try:
                user = usuario_actual(request, settings, repo)
                return await fn(request, user)
            except AuthError as e:
                return JSONResponse({"error": e.detail}, status_code=e.status)
            except ValidationError as e:
                errores = [{"campo": ".".join(map(str, err["loc"])), "mensaje": err["msg"]} for err in e.errors()]
                return JSONResponse({"error": "Datos inválidos", "detalle": errores}, status_code=422)
        return wrapped

    # ---------- públicos ----------
    async def health(request: Request):
        return JSONResponse({"estado": "ok", "auth": settings.auth_mode, "datos": settings.storage_backend,
                             "mensajeria": settings.messaging_backend, "avisos": settings.notifier_backend})

    async def dev_usuarios(request: Request):
        if not settings.es_local:  # lista de usuarios ficticios: nunca en Azure
            return JSONResponse({"error": "No disponible"}, status_code=404)
        return _json(repo.list_usuarios())

    # ---------- autenticados ----------
    @handler
    async def me(request: Request, user: Usuario):
        return _json(user)

    def _medicos(especialidad: str | None = None) -> list[Usuario]:
        meds = repo.list_usuarios(Rol.medico)
        if especialidad:
            meds = [m for m in meds if (m.especialidad or "").lower() == especialidad.lower()]
        return sorted(meds, key=lambda m: m.nombre)

    @handler
    async def actualizar_me(request: Request, user: Usuario):
        data: PerfilIn = await _body(request, PerfilIn)
        actualizado = user.model_copy(update=data.model_dump())
        repo.upsert_usuario(actualizado)
        log.info("datos de contacto actualizados por %s (avisos por %s)", user.id, data.canal_preferido.value)
        return _json(actualizado)

    @handler
    async def medicos(request: Request, user: Usuario):
        res = []
        for m in _medicos(request.query_params.get("especialidad")):
            d = m.model_dump(mode="json")
            ag = repo.get_agenda(m.id)
            d["tiene_horario"] = bool(ag and ag.bloques)
            d["duracion_min"] = ag.duracion_min if ag else None
            res.append(d)
        return _json(res)

    @handler
    async def especialidades(request: Request, user: Usuario):
        conteo = {e: 0 for e in ESPECIALIDADES}
        for m in _medicos():
            if m.especialidad:
                conteo[m.especialidad] = conteo.get(m.especialidad, 0) + 1
        return _json([{"especialidad": e, "medicos": n} for e, n in sorted(conteo.items())])

    def _publicar_disponibilidad(especialidad: str | None) -> None:
        if especialidad:
            svc.publisher.publish({"tipo": "disponibilidad", "especialidad": especialidad, "id": new_id()})

    def _hay_turnos(especialidad: str, medico_id: str | None) -> bool:
        hoy = now_utc().astimezone(LIMA).date()
        for m in _medicos(especialidad):
            if medico_id and m.id != medico_id:
                continue
            ag = repo.get_agenda(m.id)
            if ag and turnos_libres(ag, repo.list_citas(medico_id=m.id), hoy, 14):
                return True
        return False

    @handler
    async def crear_solicitud(request: Request, user: Usuario):
        exigir_rol(user, Rol.paciente)
        data: SolicitudAvisoIn = await _body(request, SolicitudAvisoIn)
        if _hay_turnos(data.especialidad, data.medico_id):
            raise AuthError(409, "Ya hay turnos disponibles: puede reservar ahora mismo")
        for s in repo.list_solicitudes(paciente_id=user.id, especialidad=data.especialidad, estado=EstadoSolicitud.activa):
            if s.medico_id == data.medico_id:
                return _json(s)  # ya estaba suscrito
        s = repo.save_solicitud(SolicitudAviso(paciente_id=user.id, especialidad=data.especialidad, medico_id=data.medico_id))
        return _json(s, 201)

    @handler
    async def mis_solicitudes(request: Request, user: Usuario):
        if user.rol == Rol.admin:  # demanda insatisfecha por especialidad (sin datos personales)
            conteo: dict[str, int] = {}
            for s in repo.list_solicitudes(estado=EstadoSolicitud.activa):
                conteo[s.especialidad] = conteo.get(s.especialidad, 0) + 1
            return _json([{"especialidad": e, "pendientes": n} for e, n in sorted(conteo.items(), key=lambda x: -x[1])])
        exigir_rol(user, Rol.paciente)
        res = []
        for s in repo.list_solicitudes(paciente_id=user.id):
            if s.estado == EstadoSolicitud.cancelada:
                continue
            d = s.model_dump(mode="json")
            med = repo.get_usuario(s.medico_id) if s.medico_id else None
            d["medico_nombre"] = med.nombre if med else None
            res.append(d)
        return _json(list(reversed(res)))

    @handler
    async def cancelar_solicitud(request: Request, user: Usuario):
        exigir_rol(user, Rol.paciente)
        sid = request.path_params["solicitud_id"]
        s = next((x for x in repo.list_solicitudes(paciente_id=user.id) if x.id == sid), None)
        if s is None:
            raise AuthError(404, "Solicitud no encontrada")
        s.estado = EstadoSolicitud.cancelada
        return _json(repo.save_solicitud(s))

    @handler
    async def registrar_medico(request: Request, user: Usuario):
        exigir_rol(user, Rol.admin)
        data: MedicoIn = await _body(request, MedicoIn)
        medico = repo.upsert_usuario(Usuario(id=f"med-{new_id()}", nombre=data.nombre, rol=Rol.medico,
                                             especialidad=data.especialidad, email=data.email))
        if data.horario_inicial and data.horario_inicial.bloques:
            repo.save_agenda(Agenda(id=medico.id, medico_id=medico.id, **data.horario_inicial.model_dump()))
        log.info("médico registrado %s (%s)", medico.id, medico.especialidad)
        _publicar_disponibilidad(medico.especialidad)
        return _json(medico, 201)

    @handler
    async def disponibilidad(request: Request, user: Usuario):
        q = request.query_params
        try:
            desde = date.fromisoformat(q["desde"]) if q.get("desde") else now_utc().astimezone(LIMA).date()
            dias = min(int(q.get("dias", "7")), HORIZONTE_DIAS)
        except ValueError as exc:
            raise AuthError(400, "Parámetros de fecha inválidos") from exc
        if q.get("medico_id"):
            medicos_sel = [m for m in _medicos() if m.id == q["medico_id"]]
        else:
            medicos_sel = _medicos(q.get("especialidad"))
        por_dia: dict[str, list[dict]] = {(desde + timedelta(days=i)).isoformat(): [] for i in range(dias)}
        for m in medicos_sel:
            ag = repo.get_agenda(m.id)
            if not ag:
                continue
            for t in turnos_libres(ag, repo.list_citas(medico_id=m.id), desde, dias):
                por_dia[t.date().isoformat()].append({"fecha_hora": t.isoformat(), "medico_id": m.id,
                                                      "medico_nombre": m.nombre, "duracion_min": ag.duracion_min})
        return _json({"desde": desde.isoformat(), "dias": [
            {"fecha": f, "turnos": sorted(ts, key=lambda x: (x["fecha_hora"], x["medico_nombre"]))}
            for f, ts in por_dia.items()]})

    def _citas_fuera(ag: Agenda) -> int:
        futuras = [c for c in repo.list_citas(medico_id=ag.medico_id)
                   if c.estado == EstadoCita.programada and c.fecha_hora > now_utc()]
        fuera = 0
        for c in futuras:
            otras = [x for x in futuras if x.id != c.id]
            if not es_turno_libre(ag, otras, c.fecha_hora):
                fuera += 1
        return fuera

    @handler
    async def mi_agenda(request: Request, user: Usuario):
        exigir_rol(user, Rol.medico)
        ag = repo.get_agenda(user.id) or Agenda(id=user.id, medico_id=user.id)
        return _json({"agenda": ag.model_dump(mode="json"), "citas_fuera_de_horario": _citas_fuera(ag)})

    @handler
    async def guardar_mi_agenda(request: Request, user: Usuario):
        exigir_rol(user, Rol.medico)
        data: AgendaIn = await _body(request, AgendaIn)
        ag = repo.save_agenda(Agenda(id=user.id, medico_id=user.id, **data.model_dump()))
        log.info("agenda actualizada por %s: %d franjas", user.id, len(ag.bloques))
        if ag.bloques:
            _publicar_disponibilidad(user.especialidad)
        return _json({"agenda": ag.model_dump(mode="json"), "citas_fuera_de_horario": _citas_fuera(ag)})

    @handler
    async def listar_citas(request: Request, user: Usuario):
        if user.rol == Rol.paciente:
            citas = repo.list_citas(paciente_id=user.id)
        elif user.rol == Rol.medico:
            citas = repo.list_citas(medico_id=user.id)
        else:
            citas = repo.list_citas()
        return _json([_cita_con_nombres(svc, c) for c in citas])

    @handler
    async def crear_cita(request: Request, user: Usuario):
        exigir_rol(user, Rol.paciente)
        data: CitaIn = await _body(request, CitaIn)
        medico = repo.get_usuario(data.medico_id)
        if medico is None or medico.rol != Rol.medico:
            raise AuthError(404, "Médico no encontrado")
        citas_medico = repo.list_citas(medico_id=medico.id)
        if any(c.fecha_hora == data.fecha_hora and c.estado == EstadoCita.programada for c in citas_medico):
            raise AuthError(409, "Ese turno acaba de ser reservado por otra persona; elija otro")
        agenda = repo.get_agenda(medico.id)
        if agenda is None or not es_turno_libre(agenda, citas_medico, data.fecha_hora):
            raise AuthError(409, "Ese horario no está dentro de la atención del médico; elija un turno disponible")
        cita = repo.save_cita(Cita(paciente_id=user.id, medico_id=medico.id,
                                   especialidad=medico.especialidad or "Medicina general",
                                   fecha_hora=data.fecha_hora, modalidad=data.modalidad, motivo=data.motivo))
        publicar_cita_creada(svc.publisher, cita, settings.reminder_hours_before)
        log.info("cita creada %s", cita.id)
        return _json(_cita_con_nombres(svc, cita), 201)

    @handler
    async def cancelar_cita(request: Request, user: Usuario):
        cita = repo.get_cita(request.path_params["cita_id"])
        if cita is None or (user.id not in {cita.paciente_id, cita.medico_id} and user.rol != Rol.admin):
            raise AuthError(404, "Cita no encontrada")
        if cita.estado != EstadoCita.programada:
            raise AuthError(409, f"La cita ya está {cita.estado.value}")
        cita.estado = EstadoCita.cancelada
        repo.save_cita(cita)
        svc.publisher.publish({"tipo": "cancelacion", "cita_id": cita.id})
        _publicar_disponibilidad(cita.especialidad)  # se liberó un turno
        return _json(_cita_con_nombres(svc, cita))

    @handler
    async def ver_historial(request: Request, user: Usuario):
        pid = request.path_params["paciente_id"]
        if not _puede_ver_paciente(svc, user, pid):
            _audit(request, "historial.denegado", user, pid)
            raise AuthError(403, "No tiene acceso a la historia clínica de este paciente")
        _audit(request, "historial.lectura", user, pid)
        paciente = repo.get_usuario(pid)
        notas = []
        for n in leer_notas(repo, svc.cifrador, pid):
            d = n.model_dump(mode="json")
            med = repo.get_usuario(n.medico_id)
            d["medico_nombre"] = med.nombre if med else None
            if user.rol != Rol.medico:
                d.pop("apuntes", None)  # apuntes internos del médico
            notas.append(d)
        return _json({"paciente": paciente.model_dump(mode="json") if paciente else None, "notas": notas})

    @handler
    async def agregar_nota(request: Request, user: Usuario):
        exigir_rol(user, Rol.medico)
        pid = request.path_params["paciente_id"]
        if not _puede_ver_paciente(svc, user, pid):
            _audit(request, "historial.escritura_denegada", user, pid)
            raise AuthError(403, "No tiene acceso a la historia clínica de este paciente")
        data: NotaIn = await _body(request, NotaIn)
        if data.cita_id:
            cita = repo.get_cita(data.cita_id)
            if cita is None or cita.paciente_id != pid or cita.medico_id != user.id:
                raise AuthError(404, "Cita no encontrada para este paciente")
            cita.estado = EstadoCita.atendida
            repo.save_cita(cita)
        nota = NotaClinica(paciente_id=pid, medico_id=user.id, **data.model_dump())
        guardar_nota(repo, svc.cifrador, nota)
        _audit(request, "historial.escritura", user, pid, nota=nota.id)
        return _json(nota, 201)

    @handler
    async def url_documento(request: Request, user: Usuario):
        data: DocumentoIn = await _body(request, DocumentoIn)
        if not _puede_ver_paciente(svc, user, data.paciente_id):
            raise AuthError(403, "No tiene acceso a este paciente")
        _audit(request, "documento.subida", user, data.paciente_id, archivo=data.nombre_archivo)
        return _json(integrations.url_subida(settings, data.paciente_id, data.nombre_archivo), 201)

    @handler
    async def videoconsulta(request: Request, user: Usuario):
        cita = repo.get_cita(request.path_params["cita_id"])
        if cita is None or user.id not in {cita.paciente_id, cita.medico_id}:
            raise AuthError(404, "Cita no encontrada")
        if cita.estado != EstadoCita.programada:
            raise AuthError(409, "La cita no está programada")
        datos = integrations.token_videollamada(settings, cita.id, user.id)
        datos["modalidad"] = cita.modalidad.value
        return _json(datos)

    @handler
    async def notificaciones(request: Request, user: Usuario):
        if user.rol == Rol.paciente:
            return _json(repo.list_notificaciones(user.id))
        exigir_rol(user, Rol.admin)
        return _json(repo.list_notificaciones())

    # ---------- Fachada FHIR R4 para socios (clave de integración, sin contenido clínico) ----------
    def _fhir(data: dict, status: int = 200) -> JSONResponse:
        return JSONResponse(data, status_code=status, media_type="application/fhir+json",
                            headers={"Cache-Control": "no-store"})

    def _fhir_autorizado(request: Request) -> bool:
        return fhir.clave_valida(request.headers.get("x-api-key"), settings.integration_keys_sha256)

    async def fhir_patient(request: Request):
        if not _fhir_autorizado(request):
            return _fhir(fhir.operation_outcome("Clave de integración inválida", "security"), 401)
        pid = request.path_params["paciente_id"]
        paciente = repo.get_usuario(pid)
        if paciente is None or paciente.rol != Rol.paciente:
            return _fhir(fhir.operation_outcome("Paciente no encontrado"), 404)
        _audit(request, "fhir.patient", None, pid)
        return _fhir(fhir.patient(paciente))

    async def fhir_appointments(request: Request):
        if not _fhir_autorizado(request):
            return _fhir(fhir.operation_outcome("Clave de integración inválida", "security"), 401)
        pid = request.query_params.get("patient", "").removeprefix("Patient/")
        if not pid:
            return _fhir(fhir.operation_outcome("Indique ?patient=<id>", "required"), 400)
        _audit(request, "fhir.appointment", None, pid)
        citas = repo.list_citas(paciente_id=pid)
        return _fhir(fhir.bundle([fhir.appointment(c, repo.get_usuario(c.medico_id)) for c in citas]))

    dev_blobs: dict[str, int] = {}

    async def dev_blob(request: Request):
        """Subida de adjuntos en modo demo: en memoria o hacia el emulador de Blob Storage."""
        if not settings.es_local:
            return Response(status_code=404)
        contenido = await request.body()
        ruta = request.path_params["ruta"]
        if settings.blob_connection_string:  # pragma: no cover - requiere el emulador
            from azure.storage.blob import BlobServiceClient
            container = BlobServiceClient.from_connection_string(settings.blob_connection_string) \
                .get_container_client(settings.blob_container)
            if not container.exists():
                container.create_container()
            container.upload_blob(ruta, contenido, overwrite=True)
        dev_blobs[ruta] = len(contenido)
        return Response(status_code=201)

    routes = [
        Route("/api/health", health),
        Route("/api/dev/usuarios", dev_usuarios),
        Route("/api/dev/blob/{ruta:path}", dev_blob, methods=["PUT"]),
        Route("/api/me", me, methods=["GET"]),
        Route("/api/me", actualizar_me, methods=["PUT"]),
        Route("/api/medicos", medicos, methods=["GET"]),
        Route("/api/medicos", registrar_medico, methods=["POST"]),
        Route("/api/avisos-disponibilidad", mis_solicitudes, methods=["GET"]),
        Route("/api/avisos-disponibilidad", crear_solicitud, methods=["POST"]),
        Route("/api/avisos-disponibilidad/{solicitud_id}/cancelar", cancelar_solicitud, methods=["POST"]),
        Route("/api/especialidades", especialidades),
        Route("/api/disponibilidad", disponibilidad),
        Route("/api/medicos/me/agenda", mi_agenda, methods=["GET"]),
        Route("/api/medicos/me/agenda", guardar_mi_agenda, methods=["PUT"]),
        Route("/api/citas", listar_citas, methods=["GET"]),
        Route("/api/citas", crear_cita, methods=["POST"]),
        Route("/api/citas/{cita_id}/cancelar", cancelar_cita, methods=["POST"]),
        Route("/api/citas/{cita_id}/videoconsulta", videoconsulta, methods=["POST"]),
        Route("/api/pacientes/{paciente_id}/historial", ver_historial, methods=["GET"]),
        Route("/api/pacientes/{paciente_id}/historial", agregar_nota, methods=["POST"]),
        Route("/api/documentos", url_documento, methods=["POST"]),
        Route("/api/notificaciones", notificaciones),
        Route("/api/fhir/Patient/{paciente_id}", fhir_patient),
        Route("/api/fhir/Appointment", fhir_appointments),
    ]
    app = Starlette(routes=routes)
    app.state.services = svc
    return app
