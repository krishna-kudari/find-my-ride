# terraform/main.tf
# Complete AWS Infrastructure for Django on EKS

terraform {
  required_version = ">= 1.6"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.23"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.11"
    }
  }

  # Remote state backend
  backend "s3" {
    bucket         = "your-terraform-state-bucket"
    key            = "production/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-state-lock"
  }
}

provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Environment = var.environment
      Project     = var.project_name
      ManagedBy   = "Terraform"
    }
  }
}

# Data sources
data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_caller_identity" "current" {}

# Local variables
locals {
  cluster_name = "${var.project_name}-${var.environment}-eks"
  
  azs = slice(data.aws_availability_zones.available.names, 0, 3)
  
  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

################################################################################
# VPC Configuration
################################################################################

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name = "${var.project_name}-${var.environment}-vpc"
  cidr = var.vpc_cidr

  azs             = local.azs
  private_subnets = var.private_subnet_cidrs
  public_subnets  = var.public_subnet_cidrs
  
  # Database subnets (isolated from app)
  database_subnets = var.database_subnet_cidrs
  
  # Enable NAT Gateway for private subnets
  enable_nat_gateway   = true
  single_nat_gateway   = var.environment != "production" # Cost optimization
  enable_dns_hostnames = true
  enable_dns_support   = true

  # VPC Flow Logs for security monitoring
  enable_flow_log                      = true
  create_flow_log_cloudwatch_iam_role  = true
  create_flow_log_cloudwatch_log_group = true

  # Tags for EKS
  public_subnet_tags = {
    "kubernetes.io/role/elb"                    = 1
    "kubernetes.io/cluster/${local.cluster_name}" = "shared"
  }

  private_subnet_tags = {
    "kubernetes.io/role/internal-elb"           = 1
    "kubernetes.io/cluster/${local.cluster_name}" = "shared"
  }

  tags = local.tags
}

################################################################################
# EKS Cluster
################################################################################

module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 19.0"

  cluster_name    = local.cluster_name
  cluster_version = "1.28"

  # Cluster endpoint access
  cluster_endpoint_public_access  = true
  cluster_endpoint_private_access = true

  # Encryption
  cluster_encryption_config = {
    resources        = ["secrets"]
    provider_key_arn = module.kms.key_arn
  }

  # Cluster addons
  cluster_addons = {
    coredns = {
      most_recent = true
    }
    kube-proxy = {
      most_recent = true
    }
    vpc-cni = {
      most_recent = true
    }
    aws-ebs-csi-driver = {
      most_recent = true
    }
  }

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  # OIDC Provider for IRSA (IAM Roles for Service Accounts)
  enable_irsa = true

  # Node groups
  eks_managed_node_groups = {
    # General purpose node group
    general = {
      name = "general-purpose"
      
      instance_types = ["t3.medium"]
      capacity_type  = "ON_DEMAND"
      
      min_size     = 2
      max_size     = 10
      desired_size = 3

      labels = {
        role = "general"
      }

      tags = {
        NodeGroup = "general"
      }
    }

    # Spot instances for non-critical workloads
    spot = {
      name = "spot-workers"
      
      instance_types = ["t3.medium", "t3a.medium"]
      capacity_type  = "SPOT"
      
      min_size     = 0
      max_size     = 5
      desired_size = 2

      labels = {
        role = "spot"
      }

      taints = [{
        key    = "spot"
        value  = "true"
        effect = "NoSchedule"
      }]

      tags = {
        NodeGroup = "spot"
      }
    }
  }

  # Manage aws-auth configmap
  manage_aws_auth_configmap = true

  tags = local.tags
}

################################################################################
# KMS for encryption
################################################################################

module "kms" {
  source  = "terraform-aws-modules/kms/aws"
  version = "~> 1.0"

  description = "KMS key for EKS cluster encryption"
  key_usage   = "ENCRYPT_DECRYPT"

  # Policy
  key_administrators = [
    data.aws_caller_identity.current.arn
  ]

  key_service_roles_for_autoscaling = [
    "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/aws-service-role/autoscaling.amazonaws.com/AWSServiceRoleForAutoScaling"
  ]

  aliases = ["${var.project_name}/${var.environment}/eks"]

  tags = local.tags
}

################################################################################
# RDS PostgreSQL
################################################################################

module "rds" {
  source  = "terraform-aws-modules/rds/aws"
  version = "~> 6.0"

  identifier = "${var.project_name}-${var.environment}-postgres"

  engine               = "postgres"
  engine_version       = "15.4"
  family               = "postgres15"
  major_engine_version = "15"
  instance_class       = var.rds_instance_class

