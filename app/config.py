import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""

    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/dsr_wsr_db",
    )

    postgres_user: str = os.getenv("POSTGRES_USER", "postgres")
    postgres_password: str = os.getenv("POSTGRES_PASSWORD", "postgres")
    postgres_host: str = os.getenv("POSTGRES_HOST", "localhost")
    postgres_port: str = os.getenv("POSTGRES_PORT", "5432")
    postgres_db: str = os.getenv("POSTGRES_DB", "dsr_wsr_db")

    # Standard OpenAI (optional)
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")

    # Azure OpenAI (preferred when set — used for story title generation)
    azure_openai_endpoint: str = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    azure_openai_api_key: str = os.getenv("AZURE_OPENAI_API_KEY", "")
    azure_openai_api_version: str = os.getenv(
        "AZURE_OPENAI_API_VERSION", "2024-02-15-preview"
    )
    azure_openai_model: str = os.getenv("AZURE_OPENAI_MODEL", "gpt-4o-mini")


@lru_cache
def get_settings() -> Settings:
    return Settings()


def llm_configured(settings: Settings | None = None) -> bool:
    """True when Azure OpenAI or standard OpenAI credentials are present."""
    s = settings or get_settings()
    if s.azure_openai_endpoint and s.azure_openai_api_key:
        return True
    return bool(s.openai_api_key)
