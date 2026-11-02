"""Datos ficticios para la demo local. Ningún dato corresponde a personas reales."""
from __future__ import annotations

from datetime import datetime, time, timedelta

from .cifrado import Cifrador
from .historial import guardar_nota
from .messaging import LIMA
from .models import Agenda, Bloque, Canal, Cita, EstadoCita, Modalidad, NotaClinica, Rol, SignosVitales, Usuario
from .repository import Repository

USUARIOS = [
    Usuario(id="pac-rosa", nombre="Rosa Quispe Mamani", rol=Rol.paciente, telefono="+51900000001",
            email="rosa.demo@example.com", canal_preferido=Canal.app, establecimiento="P.S. San Pedro de Coris"),
    Usuario(id="pac-juan", nombre="Juan Ccahuana Huamán", rol=Rol.paciente, telefono="+51900000002",
            canal_preferido=Canal.sms, establecimiento="P.S. Santa Rosa de Lircay"),
    Usuario(id="med-luis", nombre="Dr. Luis Herrera Paredes", rol=Rol.medico, especialidad="Medicina general",
            email="luis.demo@example.com"),
    Usuario(id="med-ana", nombre="Dra. Ana Torres Rojas", rol=Rol.medico, especialidad="Pediatría",
            email="ana.demo@example.com"),
    Usuario(id="med-elena", nombre="Dra. Elena Huamán Ccori", rol=Rol.medico, especialidad="Medicina general",
            email="elena.demo@example.com"),
    Usuario(id="med-jorge", nombre="Dr. Jorge Valdivia Soto", rol=Rol.medico, especialidad="Ginecología y obstetricia",
            email="jorge.demo@example.com"),
    # Cardiólogo recién incorporado: aún no publica su horario (sirve para probar la lista de espera)
    Usuario(id="med-cesar", nombre="Dr. César Mendoza Ruiz", rol=Rol.medico, especialidad="Cardiología",
            email="cesar.demo@example.com"),
    Usuario(id="admin-ong", nombre="Coordinación ONG", rol=Rol.admin, email="coordinacion.demo@example.com"),
]


def _bloques(dias: list[int], inicio: str, fin: str) -> list[Bloque]:
    return [Bloque(dia=d, inicio=time.fromisoformat(inicio), fin=time.fromisoformat(fin)) for d in dias]


# Horarios de atención (0 = lunes … 6 = domingo)
AGENDAS = {
    "med-luis": (30, _bloques([0, 1, 2, 3, 4, 5], "08:00", "12:00")),
    "med-elena": (20, _bloques([0, 2, 4], "14:00", "18:00")),
    "med-ana": (30, _bloques([0, 1, 2, 3, 4], "08:00", "12:00") + _bloques([1, 3], "14:00", "17:00")),
    "med-jorge": (30, _bloques([1, 3], "09:00", "13:00") + _bloques([5], "08:00", "11:00")),
}


def _a_las(dias: int, hora: int, minuto: int = 0) -> datetime:
    base = datetime.now(LIMA) + timedelta(days=dias)
    return base.replace(hour=hora, minute=minuto, second=0, microsecond=0)


def cargar_demo(repo: Repository, cif: Cifrador) -> None:
    if repo.get_usuario("pac-rosa"):
        return
    for u in USUARIOS:
        repo.upsert_usuario(u)
    for medico_id, (duracion, bloques) in AGENDAS.items():
        repo.save_agenda(Agenda(id=medico_id, medico_id=medico_id, duracion_min=duracion, bloques=bloques))

    pasada = repo.save_cita(Cita(paciente_id="pac-rosa", medico_id="med-luis", especialidad="Medicina general",
                                 fecha_hora=_a_las(-20, 9), estado=EstadoCita.atendida, motivo="Control de presión"))
    guardar_nota(repo, cif, NotaClinica(
        paciente_id="pac-rosa", medico_id="med-luis", cita_id=pasada.id, fecha=pasada.fecha_hora,
        motivo="Control de presión arterial", diagnostico="Hipertensión arterial controlada",
        indicaciones="Dieta baja en sal. Caminar 30 minutos al día. Control en 30 días.",
        receta=["Enalapril 10 mg: 1 tableta cada 12 horas por 30 días"],
        signos=SignosVitales(presion_sistolica=132, presion_diastolica=84, pulso=76, temperatura=36.5,
                             peso_kg=61.2, saturacion=96)))
    repo.save_cita(Cita(paciente_id="pac-rosa", medico_id="med-luis", especialidad="Medicina general",
                        fecha_hora=_a_las(1, 10), modalidad=Modalidad.video, motivo="Control mensual"))
    repo.save_cita(Cita(paciente_id="pac-juan", medico_id="med-ana", especialidad="Pediatría",
                        fecha_hora=_a_las(3, 9, 30), modalidad=Modalidad.audio, motivo="Control de niño sano"))
