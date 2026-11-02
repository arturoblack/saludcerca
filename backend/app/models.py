"""Modelos de dominio y de entrada de la API (Pydantic v2)."""
from __future__ import annotations

import re
import uuid
from datetime import UTC, date, datetime, time
from typing import Literal
from enum import Enum

from pydantic import BaseModel, Field, field_validator, model_validator


def now_utc() -> datetime:
    return datetime.now(UTC)


def new_id() -> str:
    return uuid.uuid4().hex[:12]


class Rol(str, Enum):
    paciente = "paciente"
    medico = "medico"
    admin = "admin"


class Canal(str, Enum):
    sms = "sms"
    email = "email"
    app = "app"


class EstadoCita(str, Enum):
    programada = "programada"
    cancelada = "cancelada"
    atendida = "atendida"


class Modalidad(str, Enum):
    video = "video"
    audio = "audio"


class Usuario(BaseModel):
    id: str
    nombre: str
    rol: Rol
    email: str | None = None
    telefono: str | None = None
    canal_preferido: Canal = Canal.app
    especialidad: str | None = None  # solo médicos
    establecimiento: str | None = None


class Cita(BaseModel):
    id: str = Field(default_factory=new_id)
    paciente_id: str
    medico_id: str
    especialidad: str
    fecha_hora: datetime
    modalidad: Modalidad = Modalidad.video
    motivo: str | None = None
    estado: EstadoCita = EstadoCita.programada
    creada_en: datetime = Field(default_factory=now_utc)


class SignosVitales(BaseModel):
    presion_sistolica: int | None = Field(default=None, ge=50, le=260)
    presion_diastolica: int | None = Field(default=None, ge=30, le=160)
    pulso: int | None = Field(default=None, ge=20, le=250)
    temperatura: float | None = Field(default=None, ge=30, le=45)
    peso_kg: float | None = Field(default=None, ge=0.5, le=350)
    saturacion: int | None = Field(default=None, ge=50, le=100)


class NotaClinica(BaseModel):
    """Nota clínica en claro: solo existe en memoria mientras se atiende la solicitud."""
    id: str = Field(default_factory=new_id)
    paciente_id: str
    medico_id: str
    cita_id: str | None = None
    fecha: datetime = Field(default_factory=now_utc)
    motivo: str
    diagnostico: str
    indicaciones: str
    receta: list[str] = Field(default_factory=list)
    signos: SignosVitales | None = None
    apuntes: str | None = None  # notas tomadas durante la videollamada; solo las ve el personal de salud
    adjuntos: list[str] = Field(default_factory=list)


CAMPOS_CIFRADOS = ("motivo", "diagnostico", "indicaciones", "receta", "signos", "apuntes")


class NotaAlmacenada(BaseModel):
    """Lo que se guarda en la base: metadatos en claro y contenido clínico cifrado."""
    id: str
    paciente_id: str
    medico_id: str
    cita_id: str | None = None
    fecha: datetime
    adjuntos: list[str] = Field(default_factory=list)
    contenido: str  # AES-256-GCM, ver app/cifrado.py


class Notificacion(BaseModel):
    id: str = Field(default_factory=new_id)
    cita_id: str | None = None  # None en avisos de disponibilidad
    paciente_id: str
    tipo: str  # confirmacion | recordatorio | cancelacion | disponibilidad
    canal: Canal
    destino: str
    mensaje: str
    estado: str = "enviada"  # enviada | programada | fallida
    programada_para: datetime | None = None
    creada_en: datetime = Field(default_factory=now_utc)


class Bloque(BaseModel):
    """Franja semanal de atención. dia: 0 = lunes … 6 = domingo (hora de Lima)."""
    dia: int = Field(ge=0, le=6)
    inicio: time
    fin: time

    @model_validator(mode="after")
    def fin_despues_de_inicio(self) -> Bloque:
        if self.fin <= self.inicio:
            raise ValueError("la hora de fin debe ser posterior a la de inicio")
        return self


class AgendaIn(BaseModel):
    duracion_min: Literal[15, 20, 30, 45, 60] = 30
    bloques: list[Bloque] = Field(default_factory=list, max_length=42)
    dias_bloqueados: list[date] = Field(default_factory=list, max_length=60)

    @model_validator(mode="after")
    def sin_superposicion(self) -> AgendaIn:
        for d in range(7):
            del_dia = sorted((b for b in self.bloques if b.dia == d), key=lambda b: b.inicio)
            for a, b in zip(del_dia, del_dia[1:], strict=False):
                if b.inicio < a.fin:
                    raise ValueError(f"hay franjas superpuestas el día {d}")
        return self


