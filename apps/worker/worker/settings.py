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

    # Recording transcription is local-only. A model path must already exist
    # on the private host; the worker never downloads a model at runtime.
    trans_provider: str = "stub"
    whisper_model_path: str = ""
    whisper_device: str = "cpu"
    trans_language: str = "en"

    # Narration is local-only. Configure Piper paths to enable it.
    narration_provider: str = ""
    piper_bin: str = "piper"
    piper_model_path: str = ""

    artifact_dir: str = "out/jobs"

    class Config:
        env_file = ".env"


settings = Settings()
