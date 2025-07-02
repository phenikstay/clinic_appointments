"""Конфигурация для тестов."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.database import Base, get_db
from app.main import app

# Тестовая база данных SQLite
SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

engine = create_async_engine(SQLALCHEMY_DATABASE_URL)
TestingSessionLocal = async_sessionmaker(
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    bind=engine,
    class_=AsyncSession,
)


async def override_get_db():
    """Переопределенная функция получения БД для тестов."""
    async with TestingSessionLocal() as session:
        yield session


@pytest.fixture(autouse=True)
def setup_teardown_app():
    """Автоматическая фикстура для настройки и очистки зависимостей приложения."""
    # Настройка перед тестом
    original_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = override_get_db

    yield

    # Очистка после теста
    app.dependency_overrides.clear()
    app.dependency_overrides.update(original_overrides)


@pytest.fixture
async def test_db():
    """Фикстура для получения тестовой БД."""
    # Создаем схему БД для тестов
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    # Возвращаем сессию
    async with TestingSessionLocal() as session:
        yield session

    # Очищаем схему после тестов
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
