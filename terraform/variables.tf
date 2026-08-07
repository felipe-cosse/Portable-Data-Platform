variable "name" {
  description = "Prefix used for platform resources."
  type        = string
  default     = "data-platform"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,28}$", var.name))
    error_message = "name must be 3-29 lowercase letters, numbers, or hyphens."
  }
}

variable "aws_region" {
  description = "AWS Region in which to deploy."
  type        = string
  default     = "us-west-2"
}

variable "architecture" {
  description = "EC2 CPU architecture. Keep this aligned with instance_type."
  type        = string
  default     = "arm64"

  validation {
    condition     = contains(["arm64", "x86_64"], var.architecture)
    error_message = "architecture must be arm64 or x86_64."
  }
}

variable "instance_type" {
  description = "EC2 size. t4g.medium suits the core stack; use at least 8 GiB of memory when enable_metabase is true."
  type        = string
  default     = "t4g.medium"
}

variable "enable_metabase" {
  description = "Start the optional Metabase BI profile. Use an instance with at least 8 GiB of memory."
  type        = bool
  default     = false
}

variable "cpu_credits" {
  description = "T-instance credit mode. Set null when using a non-burstable instance family."
  type        = string
  default     = "standard"

  validation {
    condition     = var.cpu_credits == null || contains(["standard", "unlimited"], var.cpu_credits)
    error_message = "cpu_credits must be standard, unlimited, or null."
  }
}

variable "root_volume_size_gb" {
  description = "Encrypted gp3 root volume size, including Docker and ClickHouse data."
  type        = number
  default     = 80

  validation {
    condition     = var.root_volume_size_gb >= 40
    error_message = "root_volume_size_gb must be at least 40."
  }
}

variable "compose_version" {
  description = "Docker Compose release installed by cloud-init."
  type        = string
  default     = "v5.1.4"
}

variable "bucket_force_destroy" {
  description = "Allow Terraform to delete a non-empty data lake bucket. Keep false for safety."
  type        = bool
  default     = false
}

variable "tags" {
  description = "Additional tags added to all supported resources."
  type        = map(string)
  default     = {}
}
