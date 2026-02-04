"""Configuration management for SecureClaw."""

from functools import lru_cache
from typing import Annotated

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Discord
    discord_token: SecretStr = Field(description="Discord bot token")
    allowed_user_ids: Annotated[
        list[int],
        Field(default_factory=list, description="Discord user IDs allowed to interact"),
    ]

    # Gemini (for embeddings)
    gemini_api_key: SecretStr = Field(description="Gemini API key for embeddings")

    # Anthropic (optional, for Claude LLM)
    anthropic_api_key: SecretStr | None = Field(
        default=None, description="Anthropic API key for Claude"
    )

    # OpenAI (optional, alternative LLM)
    openai_api_key: SecretStr | None = Field(
        default=None, description="OpenAI API key"
    )

    # Qdrant
    qdrant_host: str = Field(default="qdrant", description="Qdrant server host")
    qdrant_port: int = Field(default=6333, description="Qdrant server port")

    # Application
    environment: str = Field(default="production", description="Environment name")
    log_level: str = Field(default="INFO", description="Logging level")

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment.lower() == "development"

    @property
    def qdrant_url(self) -> str:
        """Get the full Qdrant URL."""
        return f"http://{self.qdrant_host}:{self.qdrant_port}"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
