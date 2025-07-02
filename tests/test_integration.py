"""Интеграционные тесты для API записей на прием."""

import asyncio
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import settings
from app.main import app
from app.models.appointment import Appointment
from app.models.doctor import Doctor


def get_test_time() -> datetime:
    """Получить тестовое время в правильной timezone."""
    return datetime.now(ZoneInfo(settings.timezone))


@pytest.mark.asyncio
async def test_create_appointment_success(test_db: AsyncSession) -> None:
    """Тест успешного создания записи на прием."""
    app.dependency_overrides[AsyncSession] = lambda: test_db

    # Создаем врача
    doctor = Doctor(name="Тестовый врач", specialization="Терапевт", is_active=True)
    test_db.add(doctor)
    await test_db.commit()
    await test_db.refresh(doctor)

    # Время записи в будущем
    future_time = get_test_time() + timedelta(days=1)
    appointment_time = future_time.replace(hour=10, minute=0, second=0, microsecond=0)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post(
            "/appointments",
            json={
                "doctor_id": doctor.id,
                "patient_name": "Тестовый пациент",
                "start_time": appointment_time.isoformat(),
            },
        )

    assert response.status_code == 201
    data = response.json()
    assert data["doctor_id"] == doctor.id
    assert data["patient_name"] == "Тестовый пациент"
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_create_appointment_duplicate(test_db: AsyncSession) -> None:
    """Тест создания дублирующей записи на прием."""
    app.dependency_overrides[AsyncSession] = lambda: test_db

    # Создаем врача
    doctor = Doctor(name="Тестовый врач", specialization="Терапевт", is_active=True)
    test_db.add(doctor)
    await test_db.commit()
    await test_db.refresh(doctor)

    # Время записи в будущем
    future_time = get_test_time() + timedelta(days=1)
    appointment_time = future_time.replace(hour=10, minute=30, second=0, microsecond=0)

    # Первая запись (должна быть успешной)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response1 = await ac.post(
            "/appointments",
            json={
                "doctor_id": doctor.id,
                "patient_name": "Первый пациент",
                "start_time": appointment_time.isoformat(),
            },
        )

    assert response1.status_code == 201

    # Вторая запись на то же время (должна быть отклонена)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response2 = await ac.post(
            "/appointments",
            json={
                "doctor_id": doctor.id,
                "patient_name": "Второй пациент",
                "start_time": appointment_time.isoformat(),
            },
        )

    assert response2.status_code == 400
    assert "занят в это время" in response2.json()["detail"]


@pytest.mark.asyncio
async def test_create_appointment_validation_errors(test_db: AsyncSession) -> None:
    """Тест валидации данных записи на прием."""
    app.dependency_overrides[AsyncSession] = lambda: test_db

    # Создаем врача
    doctor = Doctor(name="Тестовый врач", specialization="Терапевт", is_active=True)
    test_db.add(doctor)
    await test_db.commit()
    await test_db.refresh(doctor)

    # Тест времени в прошлом
    past_time = get_test_time() - timedelta(hours=1)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post(
            "/appointments",
            json={
                "doctor_id": doctor.id,
                "patient_name": "Тестовый пациент",
                "start_time": past_time.isoformat(),
            },
        )
    assert response.status_code == 422
    assert "Время записи должно быть в будущем" in response.text

    # Тест нерабочих часов
    future_time = get_test_time() + timedelta(days=1)
    late_time = future_time.replace(hour=19, minute=0, second=0, microsecond=0)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post(
            "/appointments",
            json={
                "doctor_id": doctor.id,
                "patient_name": "Тестовый пациент",
                "start_time": late_time.isoformat(),
            },
        )
    assert response.status_code == 422
    assert "9:00 до 17:30" in response.text


