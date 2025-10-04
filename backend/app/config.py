from pydantic_settings import BaseSettings
from pydantic import Field, ConfigDict

class Settings(BaseSettings):
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    database_url: str = Field(default="postgresql+asyncpg://postgres:postgres@db:5432/app", alias="DATABASE_URL")
    web_search_provider: str = Field(default="dummy", alias="WEB_SEARCH_PROVIDER")
    web_search_api_key: str | None = Field(default=None, alias="WEB_SEARCH_API_KEY")
    embed_batch_size: int = Field(default=32, alias="EMBED_BATCH_SIZE")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    rate_limit_per_5min: int = Field(default=100, alias="RATE_LIMIT_PER_5MIN")
    max_upload_mb: int = Field(default=25, alias="MAX_UPLOAD_MB")
    media_root: str = Field(default="/app/media", alias="MEDIA_ROOT")
    web_search_enabled: bool = Field(default=True, alias="WEB_SEARCH_ENABLED")

    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore"  # Ignora campos extras do .env (como POSTGRES_*, VITE_*)
    )

settings = Settings()
