"""Acceso a datos.

`MemoryRepository` sirve para la demo local y las pruebas.
`CosmosRepository` usa Azure Cosmos DB (API NoSQL, modo serverless) con Managed Identity.

Contenedores y claves de partición en Cosmos DB:
  usuarios        /id
  citas           /paciente_id
  historial       /paciente_id
  notificaciones  /paciente_id
  agendas         /medico_id
  solicitudes     /especialidad  (avisos de disponibilidad: se consultan por especialidad)
Particionar por paciente mantiene en una sola partición lo que más se consulta:
las citas y la historia clínica de una persona.
"""
from __future__ import annotations

import threading
from typing import Protocol, TypeVar

from pydantic import BaseModel

from .config import Settings
from .models import Agenda, Cita, EstadoSolicitud, NotaAlmacenada, Notificacion, Rol, SolicitudAviso, Usuario

M = TypeVar("M", bound=BaseModel)


class Repository(Protocol):
    def get_usuario(self, usuario_id: str) -> Usuario | None: ...
    def upsert_usuario(self, usuario: Usuario) -> Usuario: ...
    def list_usuarios(self, rol: Rol | None = None) -> list[Usuario]: ...

    def save_cita(self, cita: Cita) -> Cita: ...
    def get_cita(self, cita_id: str) -> Cita | None: ...
    def list_citas(self, *, paciente_id: str | None = None, medico_id: str | None = None) -> list[Cita]: ...

    def add_nota(self, nota: NotaAlmacenada) -> NotaAlmacenada: ...
    def list_notas(self, paciente_id: str) -> list[NotaAlmacenada]: ...

    def add_notificacion(self, n: Notificacion) -> Notificacion: ...
    def list_notificaciones(self, paciente_id: str | None = None) -> list[Notificacion]: ...

    def get_agenda(self, medico_id: str) -> Agenda | None: ...
    def save_agenda(self, agenda: Agenda) -> Agenda: ...

    def save_solicitud(self, s: SolicitudAviso) -> SolicitudAviso: ...
    def list_solicitudes(self, *, paciente_id: str | None = None, especialidad: str | None = None,
                         estado: EstadoSolicitud | None = None) -> list[SolicitudAviso]: ...


class MemoryRepository:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.usuarios: dict[str, Usuario] = {}
        self.citas: dict[str, Cita] = {}
        self.notas: dict[str, NotaAlmacenada] = {}
        self.notificaciones: dict[str, Notificacion] = {}
        self.agendas: dict[str, Agenda] = {}
        self.solicitudes: dict[str, SolicitudAviso] = {}

    def get_usuario(self, usuario_id: str) -> Usuario | None:
        return self.usuarios.get(usuario_id)

    def upsert_usuario(self, usuario: Usuario) -> Usuario:
        with self._lock:
            self.usuarios[usuario.id] = usuario
        return usuario

    def list_usuarios(self, rol: Rol | None = None) -> list[Usuario]:
        return [u for u in self.usuarios.values() if rol is None or u.rol == rol]

    def save_cita(self, cita: Cita) -> Cita:
        with self._lock:
            self.citas[cita.id] = cita
        return cita

    def get_cita(self, cita_id: str) -> Cita | None:
        return self.citas.get(cita_id)

    def list_citas(self, *, paciente_id: str | None = None, medico_id: str | None = None) -> list[Cita]:
        res = [
            c for c in self.citas.values()
            if (paciente_id is None or c.paciente_id == paciente_id)
            and (medico_id is None or c.medico_id == medico_id)
        ]
        return sorted(res, key=lambda c: c.fecha_hora)

    def add_nota(self, nota: NotaAlmacenada) -> NotaAlmacenada:
        with self._lock:
            self.notas[nota.id] = nota
        return nota

    def list_notas(self, paciente_id: str) -> list[NotaAlmacenada]:
        return sorted((n for n in self.notas.values() if n.paciente_id == paciente_id),
                      key=lambda n: n.fecha, reverse=True)

    def add_notificacion(self, n: Notificacion) -> Notificacion:
        with self._lock:
            self.notificaciones[n.id] = n
        return n

    def list_notificaciones(self, paciente_id: str | None = None) -> list[Notificacion]:
        res = [n for n in self.notificaciones.values() if paciente_id is None or n.paciente_id == paciente_id]
        return sorted(res, key=lambda n: n.creada_en, reverse=True)

    def get_agenda(self, medico_id: str) -> Agenda | None:
        return self.agendas.get(medico_id)

    def save_agenda(self, agenda: Agenda) -> Agenda:
        with self._lock:
            self.agendas[agenda.medico_id] = agenda
        return agenda

    def save_solicitud(self, s: SolicitudAviso) -> SolicitudAviso:
        with self._lock:
            self.solicitudes[s.id] = s
        return s

    def list_solicitudes(self, *, paciente_id: str | None = None, especialidad: str | None = None,
                         estado: EstadoSolicitud | None = None) -> list[SolicitudAviso]:
        res = [s for s in self.solicitudes.values()
               if (paciente_id is None or s.paciente_id == paciente_id)
               and (especialidad is None or s.especialidad == especialidad)
               and (estado is None or s.estado == estado)]
        return sorted(res, key=lambda s: s.creada_en)