  allocated_storage     = var.rds_allocated_storage
  max_allocated_storage = var.rds_max_allocated_storage
  storage_encrypted     = true
  kms_key_id            = module.kms.key_arn

  db_name  = var.db_name
  username = var.db_username
  port     = 5432

  # Multi-AZ for production
  multi_az               = var.environment == "production"
  db_subnet_group_name   = module.vpc.database_subnet_group_name
  vpc_security_group_ids = [aws_security_group.rds.id]

  # Backup configuration
  backup_retention_period = var.environment == "production" ? 30 : 7
  backup_window          = "03:00-04:00"
  maintenance_window     = "mon:04:00-mon:05:00"

  # Enable automated minor version updates
  auto_minor_version_upgrade = true

  # Performance Insights
  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]
  create_cloudwatch_log_group     = true
  performance_insights_enabled    = true
  performance_insights_retention_period = 7

  # Deletion protection for production
  deletion_protection = var.environment == "production"
  skip_final_snapshot = var.environment != "production"
  final_snapshot_identifier = var.environment == "production" ? "${var.project_name}-${var.environment}-final-snapshot-${formatdate("YYYY-MM-DD-hhmm", timestamp())}" : null

  tags = local.tags
}

# Security group for RDS
resource "aws_security_group" "rds" {
  name_prefix = "${var.project_name}-${var.environment}-rds-"
  vpc_id      = module.vpc.vpc_id
  description = "Security group for RDS PostgreSQL"

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [module.eks.cluster_security_group_id]
    description     = "PostgreSQL from EKS"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound"
  }

  tags = merge(local.tags, {
    Name = "${var.project_name}-${var.environment}-rds-sg"
  })
}

################################################################################
# ElastiCache Redis
################################################################################

resource "aws_elasticache_subnet_group" "redis" {
  name       = "${var.project_name}-${var.environment}-redis-subnet"
  subnet_ids = module.vpc.private_subnets

  tags = local.tags
}

resource "aws_elasticache_replication_group" "redis" {
  replication_group_id       = "${var.project_name}-${var.environment}-redis"
  replication_group_description = "Redis cluster for Django caching"
  
  engine         = "redis"
  engine_version = "7.0"
  node_type      = var.redis_node_type
  
  num_cache_clusters = var.environment == "production" ? 2 : 1
  port               = 6379
  
  subnet_group_name  = aws_elasticache_subnet_group.redis.name
  security_group_ids = [aws_security_group.redis.id]
  
  # Automatic failover for production
  automatic_failover_enabled = var.environment == "production"
  multi_az_enabled          = var.environment == "production"
  
  # Encryption
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  auth_token_enabled        = true
  auth_token                = random_password.redis_auth_token.result
  
  # Maintenance
  snapshot_retention_limit = var.environment == "production" ? 5 : 1
  snapshot_window         = "03:00-05:00"
  maintenance_window      = "mon:05:00-mon:07:00"
  
  # Parameter group
  parameter_group_name = aws_elasticache_parameter_group.redis.name
  
  tags = local.tags
}

resource "aws_elasticache_parameter_group" "redis" {
  name   = "${var.project_name}-${var.environment}-redis-params"
  family = "redis7"

  parameter {
    name  = "maxmemory-policy"
    value = "allkeys-lru"
  }

  tags = local.tags
}

resource "random_password" "redis_auth_token" {
  length  = 32
  special = true
}

# Security group for Redis
resource "aws_security_group" "redis" {
  name_prefix = "${var.project_name}-${var.environment}-redis-"
  vpc_id      = module.vpc.vpc_id
  description = "Security group for ElastiCache Redis"

  ingress {
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [module.eks.cluster_security_group_id]
    description     = "Redis from EKS"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound"
  }

  tags = merge(local.tags, {
    Name = "${var.project_name}-${var.environment}-redis-sg"
  })
}

################################################################################
# S3 Buckets
################################################################################

# Static files bucket
module "s3_static" {
  source  = "terraform-aws-modules/s3-bucket/aws"
  version = "~> 3.0"

  bucket = "${var.project_name}-${var.environment}-static-${data.aws_caller_identity.current.account_id}"
  
  # Access control
  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
  
  # CORS for CloudFront
  cors_rule = [{
    allowed_headers = ["*"]
    allowed_methods = ["GET", "HEAD"]
    allowed_origins = ["*"]
    expose_headers  = ["ETag"]
    max_age_seconds = 3600
  }]

  # Versioning
  versioning = {
    enabled = true
  }

