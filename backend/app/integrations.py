"""Integraciones con Blob Storage (adjuntos) y Communication Services (videollamada)."""
from __future__ import annotations

import re
from datetime import timedelta

from .config import Settings
from .models import new_id, now_utc

_NOMBRE_SEGURO = re.compile(r"[^A-Za-z0-9._-]+")


def nombre_blob(paciente_id: str, nombre_archivo: str) -> str:
    limpio = _NOMBRE_SEGURO.sub("_", nombre_archivo).strip("._") or "archivo"
    return f"{paciente_id}/{now_utc():%Y%m%d}-{new_id()}-{limpio}"


def url_subida(settings: Settings, paciente_id: str, nombre_archivo: str, minutos: int = 10) -> dict:
    """Devuelve una URL firmada (SAS) de corta duración para subir un adjunto directamente a Blob Storage.

    En Azure se usa una *user delegation key* obtenida con la Managed Identity de la función,
    así no existe ninguna clave de cuenta en la configuración.
    """
    blob = nombre_blob(paciente_id, nombre_archivo)
    expira = now_utc() + timedelta(minutes=minutos)
    if settings.blob_connection_string:  # emulador local: sube a través de la API con la cadena de conexión
        return {"blob": blob, "upload_url": f"/api/dev/blob/{blob}", "expira": expira.isoformat(), "modo": "emulador"}
    if not settings.blob_account_url:
        return {"blob": blob, "upload_url": f"/api/dev/blob/{blob}", "expira": expira.isoformat(), "modo": "simulado"}

    from azure.identity import DefaultAzureCredential  # pragma: no cover
    from azure.storage.blob import BlobSasPermissions, BlobServiceClient, generate_blob_sas  # pragma: no cover

    service = BlobServiceClient(settings.blob_account_url, credential=DefaultAzureCredential())  # pragma: no cover
    key = service.get_user_delegation_key(now_utc() - timedelta(minutes=5), expira)  # pragma: no cover
    sas = generate_blob_sas(  # pragma: no cover
        account_name=service.account_name, container_name=settings.blob_container, blob_name=blob,
        user_delegation_key=key, permission=BlobSasPermissions(create=True, write=True), expiry=expira,
    )
    url = f"{settings.blob_account_url.rstrip('/')}/{settings.blob_container}/{blob}?{sas}"  # pragma: no cover
    return {"blob": blob, "upload_url": url, "expira": expira.isoformat(), "modo": "azure"}  # pragma: no cover


def token_videollamada(settings: Settings, cita_id: str, usuario_id: str) -> dict:
    """Emite una identidad y un token de ACS válidos para unirse a la sala de la cita."""
    sala = f"cita-{cita_id}"
    if not (settings.acs_connection_string or settings.acs_endpoint):
        return {"sala": sala, "token": f"demo-token-{usuario_id}", "acs_user_id": f"demo:{usuario_id}",
                "expira": (now_utc() + timedelta(hours=1)).isoformat(), "modo": "simulado"}

    from azure.communication.identity import CommunicationIdentityClient, CommunicationTokenScope  # pragma: no cover

    if settings.acs_connection_string:  # pragma: no cover
        client = CommunicationIdentityClient.from_connection_string(settings.acs_connection_string)
    else:  # pragma: no cover
        from azure.identity import DefaultAzureCredential
        client = CommunicationIdentityClient(settings.acs_endpoint, DefaultAzureCredential())
    user, token = client.create_user_and_token(scopes=[CommunicationTokenScope.VOIP],  # pragma: no cover
                                               token_expires_in=timedelta(hours=1))
    return {"sala": sala, "token": token.token, "acs_user_id": user.properties["id"],  # pragma: no cover
            "expira": token.expires_on.isoformat(), "modo": "azure"}
