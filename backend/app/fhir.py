"""Fachada FHIR R4 para socios externos (hospital de referencia, DIRESA, MINSA).

- Autenticación con clave de integración en la cabecera `x-api-key`. Solo se guarda el hash
  SHA-256 de cada clave (INTEGRATION_KEYS_SHA256) y se compara en tiempo constante.
- Minimización de datos: se expone identificación básica del paciente y el estado de sus
  citas; nunca diagnósticos, recetas ni notas clínicas.
"""
from __future__ import annotations

import hashlib
import hmac

from .models import Cita, EstadoCita, Usuario

ESTADO_FHIR = {
    EstadoCita.programada: "booked",
    EstadoCita.cancelada: "cancelled",
    EstadoCita.atendida: "fulfilled",
}


def clave_valida(clave: str | None, hashes_csv: str) -> bool:
    if not clave or not hashes_csv:
        return False
    recibido = hashlib.sha256(clave.encode()).hexdigest()
    return any(hmac.compare_digest(recibido, h.strip().lower()) for h in hashes_csv.split(",") if h.strip())


def patient(u: Usuario) -> dict:
    partes = u.nombre.split()
    recurso = {
        "resourceType": "Patient",
        "id": u.id,
        "meta": {"profile": ["http://hl7.org/fhir/StructureDefinition/Patient"]},
        "active": True,
        "name": [{"use": "official", "text": u.nombre,
                  "family": " ".join(partes[1:]) if len(partes) > 1 else u.nombre,
                  "given": partes[:1]}],
    }
    if u.establecimiento:
        recurso["managingOrganization"] = {"display": u.establecimiento}
    return recurso


def appointment(c: Cita, medico: Usuario | None) -> dict:
    return {
        "resourceType": "Appointment",
        "id": c.id,
        "status": ESTADO_FHIR[c.estado],
        "serviceType": [{"text": c.especialidad}],
        "appointmentType": {"text": "Teleconsulta por video" if c.modalidad.value == "video" else "Teleconsulta por audio"},
        "start": c.fecha_hora.isoformat(),
        "participant": [
            {"actor": {"reference": f"Patient/{c.paciente_id}"}, "status": "accepted"},
            {"actor": {"display": medico.nombre if medico else "Médico"}, "status": "accepted"},
        ],
    }


def bundle(recursos: list[dict]) -> dict:
    return {"resourceType": "Bundle", "type": "searchset", "total": len(recursos),
            "entry": [{"resource": r} for r in recursos]}


def operation_outcome(mensaje: str, codigo: str = "not-found") -> dict:
    return {"resourceType": "OperationOutcome",
            "issue": [{"severity": "error", "code": codigo, "diagnostics": mensaje}]}