  # Lifecycle rules
  lifecycle_rule = [{
    id      = "delete-old-versions"
    enabled = true

    noncurrent_version_expiration = {
      days = 30
    }
  }]

  tags = local.tags
}

# Media files bucket
module "s3_media" {
  source  = "terraform-aws-modules/s3-bucket/aws"
  version = "~> 3.0"

  bucket = "${var.project_name}-${var.environment}-media-${data.aws_caller_identity.current.account_id}"
  
  # Access control
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true

  # Versioning
  versioning = {
    enabled = true
  }

  # Lifecycle rules
  lifecycle_rule = [{
    id      = "intelligent-tiering"
    enabled = true

    transition = [{
      days          = 30
      storage_class = "INTELLIGENT_TIERING"
    }]
  }]

  tags = local.tags
}

################################################################################
# ECR Repository
################################################################################

resource "aws_ecr_repository" "app" {
  name                 = "${var.project_name}-${var.environment}"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "KMS"
    kms_key        = module.kms.key_arn
  }

  tags = local.tags
}

resource "aws_ecr_lifecycle_policy" "app" {
  repository = aws_ecr_repository.app.name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep last 30 images"
      selection = {
        tagStatus     = "any"
        countType     = "imageCountMoreThan"
        countNumber   = 30
      }
      action = {
        type = "expire"
      }
    }]
  })
}

################################################################################
# Secrets Manager
################################################################################

resource "aws_secretsmanager_secret" "django_secret_key" {
  name        = "${var.project_name}/${var.environment}/django-secret-key"
  description = "Django SECRET_KEY"

  tags = local.tags
}

resource "aws_secretsmanager_secret_version" "django_secret_key" {
  secret_id     = aws_secretsmanager_secret.django_secret_key.id
  secret_string = random_password.django_secret_key.result
}

resource "random_password" "django_secret_key" {
  length  = 50
  special = true
}

resource "aws_secretsmanager_secret" "database_url" {
  name        = "${var.project_name}/${var.environment}/database-url"
  description = "Database connection string"

  tags = local.tags
}

resource "aws_secretsmanager_secret_version" "database_url" {
  secret_id = aws_secretsmanager_secret.database_url.id
  secret_string = jsonencode({
    host     = module.rds.db_instance_address
    port     = module.rds.db_instance_port
    database = module.rds.db_instance_name
    username = module.rds.db_instance_username
    password = module.rds.db_instance_password
    url      = "postgresql://${module.rds.db_instance_username}:${module.rds.db_instance_password}@${module.rds.db_instance_address}:${module.rds.db_instance_port}/${module.rds.db_instance_name}"
  })
}

################################################################################
# IAM Roles for Service Accounts (IRSA)
################################################################################

# Django API pod role
module "irsa_django_api" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-role-for-service-accounts-eks"
  version = "~> 5.0"

  role_name = "${var.project_name}-${var.environment}-django-api"

  role_policy_arns = {
    s3_access        = aws_iam_policy.s3_access.arn
    secrets_access   = aws_iam_policy.secrets_access.arn
    cloudwatch_logs  = "arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy"
  }

  oidc_providers = {
    main = {
      provider_arn               = module.eks.oidc_provider_arn
      namespace_service_accounts = ["production:django-api"]
    }
  }

  tags = local.tags
}

# S3 access policy
resource "aws_iam_policy" "s3_access" {
  name        = "${var.project_name}-${var.environment}-s3-access"
  description = "Allow Django to access S3 buckets"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          module.s3_static.s3_bucket_arn,
          "${module.s3_static.s3_bucket_arn}/*",
          module.s3_media.s3_bucket_arn,
          "${module.s3_media.s3_bucket_arn}/*"
        ]
      }
    ]
  })
}

# Secrets access policy
resource "aws_iam_policy" "secrets_access" {
  name        = "${var.project_name}-${var.environment}-secrets-access"
  description = "Allow Django to access Secrets Manager"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = [
          aws_secretsmanager_secret.django_secret_key.arn,
          aws_secretsmanager_secret.database_url.arn
        ]
      }
    ]
  })
}

################################################################################
# CloudWatch Log Groups
################################################################################

resource "aws_cloudwatch_log_group" "eks_cluster" {
  name              = "/aws/eks/${local.cluster_name}/cluster"
  retention_in_days = var.environment == "production" ? 90 : 7

  tags = local.tags
}

resource "aws_cloudwatch_log_group" "django_api" {
  name              = "/aws/eks/${local.cluster_name}/django-api"
  retention_in_days = var.environment == "production" ? 30 : 7

  tags = local.tags
}
