terraform {
  required_version = ">= 1.9"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.50"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
    time = {
      source  = "hashicorp/time"
      version = "~> 0.12"
    }
  }

  # Estado remoto en Blob Storage. Se completa con: terraform init -backend-config=backend.hcl
  backend "azurerm" {}
}

provider "azurerm" {
  features {
    key_vault {
      purge_soft_delete_on_destroy = false
    }
    resource_group {
      prevent_deletion_if_contains_resources = true
    }
  }
  # Sin claves de cuenta: Terraform usa Entra ID para las operaciones de datos de Storage.
  storage_use_azuread = true
  subscription_id     = var.subscription_id
}
