from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://grounded:change-me@localhost:5432/grounded"
    redis_url: str = "redis://localhost:6379/0"
    minio_endpoint: str = "http://127.0.0.1:9000"
    minio_bucket: str = "grounded"
    minio_region: str = "us-east-1"
    minio_access_key: str = "grounded"
    minio_secret_key: str = "change-me-too"
    model_base_url: str = ""
    model_name: str = "local-instruct"
    whisper_model: str = "medium"
    aws_region: str = "us-east-1"
    trans_provider: str = "stub"
    trans_s3_bucket: str = ""
    trans_language: str = "en-US"
    trans_timeout_s: int = 1800
    narration_provider: str = ""
    artifact_dir: str = "out/jobs"

    class Config:
        env_file = ".env"


settings = Settings()
