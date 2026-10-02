variable "region" {
  description = "Single approved region. Must match GROUNDED_AWS_REGIONS."
  type        = string
}

variable "name" {
  description = "Resource name prefix."
  type        = string
  default     = "grounded-studio"
}

variable "vpc_cidr" {
  type    = string
  default = "10.42.0.0/16"
}

variable "private_subnet_cidrs" {
  description = "One private subnet per AZ. No public subnets are created."
  type        = list(string)
  default     = ["10.42.1.0/24", "10.42.2.0/24"]
}

variable "availability_zones" {
  type = list(string)
}

variable "bedrock_model_ids" {
  description = "Approved foundation model IDs. Must match GROUNDED_BEDROCK_MODELS."
  type        = list(string)
  default     = ["amazon.nova-pro-v1:0", "amazon.nova-lite-v1:0", "amazon.titan-embed-text-v2:0"]
}

variable "corporate_ingress_cidrs" {
  description = "Company VPN / SSO proxy ranges allowed to reach the internal ALB."
  type        = list(string)
}

variable "log_retention_days" {
  type    = number
  default = 90
}
