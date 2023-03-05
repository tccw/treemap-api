# Configure the AWS Provider
provider "azurerm" {
  features {}
}

resource "azurerm_resource_group" "treemap" {
  name     = "treemap-resources"
  location = "Canada Central"
}

resource "azurerm_service_plan" "treemap" {
  name                = "treemap-services-plan"
  resource_group_name = azurerm_resource_group.treemap.name
  location            = azurerm_resource_group.treemap.location
  os_type             = "Linux"
  sku_name            = "F1"

  tags = {
    Product = "Treemap"
  }
}

resource "azurerm_linux_web_app" "treemap" {
  name                = "treemap-api"
  resource_group_name = azurerm_resource_group.treemap.name
  location            = azurerm_resource_group.treemap.location
  service_plan_id     = azurerm_service_plan.treemap.id

  site_config {
    always_on = false
    application_stack {
      python_version = 3.11
    }
  }

  tags = {
    Product = "Treemap"
  }


}

resource "azurerm_cognitive_account" "treemap" {
  name                = "treemap-account"
  location            = azurerm_resource_group.treemap.location
  resource_group_name = azurerm_resource_group.treemap.name
  kind                = "ContentModerator"

  sku_name = "F0"

  tags = {
    Product = "Treemap"
  }
}

resource "azurerm_cosmosdb_account" "db" {
  name                = "cosmos-db-treemap"
  location            = azurerm_resource_group.treemap.location
  resource_group_name = azurerm_resource_group.treemap.name
  offer_type          = "Standard"
  kind                = "MongoDB"

  enable_automatic_failover = true
  enable_free_tier          = true
  # mongo_server_version = 4.0

  consistency_policy {
    consistency_level       = "BoundedStaleness"
  }

  capabilities {
    name = "mongoEnableDocLevelTTL"
  }

  capabilities {
    name = "MongoDBv3.4"
  }

  capabilities {
    name = "EnableMongo"
  }

  # primary location
  geo_location {
    location          = "canadacentral"
    failover_priority = 0
  }

}