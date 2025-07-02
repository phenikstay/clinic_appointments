"""Основное FastAPI приложение."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from app.api.appointments import router as appointments_router
from app.core.settings import settings
from app.db.database import engine

# Настройка логирования
log_level = logging.DEBUG if settings.debug else logging.INFO
logging.basicConfig(
    level=log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Менеджер жизненного цикла приложения."""
    # Запуск
    logger.info("Starting application...")

    # Схема создается через init.sql в Docker Compose
    logger.info("Application started (database schema managed by init.sql)")

    yield

    # Корректно закрываем пул соединений для production.
    logger.info("Shutting down application...")
    try:
        await engine.dispose()
        logger.info("Database connections closed")
    except Exception as e:  # noqa: BLE001
        logger.error(f"Error during engine dispose: {e}")


app = FastAPI(
    title="Clinic Appointments",
    description="Микросервис для записи пациентов на прием к врачам",
    version="1.0.0",
    lifespan=lifespan,
    redirect_slashes=False,
    debug=settings.debug,
)

# Подключение роутеров

app.include_router(appointments_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    """Эндпоинт проверки."""
    return {"status": "healthy"}


@app.get("/")
def root() -> dict[str, str]:
    """Корневой эндпоинт."""
    return {"message": "Clinic Appointments API"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="debug" if settings.debug else "info",
    )
