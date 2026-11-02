"""Configuración de la aplicación leída desde variables de entorno.

En Azure, estas variables son App Settings de la Function App (definidas por Terraform).
En local, se toman de `.env` o del entorno; por defecto todo corre en memoria.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field


def _bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "si", "sí"}


@dataclass(frozen=True)
class Settings:
    # "dev": tokens de demostración (dev:<id_usuario>). "entra": JWT de Microsoft Entra External ID.
    # "oidc": cualquier proveedor OpenID Connect (p. ej. mock-oauth2-server para pruebas locales).
    auth_mode: str = field(default_factory=lambda: os.getenv("AUTH_MODE", "dev"))
    entra_tenant_subdomain: str = field(default_factory=lambda: os.getenv("ENTRA_TENANT_SUBDOMAIN", ""))
    entra_tenant_id: str = field(default_factory=lambda: os.getenv("ENTRA_TENANT_ID", ""))
    entra_api_client_id: str = field(default_factory=lambda: os.getenv("ENTRA_API_CLIENT_ID", ""))

    oidc_issuer: str = field(default_factory=lambda: os.getenv("OIDC_ISSUER", ""))
    oidc_jwks_url: str = field(default_factory=lambda: os.getenv("OIDC_JWKS_URL", ""))
    oidc_audience: str = field(default_factory=lambda: os.getenv("OIDC_AUDIENCE", ""))

    # "memory" (demo local) o "cosmos" (Azure Cosmos DB con Managed Identity).
    storage_backend: str = field(default_factory=lambda: os.getenv("STORAGE_BACKEND", "memory"))
    cosmos_endpoint: str = field(default_factory=lambda: os.getenv("COSMOS_ENDPOINT", ""))
    cosmos_database: str = field(default_factory=lambda: os.getenv("COSMOS_DATABASE", "saludcerca"))
    # Solo para emuladores (floci-az): clave de la cuenta. En Azure se deja vacío y se usa Managed Identity.
    cosmos_key: str = field(default_factory=lambda: os.getenv("COSMOS_KEY", ""))
    cosmos_auto_create: bool = field(default_factory=lambda: _bool("COSMOS_AUTO_CREATE", False))

    # "inline" (procesa el evento en el mismo proceso) o "servicebus".
    messaging_backend: str = field(default_factory=lambda: os.getenv("MESSAGING_BACKEND", "inline"))
    servicebus_namespace: str = field(default_factory=lambda: os.getenv("SERVICEBUS_FQDN", ""))
    servicebus_queue: str = field(default_factory=lambda: os.getenv("SERVICEBUS_QUEUE", "notificaciones"))
    servicebus_connection_string: str = field(default_factory=lambda: os.getenv("SERVICEBUS_CONNECTION_STRING", ""))

    # "console" (registra el aviso), "smtp" (bandeja local tipo Mailpit) o "acs" (Azure Communication Services).
    notifier_backend: str = field(default_factory=lambda: os.getenv("NOTIFIER_BACKEND", "console"))
    acs_endpoint: str = field(default_factory=lambda: os.getenv("ACS_ENDPOINT", ""))
    acs_connection_string: str = field(default_factory=lambda: os.getenv("ACS_CONNECTION_STRING", ""))
    acs_sms_from: str = field(default_factory=lambda: os.getenv("ACS_SMS_FROM", ""))
    acs_email_from: str = field(default_factory=lambda: os.getenv("ACS_EMAIL_FROM", ""))

    smtp_host: str = field(default_factory=lambda: os.getenv("SMTP_HOST", "localhost"))
    smtp_port: int = field(default_factory=lambda: int(os.getenv("SMTP_PORT", "1025")))
    smtp_from: str = field(default_factory=lambda: os.getenv("SMTP_FROM", "SaludCerca <avisos@saludcerca.local>"))

    blob_account_url: str = field(default_factory=lambda: os.getenv("BLOB_ACCOUNT_URL", ""))
    blob_container: str = field(default_factory=lambda: os.getenv("BLOB_CONTAINER", "documentos"))
    blob_connection_string: str = field(default_factory=lambda: os.getenv("BLOB_CONNECTION_STRING", ""))

    # Llave AES-256 (64 hex) del contenido clínico; en Azure llega desde Key Vault.
    record_enc_key: str = field(default_factory=lambda: os.getenv("RECORD_ENC_KEY", ""))
    # Hash SHA-256 (hex) de las claves de integración FHIR, separados por comas.
    integration_keys_sha256: str = field(default_factory=lambda: os.getenv("INTEGRATION_KEYS_SHA256", ""))

    seed_demo_data: bool = field(default_factory=lambda: _bool("SEED_DEMO_DATA", True))
    reminder_hours_before: int = field(default_factory=lambda: int(os.getenv("REMINDER_HOURS_BEFORE", "24")))

    @property
    def is_dev(self) -> bool:
        return self.auth_mode == "dev"

    @property
    def es_local(self) -> bool:
        """Entorno local de pruebas (cualquier modo que no sea Entra en Azure)."""
        return self.auth_mode != "entra"


def get_settings() -> Settings:
    return Settings()
