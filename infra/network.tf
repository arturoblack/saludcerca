# ---------- Red privada: Cosmos DB y la cuenta interna solo aceptan tráfico por Private Endpoint ----------
resource "azurerm_virtual_network" "vnet" {
  name                = "vnet-${local.nombre}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  address_space       = ["10.20.0.0/16"]
  tags                = local.tags
}

resource "azurerm_subnet" "fn" {
  name                            = "snet-funciones"
  resource_group_name             = azurerm_resource_group.rg.name
  virtual_network_name            = azurerm_virtual_network.vnet.name
  address_prefixes                = ["10.20.1.0/24"]
  default_outbound_access_enabled = true # Functions llega a Service Bus, ACS y Key Vault por sus puntos públicos

  delegation {
    name = "flex"
    service_delegation {
      name    = "Microsoft.App/environments"
      actions = ["Microsoft.Network/virtualNetworks/subnets/join/action"]
    }
  }
}

resource "azurerm_subnet" "pe" {
  name                 = "snet-endpoints"
  resource_group_name  = azurerm_resource_group.rg.name
  virtual_network_name = azurerm_virtual_network.vnet.name
  address_prefixes     = ["10.20.2.0/24"]
}

locals {
  endpoints = {
    cosmos     = { recurso = azurerm_cosmosdb_account.db.id, grupo = "Sql", zona = "privatelink.documents.azure.com" }
    func-blob  = { recurso = azurerm_storage_account.func.id, grupo = "blob", zona = "privatelink.blob.core.windows.net" }
    func-queue = { recurso = azurerm_storage_account.func.id, grupo = "queue", zona = "privatelink.queue.core.windows.net" }
  }
  zonas = toset([for e in local.endpoints : e.zona])
}

resource "azurerm_private_dns_zone" "z" {
  for_each            = local.zonas
  name                = each.key
  resource_group_name = azurerm_resource_group.rg.name
  tags                = local.tags
}

resource "azurerm_private_dns_zone_virtual_network_link" "z" {
  for_each              = local.zonas
  name                  = "vnet"
  resource_group_name   = azurerm_resource_group.rg.name
  private_dns_zone_name = azurerm_private_dns_zone.z[each.key].name
  virtual_network_id    = azurerm_virtual_network.vnet.id
}

resource "azurerm_private_endpoint" "pe" {
  for_each            = local.endpoints
  name                = "pe-${each.key}-${local.nombre}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  subnet_id           = azurerm_subnet.pe.id
  tags                = local.tags

  private_service_connection {
    name                           = each.key
    private_connection_resource_id = each.value.recurso
    subresource_names              = [each.value.grupo]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "zona"
    private_dns_zone_ids = [azurerm_private_dns_zone.z[each.value.zona].id]
  }
}
