variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "fitnesse"
}

variable "database_name" {
  description = "Database name"
  type        = string
  default     = "fitnesse"
}

variable "database_username" {
  description = "Database master username"
  type        = string
  default     = "fitnesse_admin"
  sensitive   = true
}

variable "database_password" {
  description = "Database master password"
  type        = string
  sensitive   = true
}

variable "allowed_cidr_blocks" {
  description = "CIDR blocks allowed to access the application"
  type        = list(string)
  default     = ["0.0.0.0/0"] # Restrict this in production
}

variable "domain_name" {
  description = "Domain name for HTTPS certificate (optional, leave empty to use HTTP only)"
  type        = string
  default     = ""
}


