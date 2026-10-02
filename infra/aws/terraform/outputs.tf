# Feed these into the api/worker task environment.
output "grounded_env" {
  value = {
    GROUNDED_DEPLOYMENT_MODE = "aws-private"
    GROUNDED_AWS_REGIONS     = var.region
    GROUNDED_AWS_SERVICES    = "bedrock-runtime,s3"
    GROUNDED_AWS_PRIVATE_DNS = "true"
    GROUNDED_BEDROCK_MODELS  = join(",", var.bedrock_model_ids)
    GROUNDED_OBJECT_BUCKETS  = aws_s3_bucket.artifacts.bucket
    GROUNDED_OBJECT_KMS_KEY  = aws_kms_key.data.arn
    MINIO_ENDPOINT           = "https://s3.${var.region}.amazonaws.com"
    MINIO_BUCKET             = aws_s3_bucket.artifacts.bucket
    MINIO_REGION             = var.region
  }
}

output "task_role_arn" {
  value = aws_iam_role.task.arn
}

output "app_security_group_id" {
  value = aws_security_group.app.id
}

output "private_subnet_ids" {
  value = aws_subnet.private[*].id
}
