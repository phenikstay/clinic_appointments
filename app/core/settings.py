"""Настройки приложения."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Настройки приложения."""

    # Настройки базы данных
    database_url: str

    # Режим отладки
    debug: bool = False

    # Часовой пояс приложения
    timezone: str

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()  # type: ignore[call-arg]
