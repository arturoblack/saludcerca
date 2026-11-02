"""Horarios de atención de los médicos y cálculo de turnos libres.

Cada médico define bloques semanales (p. ej. lunes 08:00–12:00) y la duración del turno.
Un turno está libre si cae dentro de un bloque, no es un día bloqueado, no tiene otra cita
programada y empieza con la anticipación mínima. Todas las horas son de Lima (UTC−05:00).
"""
from __future__ import annotations

from collections.abc import Iterable
from datetime import date, datetime, time, timedelta

from .messaging import LIMA
from .models import Agenda, Cita, EstadoCita, now_utc

ANTICIPACION_MIN = timedelta(hours=1)  # no se reserva un turno que empieza en menos de 1 h
HORIZONTE_DIAS = 30


def _en_lima(f: date, h: time) -> datetime:
    return datetime.combine(f, h, tzinfo=LIMA)


def turnos_libres(agenda: Agenda, citas: Iterable[Cita], desde: date, dias: int,
                  ahora: datetime | None = None) -> list[datetime]:
    ahora = ahora or now_utc()
    ocupados = {c.fecha_hora for c in citas if c.estado == EstadoCita.programada}
    bloqueados = set(agenda.dias_bloqueados)
    paso = timedelta(minutes=agenda.duracion_min)
    libres: list[datetime] = []
    for i in range(max(0, min(dias, HORIZONTE_DIAS))):
        dia = desde + timedelta(days=i)
        if dia in bloqueados:
            continue
        for b in sorted((b for b in agenda.bloques if b.dia == dia.weekday()), key=lambda b: b.inicio):
            t, fin = _en_lima(dia, b.inicio), _en_lima(dia, b.fin)
            while t + paso <= fin:
                if t >= ahora + ANTICIPACION_MIN and t not in ocupados:
                    libres.append(t)
                t += paso
    return libres


def es_turno_libre(agenda: Agenda, citas: Iterable[Cita], fecha_hora: datetime) -> bool:
    dia = fecha_hora.astimezone(LIMA).date()
    return fecha_hora in turnos_libres(agenda, citas, dia, 1)
