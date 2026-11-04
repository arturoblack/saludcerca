# ---------- Azure Policy: gobierno y cumplimiento sobre el grupo de recursos ----------
# Iniciativa integrada HIPAA/HITRUST (auditoría continua; no bloquea despliegues).
resource "azurerm_resource_group_policy_assignment" "hipaa" {
  name                 = "hipaa-hitrust"
  display_name         = "HITRUST/HIPAA"
  resource_group_id    = azurerm_resource_group.rg.id
  policy_definition_id = "/providers/Microsoft.Authorization/policySetDefinitions/a169a624-5599-4385-a696-c8d643089fab"
  location             = azurerm_resource_group.rg.location

  identity {
    type = "SystemAssigned"
  }
}

# Residencia de datos: los recursos regionales solo pueden crearse en la región elegida.
resource "azurerm_resource_group_policy_assignment" "regiones" {
  name                 = "regiones-permitidas"
  display_name         = "Regiones permitidas"
  resource_group_id    = azurerm_resource_group.rg.id
  policy_definition_id = "/providers/Microsoft.Authorization/policyDefinitions/e56962a6-4747-49cd-b67b-bf8b01975c4c"
  parameters           = jsonencode({ listOfAllowedLocations = { value = [var.location] } })
}
