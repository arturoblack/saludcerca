"""Cifrado del contenido clínico a nivel de aplicación (AES-256-GCM).

Además del cifrado en reposo de Cosmos DB, el diagnóstico, las indicaciones, la receta y
los signos vitales se cifran antes de guardarse: quien tenga acceso directo a la base de
datos solo ve texto cifrado. La llave (32 bytes en hexadecimal) vive en Key Vault y llega a
la función como RECORD_ENC_KEY mediante una referencia de Key Vault.

Formato: v1.<nonce>.<texto cifrado + etiqueta>, en base64url. Los datos asociados (AAD) son
"<paciente_id>:<id_nota>", así un registro cifrado no puede copiarse a otro paciente.
"""
from __future__ import annotations

import base64
import json
import logging
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

log = logging.getLogger("saludcerca.cifrado")

# Llave SOLO para la demo local (AUTH_MODE=dev). En Azure la configuración exige RECORD_ENC_KEY.
_LLAVE_DEMO = "00" * 16 + "5a" * 16


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


class Cifrador:
    def __init__(self, llave_hex: str) -> None:
        llave = bytes.fromhex(llave_hex)
        if len(llave) != 32:
            raise ValueError("RECORD_ENC_KEY debe tener 32 bytes (64 caracteres hexadecimales)")
        self._aes = AESGCM(llave)

    def cifrar(self, datos: dict, contexto: str) -> str:
        nonce = os.urandom(12)
        ct = self._aes.encrypt(nonce, json.dumps(datos, ensure_ascii=False).encode(), contexto.encode())
        return f"v1.{_b64(nonce)}.{_b64(ct)}"

    def descifrar(self, token: str, contexto: str) -> dict:
        version, nonce, ct = token.split(".")
        if version != "v1":
            raise ValueError(f"versión de cifrado desconocida: {version}")
        return json.loads(self._aes.decrypt(_unb64(nonce), _unb64(ct), contexto.encode()))


def build_cifrador(llave_hex: str, es_dev: bool) -> Cifrador:
    if not llave_hex:
        if not es_dev:
            raise RuntimeError("Falta RECORD_ENC_KEY: no se puede guardar información clínica sin llave de cifrado")
        log.warning("Usando la llave de cifrado de demostración (solo para entorno local)")
        llave_hex = _LLAVE_DEMO
    return Cifrador(llave_hex)
