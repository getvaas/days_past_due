terraform {
  required_version = ">= 1.3"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }

  # Backend S3 con config parcial: se pasa con
  #   terraform init -backend-config=configuration/<env>/backend.conf
  backend "s3" {}
}

provider "aws" {
  region  = var.aws_region
  profile = var.profile

  default_tags {
    tags = {
      Environment   = var.environment
      Author        = var.author
      CostCenter    = var.cost_center
      ProjectName   = var.project_name_camel_case
      ComponentName = var.component_name_camel_case
      GithubRepo    = var.github_repository
    }
  }
}
