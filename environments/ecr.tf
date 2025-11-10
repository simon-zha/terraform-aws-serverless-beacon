variable "manage_ecr" {
  description = "Whether this workspace manages (creates) ECR repositories"
  type        = bool
  default     = false
}

variable "ecr_repos" {
  description = "All service ECR repository names (one repo per service)"
  type        = list(string)
  default     = [
    "sbeacon-analytics-lambda-containers",
    "sbeacon-askbeacon-lambda-containers",
  ]
}

resource "aws_ecr_repository" "repos" {
  count                 = var.manage_ecr ? length(var.ecr_repos) : 0
  name                  = var.ecr_repos[count.index]
  image_tag_mutability  = "MUTABLE"
  image_scanning_configuration { scan_on_push = true }
  encryption_configuration      { encryption_type = "AES256" } 
}

resource "aws_ecr_lifecycle_policy" "policies" {
  count      = var.manage_ecr ? length(var.ecr_repos) : 0
  repository = aws_ecr_repository.repos[count.index].name
  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last tagged images for dev-/gh-/v"
        selection = {
          tagStatus        = "tagged"
          tagPrefixList    = ["dev-","gh-","v"]
          countType        = "imageCountMoreThan"
          countNumber      = var.retain_tagged
        }
        action = { type = "expire" }
      },
      {
        rulePriority = 99
        description  = "Expire untagged images after N days"
        selection = {
          tagStatus   = "untagged"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = var.expire_untagged_after_days
        }
        action = { type = "expire" }
      }
    ]
  })
}

data "aws_caller_identity" "me" {}

output "ecr_registry_url" {
  value = "${data.aws_caller_identity.me.account_id}.dkr.ecr.${var.region}.amazonaws.com"
}

output "ecr_repository_urls" {
  value = [for name in var.ecr_repos :
    "${data.aws_caller_identity.me.account_id}.dkr.ecr.${var.region}.amazonaws.com/${name}"
  ]
}
