"""Autenticación y autorización.

- AUTH_MODE=entra: valida el JWT (firma, emisor, audiencia y vencimiento) emitido por
  Microsoft Entra External ID. El rol sale del claim `roles` (App Roles: Paciente, Medico, Admin).
- AUTH_MODE=dev: acepta `Bearer dev:<id_usuario>` para la demo local. Nunca se habilita en Azure
  (Terraform fija AUTH_MODE=entra).
"""
from __future__ import annotations

import functools
import logging
import unicodedata

import jwt
from starlette.requests import Request

from .config import Settings
from .models import Canal, Rol, Usuario
from .repository import Repository


log = logging.getLogger("saludcerca.auth")


def _normalizar(t: str) -> str:
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower().strip()
    return " ".join(t.replace("_", " ").split())


def _usuario_de_prueba(claims: dict, repo: Repository) -> Usuario | None:
    """Solo en pruebas locales (AUTH_MODE=oidc): reconoce al usuario de la demo a partir de lo que se
    escribió en el proveedor de prueba: el id exacto (pac-juan), el id sin prefijo (juan) o el nombre."""
    valores = {_normalizar(str(claims[c])) for c in ("sub", "preferred_username", "username", "name", "email")
               if claims.get(c)}
    valores |= {v.split("@")[0] for v in valores}
    usuarios = repo.list_usuarios()
    for v in valores:  # 1) id exacto
        if (u := next((x for x in usuarios if x.id == v), None)):
            return u
    candidatos = []
    for u in usuarios:  # 2) id sin prefijo o nombre/apellido
        sin_prefijo = u.id.split("-", 1)[-1]
        nombre = _normalizar(u.nombre).replace("dr. ", "").replace("dra. ", "")
        if any(v and (v == sin_prefijo or v == nombre or nombre.split()[0] == v or v in nombre.split()) for v in valores):
            candidatos.append(u)
    return candidatos[0] if len(candidatos) == 1 else None


class AuthError(Exception):
    def __init__(self, status: int, detail: str) -> None:
        super().__init__(detail)
        self.status = status
        self.detail = detail


@functools.lru_cache(maxsize=4)
def _jwks_client(jwks_url: str) -> jwt.PyJWKClient:
    return jwt.PyJWKClient(jwks_url, cache_keys=True)


def _validar_entra(token: str, s: Settings) -> dict:
    base = f"https://{s.entra_tenant_subdomain}.ciamlogin.com/{s.entra_tenant_id}"
    signing_key = _jwks_client(f"{base}/discovery/v2.0/keys").get_signing_key_from_jwt(token)
    return jwt.decode(
        token, signing_key.key, algorithms=["RS256"], audience=s.entra_api_client_id,
        issuer=f"https://{s.entra_tenant_id}.ciamlogin.com/{s.entra_tenant_id}/v2.0",
        options={"require": ["exp", "iat", "sub"]},
    )


def _validar_oidc(token: str, s: Settings) -> dict:
    """Proveedor OIDC genérico (pruebas locales con mock-oauth2-server, Keycloak, etc.)."""
    signing_key = _jwks_client(s.oidc_jwks_url).get_signing_key_from_jwt(token)
    opciones = {"require": ["exp", "iat", "sub"], "verify_aud": bool(s.oidc_audience)}
    return jwt.decode(token, signing_key.key, algorithms=["RS256", "ES256"], issuer=s.oidc_issuer,
                      audience=s.oidc_audience or None, options=opciones)


def _rol_desde_claims(claims: dict) -> Rol:
    roles = {r.lower() for r in claims.get("roles", [])}
    if "admin" in roles:
        return Rol.admin
    if "medico" in roles:
        return Rol.medico
    return Rol.paciente


def usuario_actual(request: Request, s: Settings, repo: Repository) -> Usuario:
    header = request.headers.get("authorization", "")
    if not header.lower().startswith("bearer "):
        raise AuthError(401, "Falta el token de acceso")
    token = header[7:].strip()

    if s.auth_mode == "dev":
        if not token.startswith("dev:"):
            raise AuthError(401, "Token de demostración inválido")
        usuario = repo.get_usuario(token[4:])
        if usuario is None:
            raise AuthError(401, "Usuario de demostración no encontrado")
        return usuario

    try:
        claims = _validar_oidc(token, s) if s.auth_mode == "oidc" else _validar_entra(token, s)
    except jwt.PyJWTError as exc:
        raise AuthError(401, f"Token inválido: {exc}") from exc

    usuario_id = claims["oid"] if "oid" in claims else claims["sub"]
    usuario = repo.get_usuario(usuario_id)
    if usuario is None and s.auth_mode == "oidc":
        usuario = _usuario_de_prueba(claims, repo)
        if usuario:
            log.info("login de prueba: '%s' reconocido como %s (%s)", claims.get("sub"), usuario.id, usuario.nombre)
        else:
            log.warning("login de prueba: '%s' no coincide con ningún usuario de la demo; se crea un paciente nuevo "
                        "que solo recibe avisos en la app. Escriba p. ej. pac-juan o med-cesar.", claims.get("sub"))
    if usuario is None:  # primer ingreso: alta automática con el rol asignado en Entra
        usuario = repo.upsert_usuario(Usuario(
            id=usuario_id, nombre=claims.get("name", "Usuario"), rol=_rol_desde_claims(claims),
            email=claims.get("email") or claims.get("preferred_username"), canal_preferido=Canal.app,
        ))
    return usuario


def exigir_rol(usuario: Usuario, *roles: Rol) -> None:
    if usuario.rol not in roles:
        raise AuthError(403, "No tiene permiso para esta operación")
