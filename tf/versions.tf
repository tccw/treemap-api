terraform {
  cloud {
    organization = "street-trees"
    workspaces {
      name = "trees"
    }
  }
}

terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~>3.42.0"
    }
  }
}
