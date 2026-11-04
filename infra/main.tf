data "azurerm_client_config" "actual" {}

resource "random_string" "sufijo" {
  length  = 5
  upper   = false
  special = false
}

locals {
  nombre = "${var.proyecto}-${var.entorno}"
  corto  = "${var.proyecto}${var.entorno}${random_string.sufijo.result}"
  tags = {
    proyecto = var.proyecto
    entorno  = var.entorno
    campana  = var.campana
    datos    = "salud-sensible"
    gestor   = "terraform"
  }
}

resource "azurerm_resource_group" "rg" {
  name     = "rg-${local.nombre}"
  location = var.location
  tags     = local.tags
}

# ---------- Observabilidad ----------
resource "azurerm_log_analytics_workspace" "logs" {
  name                = "log-${local.nombre}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  sku                 = "PerGB2018"
  retention_in_days   = 90
  daily_quota_gb      = 1 # techo de ingesta para controlar costos
  tags                = local.tags
}

resource "azurerm_application_insights" "ai" {
  name                = "appi-${local.nombre}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  workspace_id        = azurerm_log_analytics_workspace.logs.id
  application_type    = "web"
  tags                = local.tags
}

# ---------- Almacenamiento ----------
# Cuenta interna de Azure Functions (paquetes de despliegue y estado del host).
resource "azurerm_storage_account" "func" {
  name                            = substr("stfn${local.corto}", 0, 24)
  location                        = azurerm_resource_group.rg.location
  resource_group_name             = azurerm_resource_group.rg.name
  account_tier                    = "Standard"
  account_replication_type        = "LRS"
  min_tls_version                 = "TLS1_2"
  allow_nested_items_to_be_public = false
  shared_access_key_enabled       = false
  public_network_access_enabled   = false # solo por Private Endpoint (network.tf)
  tags                            = local.tags
}

resource "azurerm_storage_container" "deploy" {
  name                  = "deployments"
  storage_account_id    = azurerm_storage_account.func.id
  container_access_type = "private"
}

# PWA: sitio web estático por HTTPS. Static Web Apps no está disponible en las regiones que permite
# Azure for Students; el sitio se activa y se publica en el pipeline (plano de datos).
resource "azurerm_storage_account" "web" {
  name                            = substr("stweb${local.corto}", 0, 24)
  location                        = azurerm_resource_group.rg.location
  resource_group_name             = azurerm_resource_group.rg.name
  account_tier                    = "Standard"
  account_replication_type        = "LRS"
  min_tls_version                 = "TLS1_2"
  allow_nested_items_to_be_public = false
  shared_access_key_enabled       = false
  tags                            = local.tags
}

resource "azurerm_role_assignment" "deployer_web" {
  scope                = azurerm_storage_account.web.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = data.azurerm_client_config.actual.object_id
}

locals {
  web_origenes = concat(
    ["https://${azurerm_storage_account.web.primary_web_host}"],
    [for e in azurerm_cdn_frontdoor_endpoint.web : "https://${e.host_name}"],
  )
}

# Cuenta de documentos clínicos (resultados, imágenes, PDF).
# Excepción al Private Endpoint: el navegador del paciente sube directo con una SAS de 10 minutos
# limitada a un solo blob, así que el punto de conexión debe ser alcanzable desde internet.
resource "azurerm_storage_account" "docs" {
  name                              = substr("stdoc${local.corto}", 0, 24)
  location                          = azurerm_resource_group.rg.location
  resource_group_name               = azurerm_resource_group.rg.name
  account_tier                      = "Standard"
  account_replication_type          = "ZRS"
  min_tls_version                   = "TLS1_2"
  allow_nested_items_to_be_public   = false
  shared_access_key_enabled         = false # solo Entra ID y SAS de delegación de usuario
  infrastructure_encryption_enabled = true  # doble cifrado AES-256 en reposo
  tags                              = local.tags
  depends_on                        = [time_sleep.rbac_cmk]

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.cmk.id]
  }

  customer_managed_key {
    key_vault_key_id          = azurerm_key_vault_key.cmk.versionless_id
    user_assigned_identity_id = azurerm_user_assigned_identity.cmk.id
  }

  blob_properties {
    versioning_enabled = true
    delete_retention_policy {
      days = 30
    }
    container_delete_retention_policy {
      days = 30
    }
    cors_rule {
      allowed_origins    = local.web_origenes
      allowed_methods    = ["PUT"]
      allowed_headers    = ["content-type", "x-ms-blob-type", "x-ms-version"]
      exposed_headers    = ["etag"]
      max_age_in_seconds = 3600
    }
  }
}

