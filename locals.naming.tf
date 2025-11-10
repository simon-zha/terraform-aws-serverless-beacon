locals {
  environment_slug_initial = regexreplace(lower(var.beacon_environment), "[^0-9a-z-]", "-")
  environment_slug_collapsed = regexreplace(local.environment_slug_initial, "-{2,}", "-")
  environment_slug_trimmed_head = regexreplace(local.environment_slug_collapsed, "^-", "")
  environment_slug_trimmed = regexreplace(local.environment_slug_trimmed_head, "-$", "")
  environment_slug = length(local.environment_slug_trimmed) > 0 ? local.environment_slug_trimmed : "env"

  environment_snake     = replace(local.environment_slug, "-", "_")
  environment_suffix    = "-${local.environment_slug}"
  environment_suffix_sn = "_${local.environment_snake}"
  environment_suffix_up = "-${upper(local.environment_slug)}"
  environment_suffix_no = "${local.environment_slug}"
  environment_prefix    = "sbeacon-${local.environment_slug}"
}

