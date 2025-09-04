# AWS Modern Data Lake Foundation
# Main Terraform configuration

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Project     = "Modern-Data-Lake"
      Environment = var.environment
      Owner       = "DataEngineering"
      ManagedBy   = "Terraform"
    }
  }
}

# S3 Buckets for Data Lake Layers
resource "aws_s3_bucket" "bronze_bucket" {
  bucket = "${var.project_name}-bronze-${var.environment}-${random_id.bucket_suffix.hex}"
  
  tags = {
    Name = "Bronze Layer - Raw Data"
    Layer = "Bronze"
  }
}

resource "aws_s3_bucket" "silver_bucket" {
  bucket = "${var.project_name}-silver-${var.environment}-${random_id.bucket_suffix.hex}"
  
  tags = {
    Name = "Silver Layer - Standardized Data"
    Layer = "Silver"
  }
}

resource "aws_s3_bucket" "gold_bucket" {
  bucket = "${var.project_name}-gold-${var.environment}-${random_id.bucket_suffix.hex}"
  
  tags = {
    Name = "Gold Layer - Analytics Ready"
    Layer = "Gold"
  }
}

# Random ID for unique bucket names
resource "random_id" "bucket_suffix" {
  byte_length = 4
}

# S3 Bucket Versioning
resource "aws_s3_bucket_versioning" "bronze_versioning" {
  bucket = aws_s3_bucket.bronze_bucket.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_versioning" "silver_versioning" {
  bucket = aws_s3_bucket.silver_bucket.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_versioning" "gold_versioning" {
  bucket = aws_s3_bucket.gold_bucket.id
  versioning_configuration {
    status = "Enabled"
  }
}

# S3 Bucket Encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "bronze_encryption" {
  bucket = aws_s3_bucket.bronze_bucket.id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.s3_key.arn
      sse_algorithm     = "aws:kms"
    }
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "silver_encryption" {
  bucket = aws_s3_bucket.silver_bucket.id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.s3_key.arn
      sse_algorithm     = "aws:kms"
    }
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "gold_encryption" {
  bucket = aws_s3_bucket.gold_bucket.id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.s3_key.arn
      sse_algorithm     = "aws:kms"
    }
  }
}

# KMS Key for S3 Encryption
resource "aws_kms_key" "s3_key" {
  description             = "KMS key for S3 bucket encryption"
  deletion_window_in_days = 7
  
  tags = {
    Name = "S3 Data Lake Encryption Key"
  }
}

resource "aws_kms_alias" "s3_key_alias" {
  name          = "alias/${var.project_name}-s3-key"
  target_key_id = aws_kms_key.s3_key.key_id
}

# S3 Lifecycle Configuration
resource "aws_s3_bucket_lifecycle_configuration" "bronze_lifecycle" {
  bucket = aws_s3_bucket.bronze_bucket.id

  rule {
    id     = "bronze_lifecycle_rule"
    status = "Enabled"

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 90
      storage_class = "GLACIER"
    }

    transition {
      days          = 365
      storage_class = "DEEP_ARCHIVE"
    }
  }
}

# Glue Database
resource "aws_glue_catalog_database" "data_lake_database" {
  name        = "${var.project_name}_database"
  description = "Data Lake catalog database"
  
  parameters = {
    "classification" = "parquet"
  }
}

# IAM Role for Glue
resource "aws_iam_role" "glue_role" {
  name = "${var.project_name}-glue-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "glue.amazonaws.com"
        }
      }
    ]
  })
}

# IAM Policy for Glue
resource "aws_iam_role_policy" "glue_policy" {
  name = "${var.project_name}-glue-policy"
  role = aws_iam_role.glue_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.bronze_bucket.arn,
          "${aws_s3_bucket.bronze_bucket.arn}/*",
          aws_s3_bucket.silver_bucket.arn,
          "${aws_s3_bucket.silver_bucket.arn}/*",
          aws_s3_bucket.gold_bucket.arn,
          "${aws_s3_bucket.gold_bucket.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey"
        ]
        Resource = [
          aws_kms_key.s3_key.arn
        ]
      }
    ]
  })
}

# Attach Glue Service Role Policy
resource "aws_iam_role_policy_attachment" "glue_service_role" {
  role       = aws_iam_role.glue_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
}
