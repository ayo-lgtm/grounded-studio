from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://grounded:change-me@localhost:5432/grounded"
    redis_url: str = "redis://localhost:6379/0"
    minio_endpoint: str = "http://127.0.0.1:9000"
    minio_bucket: str = "grounded"
    minio_region: str = "us-east-1"
    minio_access_key: str = ""
    minio_secret_key: str = ""
    model_base_url: str = ""
    model_name: str = "local-instruct"
    grounded_env: str = "production"
    cors_origins: str = ""
    bootstrap_admins: str = ""

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
