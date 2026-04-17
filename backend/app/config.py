from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5433/app_db"
    secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440  # 24 hours
    anthropic_api_key: str = ""
    anthropic_base_url: str = ""
    upload_dir: str = "./uploads"
    max_file_size: int = 20 * 1024 * 1024  # 20MB
    app_base_url: str = "http://localhost:5173"

    model_config = {"env_file": [".env", ".env.docker"], "extra": "ignore"}


settings = Settings()
