output "resource_group" {
  value = azurerm_resource_group.rg.name
}

output "function_app_name" {
  value = azurerm_function_app_flex_consumption.api.name
}

output "api_url" {
  value = "https://${azurerm_function_app_flex_consumption.api.default_hostname}"
}

output "web_url" {
  value = var.habilitar_front_door ? "https://${azurerm_cdn_frontdoor_endpoint.web[0].host_name}" : "https://${azurerm_static_web_app.web.default_host_name}"
}

output "swa_deployment_token" {
  value     = azurerm_static_web_app.web.api_key
  sensitive = true
}

output "cosmos_endpoint" {
  value = azurerm_cosmosdb_account.db.endpoint
}
