"""Modo OIDC genérico (mock-oauth2-server) y notificador SMTP (Mailpit) usados en pruebas locales."""
import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from app import auth
from app.config import Settings
from app.main import create_app
from app.messaging import SmtpNotifier
from app.models import Canal
from app.repository import MemoryRepository
from conftest import Client

ISSUER = "http://localhost:8090/default"
CLAVE = rsa.generate_private_key(public_exponent=65537, key_size=2048)


class _Llave:
    key = CLAVE.public_key()


@pytest.fixture
def oidc_client(monkeypatch):
    monkeypatch.setattr(auth, "_jwks_client", lambda url: type("J", (), {"get_signing_key_from_jwt": lambda self, t: _Llave()})())
    s = Settings(auth_mode="oidc", oidc_issuer=ISSUER, oidc_jwks_url="http://oidc:8080/default/jwks", storage_backend="memory")
    return Client(create_app(s, MemoryRepository()))


def _token(sub: str, iss: str = ISSUER, exp: int = 300) -> str:
    ahora = int(time.time())
    return jwt.encode({"sub": sub, "iss": iss, "iat": ahora, "exp": ahora + exp, "aud": "saludcerca-web"}, CLAVE, algorithm="RS256")


def _get(client, path, token):
    return client.request("GET", path, headers_extra={"Authorization": f"Bearer {token}"})


def test_oidc_token_valido_inicia_sesion_como_usuario_sembrado(oidc_client):
    r = _get(oidc_client, "/api/me", _token("pac-rosa"))
    assert r.status_code == 200 and r.json()["nombre"] == "Rosa Quispe Mamani"


def test_oidc_rechaza_emisor_ajeno_y_token_vencido(oidc_client):
    assert _get(oidc_client, "/api/me", _token("pac-rosa", iss="http://otro/default")).status_code == 401
    assert _get(oidc_client, "/api/me", _token("pac-rosa", exp=-10)).status_code == 401


def test_oidc_no_acepta_tokens_de_demo(oidc_client):
    assert _get(oidc_client, "/api/me", "dev:pac-rosa").status_code == 401


def test_smtp_envia_sms_como_correo(monkeypatch):
    enviados = []

    class FakeSMTP:
        def __init__(self, host, port, timeout):
            self.destino = (host, port)

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def send_message(self, msg):
            enviados.append((self.destino, msg["To"], msg["Subject"], msg.get_content()))

    monkeypatch.setattr("smtplib.SMTP", FakeSMTP)
    n = SmtpNotifier(Settings(smtp_host="mailpit", smtp_port=1025))
    n.send(Canal.sms, "+51900000002", "x", "Su cita es mañana")
    n.send(Canal.app, "pac-rosa", "Turnos", "copia del aviso en la app")
    assert enviados == [
        (("mailpit", 1025), "51900000002@sms.saludcerca.local", "SMS para +51900000002", "Su cita es mañana\n"),
        (("mailpit", 1025), "pac-rosa@app.saludcerca.local", "[Aviso en la app] Turnos", "copia del aviso en la app\n"),
    ]


def test_si_el_smtp_falla_la_reserva_igual_se_guarda(monkeypatch):
    def caido(*a, **k):
        raise ConnectionRefusedError("mailpit apagado")
    monkeypatch.setattr("smtplib.SMTP", caido)
    repo = MemoryRepository()
    c = Client(create_app(Settings(auth_mode="dev", notifier_backend="smtp", storage_backend="memory"), repo))
    from test_api import turno
    r = c.post("/api/citas", "pac-juan", {"medico_id": "med-luis", "fecha_hora": turno(c, "med-luis")})
    assert r.status_code == 201


def test_health_informa_el_canal_de_avisos():
    c = Client(create_app(Settings(auth_mode="dev", notifier_backend="smtp", storage_backend="memory"), MemoryRepository()))
    assert c.get("/api/health").json()["avisos"] == "smtp"


@pytest.mark.parametrize("escrito", ["pac-juan", "juan", "Juan", "Juan Ccahuana Huamán", "ccahuana"])
def test_login_de_prueba_reconoce_al_usuario_de_la_demo(oidc_client, escrito):
    r = _get(oidc_client, "/api/me", _token(escrito))
    assert r.status_code == 200 and r.json()["id"] == "pac-juan" and r.json()["canal_preferido"] == "sms"


def test_login_de_prueba_ambiguo_crea_paciente_nuevo(oidc_client):
    # "luis" es único; "dr" no identifica a nadie en particular -> paciente nuevo
    assert _get(oidc_client, "/api/me", _token("luis")).json()["id"] == "med-luis"
    assert _get(oidc_client, "/api/me", _token("alguien-nuevo")).json()["rol"] == "paciente"