resource "azurerm_storage_container" "documentos" {
  name                  = "documentos"
  storage_account_id    = azurerm_storage_account.docs.id
  container_access_type = "private"
}

# Almacenamiento escalonado: Hot -> Cool (30 d) -> Cold (90 d).
# ponytail: Azure rechaza tierToArchive en esta cuenta (mexicocentral, probado con ZRS y LRS); Archive a 365 d queda como diseño objetivo.
resource "azurerm_storage_management_policy" "escalonado" {
  storage_account_id = azurerm_storage_account.docs.id

  rule {
    name    = "documentos-por-antiguedad"
    enabled = true
    filters {
      blob_types   = ["blockBlob"]
      prefix_match = ["documentos/"]
    }
    actions {
      base_blob {
        tier_to_cool_after_days_since_modification_greater_than = 30
        tier_to_cold_after_days_since_modification_greater_than = 90
      }
      version {
        delete_after_days_since_creation = 365
      }
    }
  }
}

# ---------- Base de datos ----------
resource "azurerm_cosmosdb_account" "db" {
  name                          = "cosmos-${local.nombre}-${random_string.sufijo.result}"
  location                      = azurerm_resource_group.rg.location
  resource_group_name           = azurerm_resource_group.rg.name
  offer_type                    = "Standard"
  kind                          = "GlobalDocumentDB"
  local_authentication_enabled  = false # sin claves: solo Managed Identity (RBAC de datos)
  minimal_tls_version           = "Tls12"
  public_network_access_enabled = false # solo por Private Endpoint (network.tf)
  key_vault_key_id              = azurerm_key_vault_key.cmk.versionless_id
  default_identity_type         = "UserAssignedIdentity=${azurerm_user_assigned_identity.cmk.id}"
  tags                          = local.tags
  depends_on                    = [time_sleep.rbac_cmk]

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.cmk.id]
  }

  capabilities {
    name = "EnableServerless"
  }

  consistency_policy {
    consistency_level = "Session"
  }

  geo_location {
    location          = azurerm_resource_group.rg.location
    failover_priority = 0
  }

  backup {
    type = "Continuous" # restauración a un punto en el tiempo (PITR)
    tier = "Continuous7Days"
  }
}

resource "azurerm_cosmosdb_sql_database" "app" {
  name                = "saludcerca"
  resource_group_name = azurerm_resource_group.rg.name
  account_name        = azurerm_cosmosdb_account.db.name
}

locals {
  contenedores = {
    usuarios       = "/id"
    citas          = "/paciente_id"
    historial      = "/paciente_id"
    notificaciones = "/paciente_id"
    agendas        = "/medico_id"
    solicitudes    = "/especialidad"
  }
}

resource "azurerm_cosmosdb_sql_container" "c" {
  for_each            = local.contenedores
  name                = each.key
  resource_group_name = azurerm_resource_group.rg.name
  account_name        = azurerm_cosmosdb_account.db.name
  database_name       = azurerm_cosmosdb_sql_database.app.name
  partition_key_paths = [each.value]
}

# ---------- Mensajería ----------
resource "azurerm_servicebus_namespace" "sb" {
  name                = "sb-${local.nombre}-${random_string.sufijo.result}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  sku                 = "Basic"
  local_auth_enabled  = false
  minimum_tls_version = "1.2"
  tags                = local.tags
}

resource "azurerm_servicebus_queue" "notificaciones" {
  name                                 = "notificaciones"
  namespace_id                         = azurerm_servicebus_namespace.sb.id
  max_delivery_count                   = 5
  lock_duration                        = "PT1M"
  default_message_ttl                  = "P14D"
  dead_lettering_on_message_expiration = true
}

