locals {
  model_arns = [
    for id in var.bedrock_model_ids :
    "arn:${data.aws_partition.current.partition}:bedrock:${var.region}::foundation-model/${id}"
  ]
  interface_services = ["sts", "kms", "logs", "ecr.api", "ecr.dkr"]
}

# Bedrock runtime: the endpoint policy itself allows only the approved
# models, only for this account's task role.
resource "aws_vpc_endpoint" "bedrock_runtime" {
  vpc_id              = aws_vpc.this.id
  service_name        = "com.amazonaws.${var.region}.bedrock-runtime"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.endpoints.id]
  private_dns_enabled = true
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "ApprovedModelsOnly"
      Effect    = "Allow"
      Principal = { AWS = aws_iam_role.task.arn }
      Action    = ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"]
      Resource  = local.model_arns
    }]
  })
  tags = { Name = "${var.name}-bedrock-runtime" }
}

resource "aws_vpc_endpoint" "interface" {
  for_each            = toset(local.interface_services)
  vpc_id              = aws_vpc.this.id
  service_name        = "com.amazonaws.${var.region}.${each.value}"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.endpoints.id]
  private_dns_enabled = true
  tags                = { Name = "${var.name}-${each.value}" }
}

resource "aws_vpc_endpoint" "s3" {
  vpc_id            = aws_vpc.this.id
  service_name      = "com.amazonaws.${var.region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [aws_route_table.private.id]
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "ArtifactsBucketOnly"
        Effect    = "Allow"
        Principal = "*"
        Action    = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject", "s3:ListBucket", "s3:AbortMultipartUpload", "s3:ListMultipartUploadParts"]
        Resource  = [aws_s3_bucket.artifacts.arn, "${aws_s3_bucket.artifacts.arn}/*"]
      },
      {
        Sid       = "EcrLayersOnly"
        Effect    = "Allow"
        Principal = "*"
        Action    = ["s3:GetObject"]
        Resource  = ["arn:${data.aws_partition.current.partition}:s3:::prod-${var.region}-starport-layer-bucket/*"]
      }
    ]
  })
  tags = { Name = "${var.name}-s3" }
}
