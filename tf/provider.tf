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
    cors {
      allowed_origins = [var.CROSS_ORIGIN_DOMAIN]
    }
  }

  app_settings = {
    CLOUDINARY_URL             = var.CLOUDINARY_URL
    CLOUDINARY_NAME            = var.CLOUDINARY_NAME
    CLOUDINARY_API_KEY         = var.CLOUDINARY_API_KEY
    CLOUDINARY_API_SECRET      = var.CLOUDINARY_API_SECRET
    CONTENT_MODERATOR_KEY1     = var.CONTENT_MODERATOR_KEY1
    CONTENT_MODERATOR_ENDPOINT = var.CONTENT_MODERATOR_ENDPOINT
    COSMOSDB_CONN_STR          = var.COSMOSDB_CONN_STR
    CROSS_ORIGIN_DOMAIN        = var.CROSS_ORIGIN_DOMAIN
    TIME_OFFSET_DAYS           = var.TIME_OFFSET_DAYS
  }

  tags = {
    Product = "Treemap"
  }
}

#  Deploy code from a public GitHub repo
# resource "azurerm_app_service_source_control" "sourcecontrol" {
#   app_id             = azurerm_linux_web_app.treemap.id
#   repo_url           = "https://github.com/tccw/treemap-api"
#   branch             = "main"
#   use_manual_integration = true
#   use_mercurial      = false
# }

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
    consistency_level = "BoundedStaleness"
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