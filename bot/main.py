"""
Telegram Bot для записи пациентов с ИИ-подбором врача.

ВНИМАНИЕ: Это STUB-реализация для демонстрации архитектуры!

Точка входа бота.
"""

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message

from bot.config.settings import bot_settings
from bot.handlers.symptoms import router as symptoms_router

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


async def start_command(message: Message) -> None:
    """Обработчик команды /start"""
    welcome_message = """
👋 Добро пожаловать в клинику!

Я ваш ИИ-помощник для записи на приём.

🔹 Опишите ваши симптомы, и я подберу подходящего врача
🔹 Найду свободное время для записи
🔹 Напомню о приёме

Просто напишите, что вас беспокоит!
    """
    await message.answer(welcome_message.strip())


async def main() -> None:
    """Главная функция запуска бота"""
    if not bot_settings.telegram_bot_token:
        logger.error("TELEGRAM_BOT_TOKEN не найден в переменных окружения!")
        return

    # Создание бота и диспетчера
    bot = Bot(token=bot_settings.telegram_bot_token)
    dp = Dispatcher()

    # Регистрация обработчиков
    dp.message.register(start_command, CommandStart())

    # Подключение роутеров
    dp.include_router(symptoms_router)

    # Запуск бота
    logger.info("Запуск Telegram бота (STUB версия)...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    logger.info("=== STUB РЕАЛИЗАЦИЯ TELEGRAM БОТА ===")
    asyncio.run(main())
