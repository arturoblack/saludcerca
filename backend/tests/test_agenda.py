from datetime import datetime, time, timedelta

from app.agenda import turnos_libres
from app.messaging import LIMA
from app.models import Agenda, Bloque, Cita
from test_api import turno


def _proximo(dia_semana: int) -> datetime:
    hoy = datetime.now(LIMA).date() + timedelta(days=2)
    return datetime.combine(hoy + timedelta(days=(dia_semana - hoy.weekday()) % 7), time(0), tzinfo=LIMA)


def test_turnos_respetan_bloques_duracion_y_ocupados():
    lunes = _proximo(0)
    ag = Agenda(id="m", medico_id="m", duracion_min=30, bloques=[Bloque(dia=0, inicio=time(8), fin=time(10))])
    ocupada = Cita(paciente_id="p", medico_id="m", especialidad="x", fecha_hora=lunes.replace(hour=9))
    libres = turnos_libres(ag, [ocupada], lunes.date(), 7)
    horas = [t.strftime("%H:%M") for t in libres]
    assert horas == ["08:00", "08:30", "09:30"]  # 09:00 ocupado; 10:00 queda fuera (el turno terminaría 10:30)


def test_dia_bloqueado_no_ofrece_turnos():
    lunes = _proximo(0)
    ag = Agenda(id="m", medico_id="m", bloques=[Bloque(dia=0, inicio=time(8), fin=time(12))], dias_bloqueados=[lunes.date()])
    assert turnos_libres(ag, [], lunes.date(), 1) == []


def test_especialidades_y_filtro_de_medicos(client):
    esp = {e["especialidad"]: e["medicos"] for e in client.get("/api/especialidades", "pac-rosa").json()}
    assert esp["Medicina general"] == 2 and "Pediatría" in esp
    meds = client.get("/api/medicos?especialidad=Pediatr%C3%ADa", "pac-rosa").json()
    assert [m["id"] for m in meds] == ["med-ana"] and meds[0]["tiene_horario"]


def test_disponibilidad_por_especialidad_reune_varios_medicos(client):
    desde = (datetime.now(LIMA) + timedelta(days=2)).date().isoformat()
    dias = client.get(f"/api/disponibilidad?especialidad=Medicina%20general&desde={desde}&dias=7", "pac-rosa").json()["dias"]
    medicos = {t["medico_id"] for d in dias for t in d["turnos"]}
    assert medicos == {"med-luis", "med-elena"} and len(dias) == 7


def test_reserva_fuera_de_horario_se_rechaza(client):
    domingo_3am = _proximo(6).replace(hour=3).isoformat()
    r = client.post("/api/citas", "pac-rosa", {"medico_id": "med-luis", "fecha_hora": domingo_3am})
    assert r.status_code == 409 and "horario" in r.json()["error"]


def test_turno_reservado_desaparece_de_la_disponibilidad(client):
    t = turno(client, "med-jorge")
    assert client.post("/api/citas", "pac-rosa", {"medico_id": "med-jorge", "fecha_hora": t}).status_code == 201
    assert turno(client, "med-jorge") != t


def test_medico_define_su_horario(client):
    nuevo = {"duracion_min": 20, "bloques": [{"dia": 2, "inicio": "15:00", "fin": "17:00"}], "dias_bloqueados": []}
    r = client.request("PUT", "/api/medicos/me/agenda", "med-elena", nuevo)
    assert r.status_code == 200 and r.json()["agenda"]["duracion_min"] == 20
    horas = {t[11:16] for t in [turno(client, "med-elena", i) for i in range(6)]}
    assert horas == {"15:00", "15:20", "15:40", "16:00", "16:20", "16:40"}


def test_horario_invalido_o_superpuesto(client):
    malo = {"bloques": [{"dia": 1, "inicio": "09:00", "fin": "12:00"}, {"dia": 1, "inicio": "11:00", "fin": "13:00"}]}
    assert client.request("PUT", "/api/medicos/me/agenda", "med-luis", malo).status_code == 422
    assert client.request("PUT", "/api/medicos/me/agenda", "med-luis", {"bloques": [{"dia": 1, "inicio": "12:00", "fin": "09:00"}]}).status_code == 422


def test_paciente_no_edita_horarios(client):
    assert client.request("PUT", "/api/medicos/me/agenda", "pac-rosa", {"bloques": []}).status_code == 403