class CosmosRepository:  # pragma: no cover - requiere una cuenta de Cosmos DB
    def __init__(self, settings: Settings) -> None:
        from azure.cosmos import CosmosClient
        from azure.identity import DefaultAzureCredential

        credential = settings.cosmos_key or DefaultAzureCredential()
        # Con emulador (clave fija) se desactiva el descubrimiento de regiones: solo hay un endpoint.
        extra = {"enable_endpoint_discovery": False} if settings.cosmos_key else {}
        client = CosmosClient(settings.cosmos_endpoint, credential=credential, **extra)
        if settings.cosmos_auto_create:  # emulador local: crea base y contenedores si faltan
            from azure.cosmos import PartitionKey
            db = client.create_database_if_not_exists(settings.cosmos_database)
            for nombre, pk in (("usuarios", "/id"), ("citas", "/paciente_id"),
                               ("historial", "/paciente_id"), ("notificaciones", "/paciente_id"),
                               ("agendas", "/medico_id"), ("solicitudes", "/especialidad")):
                db.create_container_if_not_exists(nombre, partition_key=PartitionKey(path=pk))
        else:
            db = client.get_database_client(settings.cosmos_database)
        self._usuarios = db.get_container_client("usuarios")
        self._citas = db.get_container_client("citas")
        self._historial = db.get_container_client("historial")
        self._notificaciones = db.get_container_client("notificaciones")
        self._agendas = db.get_container_client("agendas")
        self._solicitudes = db.get_container_client("solicitudes")

    @staticmethod
    def _dump(model: BaseModel) -> dict:
        return model.model_dump(mode="json")

    @staticmethod
    def _query(container, model: type[M], query: str, params: list[dict], partition_key: str | None = None) -> list[M]:
        kwargs = {"partition_key": partition_key} if partition_key else {"enable_cross_partition_query": True}
        items = container.query_items(query=query, parameters=params, **kwargs)
        return [model.model_validate(i) for i in items]

    def get_usuario(self, usuario_id: str) -> Usuario | None:
        from azure.cosmos.exceptions import CosmosResourceNotFoundError
        try:
            return Usuario.model_validate(self._usuarios.read_item(usuario_id, partition_key=usuario_id))
        except CosmosResourceNotFoundError:
            return None

    def upsert_usuario(self, usuario: Usuario) -> Usuario:
        self._usuarios.upsert_item(self._dump(usuario))
        return usuario

    def list_usuarios(self, rol: Rol | None = None) -> list[Usuario]:
        if rol is None:
            return self._query(self._usuarios, Usuario, "SELECT * FROM c", [])
        return self._query(self._usuarios, Usuario, "SELECT * FROM c WHERE c.rol = @rol", [{"name": "@rol", "value": rol.value}])

    def save_cita(self, cita: Cita) -> Cita:
        self._citas.upsert_item(self._dump(cita))
        return cita

    def get_cita(self, cita_id: str) -> Cita | None:
        res = self._query(self._citas, Cita, "SELECT * FROM c WHERE c.id = @id", [{"name": "@id", "value": cita_id}])
        return res[0] if res else None

    def list_citas(self, *, paciente_id: str | None = None, medico_id: str | None = None) -> list[Cita]:
        if paciente_id:
            return self._query(self._citas, Cita, "SELECT * FROM c ORDER BY c.fecha_hora", [], partition_key=paciente_id)
        if medico_id:
            return self._query(self._citas, Cita, "SELECT * FROM c WHERE c.medico_id = @m ORDER BY c.fecha_hora",
                               [{"name": "@m", "value": medico_id}])
        return self._query(self._citas, Cita, "SELECT * FROM c ORDER BY c.fecha_hora", [])

    def add_nota(self, nota: NotaAlmacenada) -> NotaAlmacenada:
        self._historial.create_item(self._dump(nota))
        return nota

    def list_notas(self, paciente_id: str) -> list[NotaAlmacenada]:
        return self._query(self._historial, NotaAlmacenada, "SELECT * FROM c ORDER BY c.fecha DESC", [],
                           partition_key=paciente_id)

    def add_notificacion(self, n: Notificacion) -> Notificacion:
        self._notificaciones.upsert_item(self._dump(n))
        return n

    def list_notificaciones(self, paciente_id: str | None = None) -> list[Notificacion]:
        if paciente_id:
            return self._query(self._notificaciones, Notificacion, "SELECT * FROM c ORDER BY c.creada_en DESC", [],
                               partition_key=paciente_id)
        return self._query(self._notificaciones, Notificacion, "SELECT TOP 100 * FROM c ORDER BY c.creada_en DESC", [])


    def get_agenda(self, medico_id: str) -> Agenda | None:
        from azure.cosmos.exceptions import CosmosResourceNotFoundError
        try:
            return Agenda.model_validate(self._agendas.read_item(medico_id, partition_key=medico_id))
        except CosmosResourceNotFoundError:
            return None

    def save_agenda(self, agenda: Agenda) -> Agenda:
        self._agendas.upsert_item(self._dump(agenda))
        return agenda

    def save_solicitud(self, s: SolicitudAviso) -> SolicitudAviso:
        self._solicitudes.upsert_item(self._dump(s))
        return s

    def list_solicitudes(self, *, paciente_id: str | None = None, especialidad: str | None = None,
                         estado: EstadoSolicitud | None = None) -> list[SolicitudAviso]:
        filtros, params = [], []
        if paciente_id:
            filtros.append("c.paciente_id = @p")
            params.append({"name": "@p", "value": paciente_id})
        if estado:
            filtros.append("c.estado = @e")
            params.append({"name": "@e", "value": estado.value})
        where = f" WHERE {' AND '.join(filtros)}" if filtros else ""
        return self._query(self._solicitudes, SolicitudAviso, f"SELECT * FROM c{where} ORDER BY c.creada_en", params,  # noqa: S608 - filtros fijos; valores por parámetro
                           partition_key=especialidad)

def build_repository(settings: Settings) -> Repository:
    if settings.storage_backend == "cosmos":
        return CosmosRepository(settings)
    return MemoryRepository()
