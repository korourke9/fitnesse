terraform {
  required_version = ">= 1.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  
  backend "s3" {
    bucket  = "fitnesse-terraform-state"
    key     = "terraform.tfstate"
    region  = "us-east-2"  # Must match the bucket region
    # Note: Credentials are provided via environment variables
    # Run: source setup-credentials.sh before terraform commands
  }
}

provider "aws" {
  region = var.aws_region
  # Credentials are provided via environment variables
  # Run: source setup-credentials.sh before terraform commands
  
  default_tags {
    tags = {
      Project     = "Fitnesse"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}

# Data sources
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

locals {
  account_id = data.aws_caller_identity.current.account_id
  region     = data.aws_region.current.name
  
  common_tags = {
    Project     = "Fitnesse"
    Environment = var.environment
  }
}

