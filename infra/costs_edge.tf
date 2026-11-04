# ---------- Control de costos ----------
resource "azurerm_consumption_budget_resource_group" "mensual" {
  name              = "budget-${local.nombre}"
  resource_group_id = azurerm_resource_group.rg.id
  amount            = var.presupuesto_mensual_usd
  time_grain        = "Monthly"

  time_period {
    start_date = var.presupuesto_inicio
  }

  dynamic "notification" {
    for_each = { "50" = "Actual", "80" = "Actual", "100" = "Forecasted" }
    content {
      enabled        = length(var.correos_alerta) > 0
      threshold      = tonumber(notification.key)
      operator       = "GreaterThanOrEqualTo"
      threshold_type = notification.value
      contact_emails = var.correos_alerta
    }
  }
}

# ---------- Front Door + WAF (opcional: habilitar_front_door = true) ----------
resource "azurerm_cdn_frontdoor_profile" "fd" {
  count               = var.habilitar_front_door ? 1 : 0
  name                = "afd-${local.nombre}"
  resource_group_name = azurerm_resource_group.rg.name
  sku_name            = "Standard_AzureFrontDoor"
  tags                = local.tags
}

resource "azurerm_cdn_frontdoor_endpoint" "web" {
  count                    = var.habilitar_front_door ? 1 : 0
  name                     = "web-${local.corto}"
  cdn_frontdoor_profile_id = azurerm_cdn_frontdoor_profile.fd[0].id
}

resource "azurerm_cdn_frontdoor_origin_group" "web" {
  count                    = var.habilitar_front_door ? 1 : 0
  name                     = "og-web"
  cdn_frontdoor_profile_id = azurerm_cdn_frontdoor_profile.fd[0].id
  load_balancing {}
  health_probe {
    protocol            = "Https"
    path                = "/"
    request_type        = "HEAD"
    interval_in_seconds = 120
  }
}

resource "azurerm_cdn_frontdoor_origin" "swa" {
  count                          = var.habilitar_front_door ? 1 : 0
  name                           = "swa"
  cdn_frontdoor_origin_group_id  = azurerm_cdn_frontdoor_origin_group.web[0].id
  enabled                        = true
  host_name                      = azurerm_storage_account.web.primary_web_host
  origin_host_header             = azurerm_storage_account.web.primary_web_host
  certificate_name_check_enabled = true
}

resource "azurerm_cdn_frontdoor_route" "web" {
  count                         = var.habilitar_front_door ? 1 : 0
  name                          = "route-web"
  cdn_frontdoor_endpoint_id     = azurerm_cdn_frontdoor_endpoint.web[0].id
  cdn_frontdoor_origin_group_id = azurerm_cdn_frontdoor_origin_group.web[0].id
  cdn_frontdoor_origin_ids      = [azurerm_cdn_frontdoor_origin.swa[0].id]
  patterns_to_match             = ["/*"]
  supported_protocols           = ["Https", "Http"]
  https_redirect_enabled        = true
  forwarding_protocol           = "HttpsOnly"
  cache {
    query_string_caching_behavior = "IgnoreQueryString"
    compression_enabled           = true
    content_types_to_compress     = ["text/html", "text/css", "application/javascript", "application/json", "image/svg+xml"]
  }
}

resource "azurerm_cdn_frontdoor_firewall_policy" "waf" {
  count               = var.habilitar_front_door ? 1 : 0
  name                = "waf${var.proyecto}${var.entorno}"
  resource_group_name = azurerm_resource_group.rg.name
  sku_name            = "Standard_AzureFrontDoor"
  mode                = "Prevention"

  custom_rule {
    name                           = "LimiteSolicitudes"
    type                           = "RateLimitRule"
    priority                       = 1
    action                         = "Block"
    rate_limit_duration_in_minutes = 1
    rate_limit_threshold           = 300
    match_condition {
      match_variable = "RemoteAddr"
      operator       = "IPMatch"
      match_values   = ["0.0.0.0/0", "::/0"]
    }
  }

  custom_rule {
    name     = "SoloPaisesPermitidos"
    type     = "MatchRule"
    priority = 2
    action   = "Block"
    match_condition {
      match_variable     = "SocketAddr"
      operator           = "GeoMatch"
      negation_condition = true
      match_values       = var.paises_permitidos
    }
  }
}

resource "azurerm_cdn_frontdoor_security_policy" "waf" {
  count                    = var.habilitar_front_door ? 1 : 0
  name                     = "sp-waf"
  cdn_frontdoor_profile_id = azurerm_cdn_frontdoor_profile.fd[0].id
  security_policies {
    firewall {
      cdn_frontdoor_firewall_policy_id = azurerm_cdn_frontdoor_firewall_policy.waf[0].id
      association {
        patterns_to_match = ["/*"]
        domain {
          cdn_frontdoor_domain_id = azurerm_cdn_frontdoor_endpoint.web[0].id
        }
      }
    }
  }
}
