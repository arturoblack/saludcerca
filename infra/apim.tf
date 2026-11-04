# ---------- API Management (Consumption): puerta única de la API ----------
# ponytail: Consumption no ofrece rate-limit-by-key; el límite por IP lo aplica el WAF de Front Door.
# Quien llame directo a la Function App igual debe presentar un token válido.
resource "azurerm_api_management" "api" {
  name                = "apim-${local.nombre}-${random_string.sufijo.result}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  publisher_name      = "SaludCerca"
  publisher_email     = var.apim_publisher_email
  sku_name            = "Consumption_0"
  tags                = local.tags
}

resource "azurerm_api_management_api" "api" {
  name                  = "saludcerca"
  resource_group_name   = azurerm_resource_group.rg.name
  api_management_name   = azurerm_api_management.api.name
  revision              = "1"
  display_name          = "SaludCerca"
  path                  = "api"
  protocols             = ["https"]
  service_url           = "https://${azurerm_function_app_flex_consumption.api.default_hostname}/api"
  subscription_required = false
}

resource "azurerm_api_management_api_operation" "todas" {
  for_each            = toset(["GET", "POST", "PUT", "DELETE", "OPTIONS"])
  operation_id        = lower(each.key)
  api_name            = azurerm_api_management_api.api.name
  api_management_name = azurerm_api_management.api.name
  resource_group_name = azurerm_resource_group.rg.name
  display_name        = each.key
  method              = each.key
  url_template        = "/*"
}

locals {
  entra_configurado = var.entra_tenant_id != "00000000-0000-0000-0000-000000000000"
  origenes_xml      = join("", [for o in local.web_origenes : "<origin>${o}</origin>"])
  # La salud del servicio y FHIR (clave de integración) no usan token de Entra.
  validar_jwt_xml = <<-XML
    <choose>
      <when condition="@(context.Request.Method != &quot;OPTIONS&quot; &amp;&amp; !context.Request.Url.Path.Contains(&quot;/fhir/&quot;) &amp;&amp; !context.Request.Url.Path.EndsWith(&quot;/health&quot;))">
        <validate-jwt header-name="Authorization" failed-validation-httpcode="401" failed-validation-error-message="Token inválido">
          <openid-config url="https://${var.entra_tenant_subdomain}.ciamlogin.com/${var.entra_tenant_id}/v2.0/.well-known/openid-configuration" />
          <audiences><audience>${var.entra_api_client_id}</audience></audiences>
        </validate-jwt>
      </when>
    </choose>
  XML
  validar_jwt     = local.entra_configurado ? local.validar_jwt_xml : ""
}

resource "azurerm_api_management_api_policy" "api" {
  api_name            = azurerm_api_management_api.api.name
  api_management_name = azurerm_api_management.api.name
  resource_group_name = azurerm_resource_group.rg.name
  xml_content         = <<-XML
    <policies>
      <inbound>
        <base />
        <cors>
          <allowed-origins>${local.origenes_xml}</allowed-origins>
          <allowed-methods><method>GET</method><method>POST</method><method>PUT</method><method>DELETE</method></allowed-methods>
          <allowed-headers><header>authorization</header><header>content-type</header><header>x-api-key</header></allowed-headers>
        </cors>
        ${local.validar_jwt}
      </inbound>
      <backend><base /></backend>
      <outbound><base /></outbound>
      <on-error><base /></on-error>
    </policies>
  XML
  depends_on          = [azurerm_api_management_api_operation.todas]
}
