def test_paciente_cambia_a_sms_y_recibe_avisos_por_sms(client, repo):
    r = client.request("PUT", "/api/me", "pac-rosa", {"telefono": "987 654 321", "email": "", "canal_preferido": "sms"})
    assert r.status_code == 200 and r.json()["telefono"] == "+51987654321" and r.json()["canal_preferido"] == "sms"
    s = client.post("/api/avisos-disponibilidad", "pac-rosa", {"especialidad": "Cardiología"})
    assert s.status_code == 201
    client.request("PUT", "/api/medicos/me/agenda", "med-cesar",
                   {"duracion_min": 30, "bloques": [{"dia": d, "inicio": "08:00", "fin": "12:00"} for d in range(7)]})
    aviso = next(n for n in repo.list_notificaciones("pac-rosa") if n.tipo == "disponibilidad")
    assert aviso.canal.value == "sms" and aviso.destino == "+51987654321"


def test_sms_sin_telefono_se_rechaza(client):
    r = client.request("PUT", "/api/me", "pac-rosa", {"telefono": "", "canal_preferido": "sms"})
    assert r.status_code == 422 and "celular" in r.body.decode()


def test_telefono_y_correo_invalidos(client):
    assert client.request("PUT", "/api/me", "pac-rosa", {"telefono": "12", "canal_preferido": "app"}).status_code == 422
    assert client.request("PUT", "/api/me", "pac-rosa", {"email": "no-es-correo", "canal_preferido": "app"}).status_code == 422


def test_cada_usuario_solo_cambia_sus_datos(client):
    client.request("PUT", "/api/me", "pac-juan", {"email": "juan@example.com", "telefono": "+51900000002", "canal_preferido": "email"})
    assert client.get("/api/me", "pac-rosa").json()["email"] == "rosa.demo@example.com"
    assert client.get("/api/me", "pac-juan").json()["canal_preferido"] == "email"


def test_sin_consentimiento_no_reserva_ni_pide_avisos(client):
    assert client.get("/api/me", "pac-maria").json()["consentimiento_en"] is None
    r = client.post("/api/avisos-disponibilidad", "pac-maria", {"especialidad": "Cardiología"})
    assert r.status_code == 403 and "datos personales" in r.body.decode()
    assert client.post("/api/me/consentimiento", "pac-maria", {"acepta": False}).status_code == 422
    assert client.get("/api/me", "pac-maria").json()["consentimiento_en"] is None

    primero = client.post("/api/me/consentimiento", "pac-maria", {"acepta": True}).json()
    assert primero["consentimiento_en"] and primero["consentimiento_version"]
    assert client.post("/api/avisos-disponibilidad", "pac-maria", {"especialidad": "Cardiología"}).status_code == 201
    # aceptar otra vez o cambiar el perfil no altera la fecha original
    assert client.post("/api/me/consentimiento", "pac-maria", {"acepta": True}).json()["consentimiento_en"] == primero["consentimiento_en"]
    r = client.request("PUT", "/api/me", "pac-maria", {"telefono": "+51900000003", "canal_preferido": "sms"})
    assert r.json()["consentimiento_en"] == primero["consentimiento_en"]
