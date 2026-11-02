HORARIO = {"duracion_min": 30, "bloques": [{"dia": d, "inicio": "08:00", "fin": "12:00"} for d in range(6)], "dias_bloqueados": []}


def _avisos(repo, paciente):
    return [n for n in repo.list_notificaciones(paciente) if n.tipo == "disponibilidad"]


def test_suscripcion_sin_duplicados(client):
    a = client.post("/api/avisos-disponibilidad", "pac-juan", {"especialidad": "Cardiología"})
    b = client.post("/api/avisos-disponibilidad", "pac-juan", {"especialidad": "Cardiología"})
    assert a.status_code == 201 and b.status_code == 200 and a.json()["id"] == b.json()["id"]


def test_si_ya_hay_turnos_no_hace_falta_suscribirse(client):
    r = client.post("/api/avisos-disponibilidad", "pac-rosa", {"especialidad": "Pediatría"})
    assert r.status_code == 409


def test_especialidad_fuera_del_catalogo(client):
    assert client.post("/api/avisos-disponibilidad", "pac-rosa", {"especialidad": "Astrología"}).status_code == 422


def test_nuevo_medico_con_horario_avisa_por_sms(client, repo):
    client.post("/api/avisos-disponibilidad", "pac-juan", {"especialidad": "Cardiología"})
    r = client.post("/api/medicos", "admin-ong", {"nombre": "Dr. Raúl Quispe Arce", "especialidad": "Cardiología",
                                                   "horario_inicial": HORARIO})
    assert r.status_code == 201
    avisos = _avisos(repo, "pac-juan")
    assert len(avisos) == 1 and avisos[0].canal.value == "sms" and "Cardiología" in avisos[0].mensaje
    sol = client.get("/api/avisos-disponibilidad", "pac-juan").json()[0]
    assert sol["estado"] == "notificada"
    # se avisa una sola vez
    client.request("PUT", "/api/medicos/me/agenda", r.json()["id"], HORARIO)
    assert len(_avisos(repo, "pac-juan")) == 1


def test_medico_sin_horario_avisa_cuando_lo_publica(client, repo):
    client.post("/api/avisos-disponibilidad", "pac-rosa", {"especialidad": "Psicología"})
    med = client.post("/api/medicos", "admin-ong", {"nombre": "Lic. Carmen Rojas Vela", "especialidad": "Psicología"}).json()
    assert _avisos(repo, "pac-rosa") == []
    client.request("PUT", "/api/medicos/me/agenda", med["id"], HORARIO)
    assert len(_avisos(repo, "pac-rosa")) == 1


def test_aviso_para_un_medico_concreto(client, repo):
    client.request("PUT", "/api/medicos/me/agenda", "med-elena", {"bloques": []})
    r = client.post("/api/avisos-disponibilidad", "pac-rosa", {"especialidad": "Medicina general", "medico_id": "med-elena"})
    assert r.status_code == 201
    client.request("PUT", "/api/medicos/me/agenda", "med-luis", HORARIO)  # otro médico: no cuenta
    assert _avisos(repo, "pac-rosa") == []
    client.request("PUT", "/api/medicos/me/agenda", "med-elena", HORARIO)
    assert len(_avisos(repo, "pac-rosa")) == 1 and "Elena" in _avisos(repo, "pac-rosa")[0].mensaje


def test_cancelar_suscripcion(client, repo):
    s = client.post("/api/avisos-disponibilidad", "pac-juan", {"especialidad": "Dermatología"}).json()
    assert client.post(f"/api/avisos-disponibilidad/{s['id']}/cancelar", "pac-juan").status_code == 200
    client.post("/api/medicos", "admin-ong", {"nombre": "Dra. Sofía Paredes Luna", "especialidad": "Dermatología",
                                             "horario_inicial": HORARIO})
    assert _avisos(repo, "pac-juan") == []


def test_solo_coordinacion_registra_medicos(client):
    body = {"nombre": "Dr. Falso Médico Uno", "especialidad": "Cardiología"}
    assert client.post("/api/medicos", "med-luis", body).status_code == 403
    assert client.post("/api/medicos", "pac-rosa", body).status_code == 403


def test_especialidades_incluye_las_que_no_tienen_medicos(client):
    esp = {e["especialidad"]: e["medicos"] for e in client.get("/api/especialidades", "pac-rosa").json()}
    assert esp["Dermatología"] == 0 and esp["Cardiología"] == 1 and esp["Pediatría"] == 1


def test_coordinacion_ve_demanda_sin_datos_personales(client):
    client.post("/api/avisos-disponibilidad", "pac-juan", {"especialidad": "Nutrición"})
    client.post("/api/avisos-disponibilidad", "pac-rosa", {"especialidad": "Nutrición"})
    r = client.get("/api/avisos-disponibilidad", "admin-ong").json()
    assert {"especialidad": "Nutrición", "pendientes": 2} in r and "paciente_id" not in str(r)


def test_cardiologo_sin_horario_no_ofrece_turnos_y_avisa_al_publicarlo(client, repo):
    meds = client.get("/api/medicos?especialidad=Cardiolog%C3%ADa", "pac-juan").json()
    assert [(m["id"], m["tiene_horario"]) for m in meds] == [("med-cesar", False)]
    assert client.post("/api/avisos-disponibilidad", "pac-juan", {"especialidad": "Cardiología"}).status_code == 201
    client.request("PUT", "/api/medicos/me/agenda", "med-cesar", HORARIO)  # el Dr. Mendoza publica su horario
    avisos = _avisos(repo, "pac-juan")
    assert len(avisos) == 1 and "César Mendoza" in avisos[0].mensaje
