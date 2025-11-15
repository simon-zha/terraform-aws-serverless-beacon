# ../locals.naming.tf 
locals {
  env_in = lower(trimspace(coalesce(var.beacon_environment, terraform.workspace)))

  env_map          = { dev = "dev", staging = "staging", prod = "prod" }
  environment_slug = lookup(local.env_map, local.env_in, "dev")

  environment_snake     = replace(local.environment_slug, "-", "_")
  environment_suffix    = "-${local.environment_slug}"
  environment_suffix_sn = "_${local.environment_snake}"
  environment_suffix_up = "-${upper(local.environment_slug)}"
  environment_suffix_no = local.environment_slug
  environment_prefix    = "sbeacon-${local.environment_slug}"
}
