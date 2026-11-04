output "resource_group" {
  value = azurerm_resource_group.rg.name
}

output "function_app_name" {
  value = azurerm_function_app_flex_consumption.api.name
}

output "api_url" {
  description = "Puerta de enlace de API Management: es la URL que usa la PWA."
  value       = azurerm_api_management.api.gateway_url
}

output "function_host" {
  value = azurerm_function_app_flex_consumption.api.default_hostname
}

output "web_storage_account" {
  value = azurerm_storage_account.web.name
}

output "web_url" {
  value = var.habilitar_front_door ? "https://${azurerm_cdn_frontdoor_endpoint.web[0].host_name}" : "https://${azurerm_storage_account.web.primary_web_host}"
}

output "cosmos_endpoint" {
  value = azurerm_cosmosdb_account.db.endpoint
}
