from datetime import datetime, timedelta

import pytest

from app.messaging import LIMA


def turno(client, medico_id: str, n: int = 0, desde_dias: int = 2) -> str:
    """n-ésimo turno libre del médico a partir de pasado mañana (evita depender del día de la semana)."""
    desde = (datetime.now(LIMA) + timedelta(days=desde_dias)).date().isoformat()
    dias = client.get(f"/api/disponibilidad?medico_id={medico_id}&desde={desde}&dias=14", "pac-rosa").json()["dias"]
    return [t["fecha_hora"] for d in dias for t in d["turnos"]][n]


def fecha(dias: int, hora: int = 11) -> str:
    return (datetime.now(LIMA) + timedelta(days=dias)).replace(hour=hora, minute=0, second=0, microsecond=0).isoformat()


def test_health_es_publico(client):
    r = client.get("/api/health")
    assert r.status_code == 200 and r.json()["estado"] == "ok"


def test_sin_token_responde_401(client):
    assert client.get("/api/citas").status_code == 401


def test_paciente_solo_ve_sus_citas(client):
    citas = client.get("/api/citas", "pac-rosa").json()
    assert citas and all(c["paciente_id"] == "pac-rosa" for c in citas)


def test_crear_cita_envia_confirmacion_y_programa_recordatorio(client, repo):
    r = client.post("/api/citas", "pac-rosa", {"medico_id": "med-ana", "fecha_hora": turno(client, "med-ana"), "motivo": "Tos"})
    assert r.status_code == 201, r.body
    cita = r.json()
    assert cita["especialidad"] == "Pediatría" and cita["medico_nombre"].startswith("Dra.")
    avisos = [n for n in repo.list_notificaciones("pac-rosa") if n.cita_id == cita["id"]]
    assert {n.tipo for n in avisos} == {"confirmacion", "recordatorio"}
    assert next(n for n in avisos if n.tipo == "recordatorio").estado == "programada"


def test_paciente_con_telefono_basico_recibe_sms(client, repo):
    # pac-juan prefiere SMS: crea su cita y el aviso sale por ese canal
    r = client.post("/api/citas", "pac-juan", {"medico_id": "med-luis", "fecha_hora": turno(client, "med-luis", 1)})
    assert r.status_code == 201
    conf = next(n for n in repo.list_notificaciones("pac-juan") if n.tipo == "confirmacion")
    assert conf.canal.value == "sms" and conf.destino.startswith("+51")


def test_cita_en_el_pasado_es_rechazada(client):
    r = client.post("/api/citas", "pac-rosa", {"medico_id": "med-luis", "fecha_hora": fecha(-1)})
    assert r.status_code == 422


def test_horario_ocupado_devuelve_409(client):
    body = {"medico_id": "med-luis", "fecha_hora": turno(client, "med-luis", 2)}
    assert client.post("/api/citas", "pac-rosa", body).status_code == 201
    r = client.post("/api/citas", "pac-juan", body)
    assert r.status_code == 409 and "reservado" in r.json()["error"]


def test_medico_no_puede_crear_citas(client):
    assert client.post("/api/citas", "med-luis", {"medico_id": "med-ana", "fecha_hora": turno(client, "med-ana")}).status_code == 403


def test_paciente_no_ve_historial_ajeno(client):
    assert client.get("/api/pacientes/pac-juan/historial", "pac-rosa").status_code == 403
    assert client.get("/api/pacientes/pac-rosa/historial", "pac-rosa").status_code == 200


def test_medico_solo_accede_a_sus_pacientes(client):
    assert client.get("/api/pacientes/pac-rosa/historial", "med-luis").status_code == 200
    assert client.get("/api/pacientes/pac-rosa/historial", "med-ana").status_code == 403


def test_admin_no_lee_historias_clinicas(client):
    assert client.get("/api/pacientes/pac-rosa/historial", "admin-ong").status_code == 403


def test_medico_registra_nota_y_cierra_la_cita(client):
    cita = next(c for c in client.get("/api/citas", "med-luis").json() if c["estado"] == "programada")
    r = client.post(f"/api/pacientes/{cita['paciente_id']}/historial", "med-luis", {
        "cita_id": cita["id"], "motivo": "Control mensual", "diagnostico": "Paciente estable",
        "indicaciones": "Mantener tratamiento"})
    assert r.status_code == 201
    hist = client.get(f"/api/pacientes/{cita['paciente_id']}/historial", "med-luis").json()
    assert hist["notas"][0]["diagnostico"] == "Paciente estable"
    estado = next(c for c in client.get("/api/citas", "med-luis").json() if c["id"] == cita["id"])["estado"]
    assert estado == "atendida"


def test_cancelar_cita_notifica(client, repo):
    cita = client.post("/api/citas", "pac-rosa", {"medico_id": "med-ana", "fecha_hora": turno(client, "med-ana", 3)}).json()
    r = client.post(f"/api/citas/{cita['id']}/cancelar", "pac-rosa")
    assert r.status_code == 200 and r.json()["estado"] == "cancelada"
    assert any(n.tipo == "cancelacion" for n in repo.list_notificaciones("pac-rosa"))
    assert client.post(f"/api/citas/{cita['id']}/cancelar", "pac-rosa").status_code == 409


def test_token_de_videoconsulta_solo_para_participantes(client):
    cita = next(c for c in client.get("/api/citas", "pac-rosa").json() if c["estado"] == "programada")
    ok = client.post(f"/api/citas/{cita['id']}/videoconsulta", "pac-rosa")
    assert ok.status_code == 200 and ok.json()["sala"] == f"cita-{cita['id']}"
    assert client.post(f"/api/citas/{cita['id']}/videoconsulta", "med-luis").json()["grupo"] == ok.json()["grupo"]
    assert client.post(f"/api/citas/{cita['id']}/videoconsulta", "pac-juan").status_code == 404


def test_url_de_subida_limpia_el_nombre(client):
    r = client.post("/api/documentos", "med-luis", {"paciente_id": "pac-rosa", "nombre_archivo": "../ecografía 1.pdf"})
    assert r.status_code == 201
    blob = r.json()["blob"]
    assert blob.startswith("pac-rosa/") and ".." not in blob and " " not in blob


@pytest.mark.parametrize("expira", ["2026-11-03T10:00:00+00:00", __import__("datetime").datetime(2026, 11, 3, 10, tzinfo=__import__("datetime").UTC)])
def test_token_de_video_acepta_el_vencimiento_como_texto_o_fecha(monkeypatch, expira):
    import types

    from app import integrations
    from app.config import Settings

    cliente = types.SimpleNamespace(create_user_and_token=lambda **_: (
        types.SimpleNamespace(properties={"id": "8:acs:1"}), types.SimpleNamespace(token="t", expires_on=expira)))
    modulo = types.SimpleNamespace(
        CommunicationIdentityClient=types.SimpleNamespace(from_connection_string=lambda _: cliente),
        CommunicationTokenScope=types.SimpleNamespace(VOIP="voip"))
    monkeypatch.setitem(__import__("sys").modules, "azure.communication.identity", modulo)
    r = integrations.token_videollamada(Settings(acs_connection_string="endpoint=x"), "c1", "u1")
    assert r["modo"] == "azure" and r["expira"].startswith("2026-11-03T10:00:00") and r["grupo"]
