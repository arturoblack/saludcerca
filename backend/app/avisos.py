"""Avisos de disponibilidad ("Avisarme cuando haya turnos").

Cuando se publican turnos de una especialidad (un médico guarda su horario, la coordinación
registra un médico nuevo con horario o se cancela una cita), se encola el evento
`disponibilidad`. fn-notificador lo procesa fuera de la solicitud HTTP: busca las solicitudes
activas de esa especialidad, comprueba que de verdad haya turnos libres y avisa a cada paciente
por su canal (SMS si usa teléfono básico). Cada solicitud se avisa una sola vez.
"""
from __future__ import annotations

import logging

from .agenda import turnos_libres
from .messaging import LIMA, Notifier, destino_para
from .models import EstadoSolicitud, Notificacion, Rol, now_utc
from .repository import Repository

log = logging.getLogger("saludcerca.avisos")
DIAS_BUSQUEDA = 14
_DIAS = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]


def _primer_turno_por_medico(repo: Repository, especialidad: str) -> dict[str, object]:
    hoy = now_utc().astimezone(LIMA).date()
    res = {}
    for m in repo.list_usuarios(Rol.medico):
        if m.especialidad != especialidad:
            continue
        ag = repo.get_agenda(m.id)
        if not ag:
            continue
        libres = turnos_libres(ag, repo.list_citas(medico_id=m.id), hoy, DIAS_BUSQUEDA)
        if libres:
            res[m.id] = (m, libres[0], len(libres))
    return res


def _mensaje(especialidad: str, medico, primero) -> str:
    t = primero.astimezone(LIMA)
    cuando = f"{_DIAS[t.weekday()]} {t:%d/%m} a las {t:%H:%M}"
    return (f"SaludCerca: ya hay turnos de {especialidad} con {medico.nombre}, desde el {cuando}. "
            f"Ingrese a la app o acuda a su puesto de salud para reservar.")


def notificar_disponibilidad(repo: Repository, notifier: Notifier, especialidad: str) -> list[Notificacion]:
    pendientes = repo.list_solicitudes(especialidad=especialidad, estado=EstadoSolicitud.activa)
    if not pendientes:
        return []
    disponibles = _primer_turno_por_medico(repo, especialidad)
    if not disponibles:
        log.info("disponibilidad: %s sin turnos libres todavía", especialidad)
        return []
    enviadas = []
    for s in pendientes:
        if s.medico_id and s.medico_id not in disponibles:
            continue  # pidió un médico concreto que aún no tiene turnos
        opciones = {s.medico_id: disponibles[s.medico_id]} if s.medico_id else disponibles
        medico, primero, _ = min(opciones.values(), key=lambda x: x[1])
        paciente = repo.get_usuario(s.paciente_id)
        if paciente is None:
            continue
        canal, destino = destino_para(paciente)
        texto = _mensaje(especialidad, medico, primero)
        notif = Notificacion(cita_id=None, paciente_id=paciente.id, tipo="disponibilidad", canal=canal,
                             destino=destino, mensaje=texto)
        try:
            notifier.send(canal, destino, f"Turnos de {especialidad} disponibles", texto)
        except Exception:
            log.exception("no se pudo avisar a %s por %s", paciente.id, canal.value)
            notif.estado = "fallida"
        repo.add_notificacion(notif)
        s.estado, s.notificada_en = EstadoSolicitud.notificada, now_utc()
        repo.save_solicitud(s)
        enviadas.append(notif)
    log.info("disponibilidad: %s -> %d avisos enviados", especialidad, len(enviadas))
    return enviadas