class Agenda(AgendaIn):
    id: str  # = medico_id (un documento por médico)
    medico_id: str
    actualizada_en: datetime = Field(default_factory=now_utc)


# Catálogo de especialidades que ofrece la red (aunque aún no tengan médicos).
ESPECIALIDADES = [
    "Cardiología", "Dermatología", "Ginecología y obstetricia", "Medicina general",
    "Nutrición", "Pediatría", "Psicología",
]


class EstadoSolicitud(str, Enum):
    activa = "activa"
    notificada = "notificada"
    cancelada = "cancelada"


class SolicitudAviso(BaseModel):
    """El paciente pide que le avisen cuando haya turnos de una especialidad (o de un médico)."""
    id: str = Field(default_factory=new_id)
    paciente_id: str
    especialidad: str
    medico_id: str | None = None
    estado: EstadoSolicitud = EstadoSolicitud.activa
    creada_en: datetime = Field(default_factory=now_utc)
    notificada_en: datetime | None = None


# ---------- Entradas de la API ----------

class CitaIn(BaseModel):
    medico_id: str
    fecha_hora: datetime
    modalidad: Modalidad = Modalidad.video
    motivo: str | None = Field(default=None, max_length=280)

    @field_validator("fecha_hora")
    @classmethod
    def futura_y_con_zona(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("fecha_hora debe incluir zona horaria (ISO 8601, p. ej. 2026-11-05T10:00:00-05:00)")
        if v <= now_utc():
            raise ValueError("la cita debe programarse en el futuro")
        return v


class NotaIn(BaseModel):
    cita_id: str | None = None
    motivo: str = Field(min_length=3, max_length=500)
    diagnostico: str = Field(min_length=3, max_length=1000)
    indicaciones: str = Field(min_length=3, max_length=2000)
    receta: list[str] = Field(default_factory=list, max_length=15)
    signos: SignosVitales | None = None
    apuntes: str | None = Field(default=None, max_length=4000)
    adjuntos: list[str] = Field(default_factory=list, max_length=10)


class PerfilIn(BaseModel):
    """Datos de contacto que cada usuario puede cambiar."""
    telefono: str | None = Field(default=None, max_length=20)
    email: str | None = Field(default=None, max_length=120)
    canal_preferido: Canal

    @field_validator("telefono")
    @classmethod
    def telefono_valido(cls, v: str | None) -> str | None:
        if not v or not v.strip():
            return None
        n = re.sub(r"[\s\-().]", "", v)
        if re.fullmatch(r"9\d{8}", n):  # celular peruano sin código de país
            n = "+51" + n
        if not re.fullmatch(r"\+\d{8,15}", n):
            raise ValueError("use un número como 987 654 321 o +51 987 654 321")
        return n

    @field_validator("email")
    @classmethod
    def email_valido(cls, v: str | None) -> str | None:
        if not v or not v.strip():
            return None
        v = v.strip().lower()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", v):
            raise ValueError("correo inválido")
        return v

    @model_validator(mode="after")
    def canal_con_dato(self) -> PerfilIn:
        if self.canal_preferido == Canal.sms and not self.telefono:
            raise ValueError("para recibir avisos por SMS indique su número de celular")
        if self.canal_preferido == Canal.email and not self.email:
            raise ValueError("para recibir avisos por correo indique su correo")
        return self


class SolicitudAvisoIn(BaseModel):
    especialidad: str
    medico_id: str | None = None

    @field_validator("especialidad")
    @classmethod
    def en_catalogo(cls, v: str) -> str:
        if v not in ESPECIALIDADES:
            raise ValueError("especialidad no ofrecida")
        return v


class MedicoIn(BaseModel):
    nombre: str = Field(min_length=5, max_length=120)
    especialidad: str
    email: str | None = Field(default=None, max_length=120)
    # Plantilla de horario inicial opcional; el médico puede cambiarlo luego en "Mi horario".
    horario_inicial: AgendaIn | None = None

    @field_validator("especialidad")
    @classmethod
    def en_catalogo(cls, v: str) -> str:
        if v not in ESPECIALIDADES:
            raise ValueError("especialidad no ofrecida")
        return v


class DocumentoIn(BaseModel):
    paciente_id: str
    nombre_archivo: str = Field(min_length=1, max_length=120)
    tipo_contenido: str = "application/pdf"