# ---------- Communication Services (SMS, email, video) ----------
resource "azurerm_communication_service" "acs" {
  name                = "acs-${local.nombre}-${random_string.sufijo.result}"
  resource_group_name = azurerm_resource_group.rg.name
  data_location       = var.acs_data_location
  tags                = local.tags
}

resource "azurerm_email_communication_service" "email" {
  name                = "email-${local.nombre}-${random_string.sufijo.result}"
  resource_group_name = azurerm_resource_group.rg.name
  data_location       = var.acs_data_location
  tags                = local.tags
}

resource "azurerm_email_communication_service_domain" "azure" {
  name              = "AzureManagedDomain"
  email_service_id  = azurerm_email_communication_service.email.id
  domain_management = "AzureManaged"
}

resource "azurerm_communication_service_email_domain_association" "link" {
  communication_service_id = azurerm_communication_service.acs.id
  email_service_domain_id  = azurerm_email_communication_service_domain.azure.id
}

# ---------- Cómputo ----------
resource "azurerm_service_plan" "fn" {
  name                = "asp-${local.nombre}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  os_type             = "Linux"
  sku_name            = "FC1" # Flex Consumption: pago por uso, escala a cero
  tags                = local.tags
}

resource "azurerm_function_app_flex_consumption" "api" {
  name                        = "func-${local.nombre}-${random_string.sufijo.result}"
  location                    = azurerm_resource_group.rg.location
  resource_group_name         = azurerm_resource_group.rg.name
  service_plan_id             = azurerm_service_plan.fn.id
  storage_container_type      = "blobContainer"
  storage_container_endpoint  = "${azurerm_storage_account.func.primary_blob_endpoint}${azurerm_storage_container.deploy.name}"
  storage_authentication_type = "SystemAssignedIdentity"
  runtime_name                = "python"
  runtime_version             = "3.11"
  maximum_instance_count      = var.fn_max_instancias
  instance_memory_in_mb       = var.fn_memoria_mb
  https_only                  = true
  virtual_network_subnet_id   = azurerm_subnet.fn.id
  tags                        = local.tags

  identity {
    type = "SystemAssigned"
  }

  site_config {
    application_insights_connection_string = azurerm_application_insights.ai.connection_string
  }

  app_settings = {
    AzureWebJobsStorage__accountName    = azurerm_storage_account.func.name
    AUTH_MODE                           = var.auth_mode
    ENTRA_TENANT_SUBDOMAIN              = var.entra_tenant_subdomain
    ENTRA_TENANT_ID                     = var.entra_tenant_id
    ENTRA_API_CLIENT_ID                 = var.entra_api_client_id
    STORAGE_BACKEND                     = "cosmos"
    COSMOS_ENDPOINT                     = azurerm_cosmosdb_account.db.endpoint
    COSMOS_DATABASE                     = azurerm_cosmosdb_sql_database.app.name
    MESSAGING_BACKEND                   = "servicebus"
    SERVICEBUS_FQDN                     = "${azurerm_servicebus_namespace.sb.name}.servicebus.windows.net"
    SERVICEBUS_QUEUE                    = azurerm_servicebus_queue.notificaciones.name
    SERVICEBUS__fullyQualifiedNamespace = "${azurerm_servicebus_namespace.sb.name}.servicebus.windows.net"
    NOTIFIER_BACKEND                    = "acs"
    ACS_ENDPOINT                        = "https://${azurerm_communication_service.acs.hostname}"
    ACS_CONNECTION_STRING               = "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault_secret.acs.versionless_id})"
    ACS_SMS_FROM                        = var.acs_sms_from
    ACS_EMAIL_FROM                      = "DoNotReply@${azurerm_email_communication_service_domain.azure.from_sender_domain}"
    BLOB_ACCOUNT_URL                    = azurerm_storage_account.docs.primary_blob_endpoint
    BLOB_CONTAINER                      = azurerm_storage_container.documentos.name
    SEED_DEMO_DATA                      = var.auth_mode == "dev" ? "true" : "false"
    RECORD_ENC_KEY                      = "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault_secret.record_key.versionless_id})"
    INTEGRATION_KEYS_SHA256             = var.integration_keys_sha256
  }
}
