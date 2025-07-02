"""Настройки Telegram бота"""

from pydantic_settings import BaseSettings


class BotSettings(BaseSettings):
    """Настройки Telegram бота"""

    # Токен Telegram бота
    telegram_bot_token: str

    # OpenAI API Key для ИИ-анализа симптомов
    openai_api_key: str

    # URL API клиники
    clinic_api_url: str

    # Настройки ИИ
    ai_model: str
    ai_temperature: float

    # Часовой пояс
    timezone: str

    model_config = {"env_file": ".env", "extra": "ignore"}


# Создание экземпляра настроек
bot_settings = BotSettings()  # type: ignore[call-arg]
