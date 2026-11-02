# ---------- Key Vault: secretos fuera del código y de la configuración ----------
resource "azurerm_key_vault" "kv" {
  name                       = substr("kv-${local.corto}", 0, 24)
  location                   = azurerm_resource_group.rg.location
  resource_group_name        = azurerm_resource_group.rg.name
  tenant_id                  = data.azurerm_client_config.actual.tenant_id
  sku_name                   = "standard"
  rbac_authorization_enabled = true
  purge_protection_enabled   = true
  soft_delete_retention_days = 30
  tags                       = local.tags
}

# Quien ejecuta Terraform (pipeline) puede escribir secretos.
resource "azurerm_role_assignment" "deployer_kv" {
  scope                = azurerm_key_vault.kv.id
  role_definition_name = "Key Vault Secrets Officer"
  principal_id         = data.azurerm_client_config.actual.object_id
}

resource "time_sleep" "rbac_kv" {
  depends_on      = [azurerm_role_assignment.deployer_kv]
  create_duration = "60s" # propagación de RBAC
}

resource "azurerm_key_vault_secret" "acs" {
  name         = "acs-connection-string"
  value        = azurerm_communication_service.acs.primary_connection_string
  key_vault_id = azurerm_key_vault.kv.id
  content_type = "connection-string"
  depends_on   = [time_sleep.rbac_kv]
}

# Llave AES-256 del contenido clínico (cifrado a nivel de aplicación). Se genera una vez y
# nunca sale de Key Vault; rotarla exige volver a cifrar las notas (ver README).
resource "random_id" "record_key" {
  byte_length = 32
}

resource "azurerm_key_vault_secret" "record_key" {
  name         = "record-enc-key"
  value        = random_id.record_key.hex
  key_vault_id = azurerm_key_vault.kv.id
  content_type = "aes-256-gcm-hex"
  depends_on   = [time_sleep.rbac_kv]
  lifecycle {
    prevent_destroy = true
  }
}

# ---------- Mínimo privilegio para la identidad administrada de la Function App ----------
locals {
  fn_principal = azurerm_function_app_flex_consumption.api.identity[0].principal_id
  roles_fn     = {
    host_storage = { scope = azurerm_storage_account.func.id, role = "Storage Blob Data Owner" }
    docs_blob    = { scope = azurerm_storage_account.docs.id, role = "Storage Blob Data Contributor" }
    docs_sas     = { scope = azurerm_storage_account.docs.id, role = "Storage Blob Delegator" }
    sb_sender    = { scope = azurerm_servicebus_namespace.sb.id, role = "Azure Service Bus Data Sender" }
    sb_receiver  = { scope = azurerm_servicebus_namespace.sb.id, role = "Azure Service Bus Data Receiver" }
    kv_secrets   = { scope = azurerm_key_vault.kv.id, role = "Key Vault Secrets User" }
    monitoring   = { scope = azurerm_application_insights.ai.id, role = "Monitoring Metrics Publisher" }
  }
}

resource "azurerm_role_assignment" "fn" {
  for_each             = local.roles_fn
  scope                = each.value.scope
  role_definition_name = each.value.role
  principal_id         = local.fn_principal
}

# Cosmos DB usa su propio RBAC de plano de datos: "Cosmos DB Built-in Data Contributor".
resource "azurerm_cosmosdb_sql_role_assignment" "fn" {
  resource_group_name = azurerm_resource_group.rg.name
  account_name        = azurerm_cosmosdb_account.db.name
  role_definition_id  = "${azurerm_cosmosdb_account.db.id}/sqlRoleDefinitions/00000000-0000-0000-0000-000000000002"
  principal_id        = local.fn_principal
  scope               = azurerm_cosmosdb_account.db.id
}

# ---------- Auditoría: registros de diagnóstico hacia Log Analytics ----------
resource "azurerm_monitor_diagnostic_setting" "cosmos" {
  name                       = "diag-cosmos"
  target_resource_id         = azurerm_cosmosdb_account.db.id
  log_analytics_workspace_id = azurerm_log_analytics_workspace.logs.id
  enabled_log {
    category = "DataPlaneRequests"
  }
}

resource "azurerm_monitor_diagnostic_setting" "kv" {
  name                       = "diag-kv"
  target_resource_id         = azurerm_key_vault.kv.id
  log_analytics_workspace_id = azurerm_log_analytics_workspace.logs.id
  enabled_log {
    category = "AuditEvent"
  }
}

resource "azurerm_monitor_diagnostic_setting" "docs" {
  name                       = "diag-docs-blob"
  target_resource_id         = "${azurerm_storage_account.docs.id}/blobServices/default"
  log_analytics_workspace_id = azurerm_log_analytics_workspace.logs.id
  enabled_log {
    category = "StorageRead"
  }
  enabled_log {
    category = "StorageWrite"
  }
}
