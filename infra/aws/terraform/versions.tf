# Reference infrastructure for the aws-private profile.
#
# Builds an isolated VPC with NO internet gateway and NO NAT: the only way
# out of the private subnets is through VPC endpoints whose policies allow
# just the approved Bedrock model ARNs, the approved bucket, and the AWS
# plumbing a container needs (ECR pull, STS for role credentials, KMS,
# CloudWatch Logs). Review with your security team; AWS account, region,
# models and data classification must follow your internal policy.

terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.40"
    }
  }
}

provider "aws" {
  region = var.region
  default_tags {
    tags = {
      application = "grounded-studio"
      profile     = "aws-private"
    }
  }
}

data "aws_caller_identity" "current" {}
data "aws_partition" "current" {}
