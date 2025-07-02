"""Конфигурация базы данных."""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.settings import settings

# Создаем асинхронный движок
engine = create_async_engine(settings.database_url)
AsyncSessionLocal = async_sessionmaker(
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    bind=engine,
    class_=AsyncSession,
)


class Base(DeclarativeBase):
    """Базовый класс для моделей базы данных."""

    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Получить асинхронную сессию базы данных."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
