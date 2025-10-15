terraform {
  required_version = ">= 1.3.7"

  backend "s3" {}
}

variable "region" {
  type        = string
  description = "AWS Region"
  default     = "us-east-1"
}

variable "additional_tags" {
  type        = map(string)
  description = "additional_tags"
  default     = {}
}

variable "beacon_id" {
  type        = string
  description = "Beacon ID"
  default     = null
}

variable "beacon_name" {
  type        = string
  description = "Beacon name"
  default     = null
}

variable "beacon_description" {
  type        = string
  description = "Beacon description"
  default     = null
}

variable "beacon_enable_auth" {
  type        = bool
  description = "authentication enable"
  default     = null
}

variable "beacon_guest_username" {
  type        = string
  description = "guest account"
  default     = null
}

variable "beacon_guest_password" {
  type        = string
  description = "guest password"
  default     = null
}

variable "beacon_admin_username" {
  type        = string
  description = "admin username"
  default     = null
}

variable "beacon_admin_password" {
  type        = string
  description = "admin pass"
  default     = null
}

variable "azure_openai_api_key" {
  type        = string
  description = "Azure OpenAI API Key"
  default     = null
}

variable "azure_openai_endpoint" {
  type        = string
  description = "Azure OpenAI Endpoint"
  default     = null
}

variable "azure_openai_api_version" {
  type        = string
  description = "Azure OpenAI API version"
  default     = null
}

variable "azure_openai_chat_deployment_name" {
  type        = string
  description = "Azure OpenAI Chat deployment name"
  default     = null
}

variable "openai_api_key" {
  type        = string
  description = "OpenAI API Key"
  default     = null
}

locals {
  raw_workspace = terraform.workspace
  environment = (length(trimspace(coalesce(local.raw_workspace, ""))) == 0 || local.raw_workspace == "default") ? "dev" : local.raw_workspace

  env_defaults = {
    dev = {
      beacon_enable_auth = false
      beacon_description = "Serverless Beacon DEV environment"
      name_suffix        = "DEV"
    }
    staging = {
      beacon_enable_auth = true
      beacon_description = "Serverless Beacon STAGING environment"
      name_suffix        = "STAGING"
    }
    prod = {
      beacon_enable_auth = true
      beacon_description = "Serverless Beacon PROD environment"
      name_suffix        = "PROD"
    }
  }

  selected_defaults = merge(
    {
      beacon_enable_auth = false
      beacon_description = "Serverless Beacon DEV environment"
      name_suffix        = upper(local.environment)
    },
    lookup(local.env_defaults, local.environment, {})
  )

  base_tags = merge({
    application = "serverless-beacon"
    environment = local.environment
  }, var.additional_tags)
}

module "serverless_beacon" {
  source = ".."

  region      = var.region
  common-tags = local.base_tags

  variants-bucket-prefix      = "sbeacon-${local.environment}-variants-"
  metadata-bucket-prefix      = "sbeacon-${local.environment}-metadata-"
  lambda-layers-bucket-prefix = "sbeacon-${local.environment}-lambda-layers-"

  beacon-environment = local.environment
  beacon-id          = coalesce(var.beacon_id, "au.csiro.serverless-beacon-${local.environment}")
  beacon-name        = coalesce(var.beacon_name, "CSIRO Serverless Beacon (${local.selected_defaults.name_suffix})")
  beacon-description = coalesce(var.beacon_description, local.selected_defaults.beacon_description)
  beacon-enable-auth = coalesce(var.beacon_enable_auth, local.selected_defaults.beacon_enable_auth)

  beacon-guest-username = coalesce(var.beacon_guest_username, "guest+${local.environment}@example.com")
  beacon-guest-password = coalesce(var.beacon_guest_password, "ChangeMe!Guest#${local.environment}")
  beacon-admin-username = coalesce(var.beacon_admin_username, "admin+${local.environment}@example.com")
  beacon-admin-password = coalesce(var.beacon_admin_password, "ChangeMe!Admin#${local.environment}")

  azure-openai-api-key              = var.azure_openai_api_key
  azure-openai-endpoint             = var.azure_openai_endpoint
  azure-openai-api-version          = var.azure_openai_api_version
  azure-openai-chat-deployment-name = var.azure_openai_chat_deployment_name

  openai-api-key = var.openai_api_key
}