@pytest.mark.asyncio
async def test_get_appointment_success(test_db: AsyncSession) -> None:
    """Тест успешного получения записи на прием."""
    app.dependency_overrides[AsyncSession] = lambda: test_db

    # Создаем врача и запись
    doctor = Doctor(name="Тестовый врач", specialization="Терапевт", is_active=True)
    test_db.add(doctor)
    await test_db.commit()
    await test_db.refresh(doctor)

    future_time = get_test_time() + timedelta(days=1)
    appointment_time = future_time.replace(hour=11, minute=0, second=0, microsecond=0)

    appointment = Appointment(
        doctor_id=doctor.id,
        patient_name="Тестовый пациент",
        start_time=appointment_time,
    )
    test_db.add(appointment)
    await test_db.commit()
    await test_db.refresh(appointment)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get(f"/appointments/{appointment.id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == appointment.id
    assert data["doctor_id"] == doctor.id
    assert data["patient_name"] == "Тестовый пациент"


@pytest.mark.asyncio
async def test_get_appointment_not_found(test_db: AsyncSession) -> None:
    """Тест получения несуществующей записи на прием."""
    app.dependency_overrides[AsyncSession] = lambda: test_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/appointments/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Запись не найдена"


@pytest.mark.asyncio
async def test_health_check() -> None:
    """Тест health check эндпоинта."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


@pytest.mark.asyncio
async def test_invalid_doctor_id_validation(test_db: AsyncSession) -> None:
    """Тест валидации несуществующего врача."""
    app.dependency_overrides[AsyncSession] = lambda: test_db

    future_time = get_test_time() + timedelta(days=1)
    appointment_time = future_time.replace(hour=10, minute=0, second=0, microsecond=0)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post(
            "/appointments",
            json={
                "doctor_id": 999,  # Несуществующий врач
                "patient_name": "Тестовый пациент",
                "start_time": appointment_time.isoformat(),
            },
        )

    assert response.status_code == 400
    assert "не найден или неактивен" in response.json()["detail"]


@pytest.mark.asyncio
async def test_concurrent_appointments_race_condition(test_db: AsyncSession) -> None:
    """Тест предотвращения race condition при одновременных запросах."""
    app.dependency_overrides[AsyncSession] = lambda: test_db

    # Создаем врача
    doctor = Doctor(name="Тестовый врач", specialization="Терапевт", is_active=True)
    test_db.add(doctor)
    await test_db.commit()
    await test_db.refresh(doctor)

    # Время записи в будущем
    future_time = get_test_time() + timedelta(days=1)
    appointment_time = future_time.replace(hour=14, minute=0, second=0, microsecond=0)

    # Создаем несколько одновременных запросов на одно и то же время
    async def create_appointment(patient_name: str) -> dict:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            response = await ac.post(
                "/appointments",
                json={
                    "doctor_id": doctor.id,
                    "patient_name": patient_name,
                    "start_time": appointment_time.isoformat(),
                },
            )
            return {"status_code": response.status_code, "response": response.json()}

    # Запускаем 5 одновременных запросов
    tasks = [create_appointment(f"Пациент {i}") for i in range(1, 6)]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Проверяем результаты
    success_count = 0
    error_count = 0

    for result in results:
        if isinstance(result, dict):
            if result["status_code"] == 201:
                success_count += 1
            elif result["status_code"] == 400:
                error_count += 1
                # Проверяем, что ошибка связана с занятостью врача или интеграцией
                detail = result["response"]["detail"]
                assert (
                    "занят в это время" in detail or "ограничений целостности" in detail
                ), f"Unexpected error: {detail}"

    # Должна быть создана только одна запись, остальные отклонены
    assert success_count == 1, f"Ожидалась 1 успешная запись, получено {success_count}"
    assert error_count == 4, f"Ожидалось 4 отклоненных запроса, получено {error_count}"


@pytest.mark.asyncio
async def test_inactive_doctor_validation(test_db: AsyncSession) -> None:
    """Тест валидации неактивного врача."""
    app.dependency_overrides[AsyncSession] = lambda: test_db

    # Создаем неактивного врача
    doctor = Doctor(name="Неактивный врач", specialization="Терапевт", is_active=False)
    test_db.add(doctor)
    await test_db.commit()
    await test_db.refresh(doctor)

    future_time = get_test_time() + timedelta(days=1)
    appointment_time = future_time.replace(hour=10, minute=0, second=0, microsecond=0)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post(
            "/appointments",
            json={
                "doctor_id": doctor.id,
                "patient_name": "Тестовый пациент",
                "start_time": appointment_time.isoformat(),
            },
        )

    assert response.status_code == 400
    assert "не найден или неактивен" in response.json()["detail"]
