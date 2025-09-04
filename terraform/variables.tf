# Variables for AWS Modern Data Lake Foundation

variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
  
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "modern-data-lake"
  
  validation {
    condition     = can(regex("^[a-z0-9-]+$", var.project_name))
    error_message = "Project name must contain only lowercase letters, numbers, and hyphens."
  }
}

variable "data_retention_days" {
  description = "Number of days to retain data in bronze layer"
  type        = number
  default     = 2555  # 7 years for compliance
  
  validation {
    condition     = var.data_retention_days > 0 && var.data_retention_days <= 3650
    error_message = "Data retention must be between 1 and 3650 days."
  }
}

variable "enable_versioning" {
  description = "Enable S3 bucket versioning"
  type        = bool
  default     = true
}

variable "enable_encryption" {
  description = "Enable S3 bucket encryption"
  type        = bool
  default     = true
}

variable "enable_access_logging" {
  description = "Enable S3 access logging"
  type        = bool
  default     = true
}

variable "enable_lifecycle_management" {
  description = "Enable S3 lifecycle management"
  type        = bool
  default     = true
}

variable "ia_transition_days" {
  description = "Days before transitioning to Infrequent Access storage"
  type        = number
  default     = 30
}

variable "glacier_transition_days" {
  description = "Days before transitioning to Glacier storage"
  type        = number
  default     = 90
}

variable "deep_archive_transition_days" {
  description = "Days before transitioning to Deep Archive storage"
  type        = number
  default     = 365
}

variable "glue_crawler_schedule" {
  description = "Schedule for Glue crawler (cron expression)"
  type        = string
  default     = "cron(0 1 * * ? *)"  # Daily at 1 AM
}

variable "enable_cloudwatch_logs" {
  description = "Enable CloudWatch logging for Glue jobs"
  type        = bool
  default     = true
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 30
}

variable "tags" {
  description = "Additional tags to apply to resources"
  type        = map(string)
  default = {
    "Project"    = "Modern Data Lake"
    "ManagedBy"  = "Terraform"
    "Owner"      = "DataEngineering"
  }
}

# Data processing configuration
variable "spark_config" {
  description = "Spark configuration for Glue jobs"
  type = object({
    worker_type       = string
    number_of_workers = number
    max_capacity      = number
    timeout           = number
  })
  default = {
    worker_type       = "G.1X"
    number_of_workers = 2
    max_capacity      = 10
    timeout           = 2880  # 48 hours
  }
}

# Security configuration
variable "kms_key_deletion_window" {
  description = "KMS key deletion window in days"
  type        = number
  default     = 7
  
  validation {
    condition     = var.kms_key_deletion_window >= 7 && var.kms_key_deletion_window <= 30
    error_message = "KMS key deletion window must be between 7 and 30 days."
  }
}

variable "enable_mfa_delete" {
  description = "Enable MFA delete for S3 buckets"
  type        = bool
  default     = false  # Requires root account access
}

# Monitoring and alerting
variable "enable_sns_notifications" {
  description = "Enable SNS notifications for alerts"
  type        = bool
  default     = true
}

variable "notification_email" {
  description = "Email address for notifications"
  type        = string
  default     = ""
}

# Cost optimization
variable "enable_intelligent_tiering" {
  description = "Enable S3 Intelligent Tiering"
  type        = bool
  default     = true
}

variable "enable_cost_anomaly_detection" {
  description = "Enable AWS Cost Anomaly Detection"
  type        = bool
  default     = true
}
