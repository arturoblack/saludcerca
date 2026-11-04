import json
import logging

import pytest
from conftest import CLAVE_FHIR
from cryptography.exceptions import InvalidTag

from app.cifrado import Cifrador


def _nota(client, **extra):
    cita = next(c for c in client.get("/api/citas", "med-luis").json() if c["estado"] == "programada")
    body = {"cita_id": cita["id"], "motivo": "Control", "diagnostico": "Gastritis aguda",
            "indicaciones": "Dieta blanda", **extra}
    return cita, client.post(f"/api/pacientes/{cita['paciente_id']}/historial", "med-luis", body)


def test_contenido_clinico_se_guarda_cifrado(client, repo):
    _, r = _nota(client, receta=["Omeprazol 20 mg cada 24 h por 14 días"])
    assert r.status_code == 201
    guardada = next(n for n in repo.notas.values() if n.id == r.json()["id"])
    crudo = guardada.model_dump_json()
    assert "Gastritis" not in crudo and "Omeprazol" not in crudo and guardada.contenido.startswith("v1.")


def test_texto_cifrado_no_se_puede_mover_a_otro_paciente(client, repo):
    _, r = _nota(client)
    guardada = next(n for n in repo.notas.values() if n.id == r.json()["id"])
    cif = client.app.state.services.cifrador
    assert cif.descifrar(guardada.contenido, f"{guardada.paciente_id}:{guardada.id}")["diagnostico"] == "Gastritis aguda"
    with pytest.raises(InvalidTag):
        cif.descifrar(guardada.contenido, f"pac-juan:{guardada.id}")


def test_llave_debe_tener_32_bytes():
    with pytest.raises(ValueError):
        Cifrador("abcd")


def test_nota_estructurada_con_signos_y_receta(client):
    cita, r = _nota(client, receta=["Paracetamol 500 mg cada 8 h"],
                    signos={"presion_sistolica": 118, "presion_diastolica": 76, "pulso": 72, "temperatura": 36.8})
    assert r.status_code == 201
    nota = client.get(f"/api/pacientes/{cita['paciente_id']}/historial", "pac-rosa").json()["notas"][0]
    assert nota["receta"] == ["Paracetamol 500 mg cada 8 h"] and nota["signos"]["pulso"] == 72


def test_signos_fuera_de_rango_se_rechazan(client):
    _, r = _nota(client, signos={"temperatura": 50})
    assert r.status_code == 422


def test_auditoria_registra_ip(client, caplog):
    caplog.set_level(logging.INFO, logger="saludcerca.audit")
    client.request("GET", "/api/pacientes/pac-rosa/historial", "med-luis", headers_extra={"X-Forwarded-For": "190.12.34.56"})
    evento = json.loads(caplog.records[-1].getMessage())
    assert evento["accion"] == "historial.lectura" and evento["ip"] == "190.12.34.56"


def test_fhir_exige_clave(client):
    assert client.get("/api/fhir/Patient/pac-rosa").status_code == 401
    assert client.get("/api/fhir/Patient/pac-rosa", headers={"x-api-key": "otra"}).status_code == 401


def test_fhir_patient_sin_datos_clinicos(client):
    r = client.get("/api/fhir/Patient/pac-rosa", headers={"x-api-key": CLAVE_FHIR})
    assert r.status_code == 200
    p = r.json()
    assert p["resourceType"] == "Patient" and p["name"][0]["text"] == "Rosa Quispe Mamani"
    assert "Hipertensión" not in r.body.decode() and "telecom" not in p


def test_fhir_appointment_bundle(client):
    r = client.get("/api/fhir/Appointment?patient=Patient/pac-rosa", headers={"x-api-key": CLAVE_FHIR})
    b = r.json()
    assert b["resourceType"] == "Bundle" and b["total"] >= 2
    assert {e["resource"]["status"] for e in b["entry"]} <= {"booked", "fulfilled", "cancelled"}


def test_apuntes_de_la_llamada_solo_para_el_medico(client, repo):
    cita, r = _nota(client, apuntes="[02:15] Refiere dolor epigástrico después de comer")
    assert r.status_code == 201
    guardada = next(n for n in repo.notas.values() if n.id == r.json()["id"])
    assert "epigástrico" not in guardada.model_dump_json()  # también se cifran
    med = client.get(f"/api/pacientes/{cita['paciente_id']}/historial", "med-luis").json()["notas"][0]
    pac = client.get(f"/api/pacientes/{cita['paciente_id']}/historial", "pac-rosa").json()["notas"][0]
    assert med["apuntes"].startswith("[02:15]") and "apuntes" not in pac
