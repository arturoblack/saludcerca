"""Cliente ASGI mínimo para las pruebas (sin dependencias extra)."""
import asyncio
import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("AUTH_MODE", "dev")

from app.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402
from app.repository import MemoryRepository  # noqa: E402

CLAVE_FHIR = "clave-de-prueba-hospital"
CLAVE_FHIR_SHA256 = __import__("hashlib").sha256(CLAVE_FHIR.encode()).hexdigest()


class Resp:
    def __init__(self, status: int, body: bytes) -> None:
        self.status_code = status
        self.body = body

    def json(self):
        return json.loads(self.body)


class Client:
    def __init__(self, app) -> None:
        self.app = app

    def request(self, method: str, path: str, user: str | None = None, body=None, headers_extra=None) -> Resp:
        headers = [(b"content-type", b"application/json")]
        for k, v in (headers_extra or {}).items():
            headers.append((k.lower().encode(), v.encode()))
        if user:
            headers.append((b"authorization", f"Bearer dev:{user}".encode()))
        payload = json.dumps(body).encode() if body is not None else b""
        path, _, query = path.partition("?")
        scope = {"type": "http", "method": method, "path": path, "raw_path": path.encode(), "query_string": query.encode(),
                 "headers": headers, "http_version": "1.1", "scheme": "http", "server": ("test", 80),
                 "client": ("test", 1234), "root_path": ""}
        out = {"status": 0, "body": b""}
        sent = False

        async def receive():
            nonlocal sent
            if not sent:
                sent = True
                return {"type": "http.request", "body": payload, "more_body": False}
            return {"type": "http.disconnect"}

        async def send(message):
            if message["type"] == "http.response.start":
                out["status"] = message["status"]
            elif message["type"] == "http.response.body":
                out["body"] += message.get("body", b"")

        asyncio.run(self.app(scope, receive, send))
        return Resp(out["status"], out["body"])

    def get(self, path, user=None, headers=None):
        return self.request("GET", path, user, headers_extra=headers)

    def post(self, path, user=None, body=None):
        return self.request("POST", path, user, body if body is not None else {})


@pytest.fixture
def repo():
    return MemoryRepository()


@pytest.fixture
def client(repo):
    return Client(create_app(Settings(auth_mode="dev", storage_backend="memory", seed_demo_data=True,
                                      integration_keys_sha256=CLAVE_FHIR_SHA256), repo))
