
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    gemini_api_key: str = ""
    

def get_settings()-> Settings:
    """Get cached settings instance.

    Returns:
        Singleton Settings instance
    """
    return Settings()