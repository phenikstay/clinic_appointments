"""Исчерпывающие тесты для всех API эндпоинтов."""

import asyncio
from datetime import datetime, timedelta, timezone
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
async def test_root_endpoint() -> None:
    """Тест корневого эндпоинта."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/")

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Clinic Appointments API"


@pytest.mark.asyncio
async def test_health_endpoint() -> None:
    """Тест health check эндпоинта."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_nonexistent_endpoint() -> None:
    """Тест несуществующего эндпоинта."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/nonexistent")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_appointment_success_basic(test_db: AsyncSession) -> None:
    """Тест базового успешного создания записи."""
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
    assert "updated_at" in data


@pytest.mark.asyncio
async def test_create_appointment_success_half_hour(test_db: AsyncSession) -> None:
    """Тест создания записи на полчаса."""
    app.dependency_overrides[AsyncSession] = lambda: test_db

    doctor = Doctor(name="Тестовый врач", specialization="Терапевт", is_active=True)
    test_db.add(doctor)
    await test_db.commit()
    await test_db.refresh(doctor)

    future_time = get_test_time() + timedelta(days=1)
    appointment_time = future_time.replace(hour=14, minute=30, second=0, microsecond=0)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post(
            "/appointments",
            json={
                "doctor_id": doctor.id,
                "patient_name": "Пациент на полчаса",
                "start_time": appointment_time.isoformat(),
            },
        )

    assert response.status_code == 201


@pytest.mark.asyncio
async def test_create_appointment_success_last_slot(test_db: AsyncSession) -> None:
    """Тест создания записи на последний доступный слот (17:30)."""
    app.dependency_overrides[AsyncSession] = lambda: test_db

    doctor = Doctor(name="Тестовый врач", specialization="Терапевт", is_active=True)
    test_db.add(doctor)
    await test_db.commit()
    await test_db.refresh(doctor)

    future_time = get_test_time() + timedelta(days=1)
    appointment_time = future_time.replace(hour=17, minute=30, second=0, microsecond=0)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post(
            "/appointments",
            json={
                "doctor_id": doctor.id,
                "patient_name": "Последний пациент",
                "start_time": appointment_time.isoformat(),
            },
        )

    assert response.status_code == 201


@pytest.mark.asyncio
async def test_create_appointment_missing_fields(test_db: AsyncSession) -> None:
    """Тест создания записи с отсутствующими полями."""
    app.dependency_overrides[AsyncSession] = lambda: test_db

    test_cases = [
        {},  # Все поля отсутствуют
        {"doctor_id": 1},  # Отсутствует patient_name и start_time
        {"patient_name": "Пациент"},  # Отсутствует doctor_id и start_time
        {"start_time": "2025-07-01T10:00:00Z"},  # Отсутствует doctor_id и patient_name
        {"doctor_id": 1, "patient_name": "Пациент"},  # Отсутствует start_time
        {
            "doctor_id": 1,
            "start_time": "2025-07-01T10:00:00Z",
        },  # Отсутствует patient_name
        {
            "patient_name": "Пациент",
            "start_time": "2025-07-01T10:00:00Z",
        },  # Отсутствует doctor_id
    ]

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        for test_data in test_cases:
            response = await ac.post("/appointments", json=test_data)
            assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_create_appointment_invalid_doctor_id(test_db: AsyncSession) -> None:
    """Тест создания записи с некорректным ID врача."""
    app.dependency_overrides[AsyncSession] = lambda: test_db

    future_time = get_test_time() + timedelta(days=1)
    appointment_time = future_time.replace(hour=10, minute=0, second=0, microsecond=0)

    test_cases = [
        {"doctor_id": 0, "error_expected": 422},  # Валидация Pydantic (ge=1)
        {"doctor_id": -1, "error_expected": 422},  # Отрицательный ID
        {"doctor_id": "abc", "error_expected": 422},  # Строка вместо числа
        {"doctor_id": 999999, "error_expected": 400},  # Несуществующий врач
    ]

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        for test_case in test_cases:
            response = await ac.post(
                "/appointments",
                json={
                    "doctor_id": test_case["doctor_id"],
                    "patient_name": "Тестовый пациент",
                    "start_time": appointment_time.isoformat(),
                },
            )
            assert response.status_code == test_case["error_expected"]


@pytest.mark.asyncio
async def test_create_appointment_invalid_patient_name(test_db: AsyncSession) -> None:
    """Тест создания записи с некорректным именем пациента."""
    app.dependency_overrides[AsyncSession] = lambda: test_db

    doctor = Doctor(name="Тестовый врач", specialization="Терапевт", is_active=True)
    test_db.add(doctor)
    await test_db.commit()
    await test_db.refresh(doctor)

    future_time = get_test_time() + timedelta(days=1)
    appointment_time = future_time.replace(hour=10, minute=0, second=0, microsecond=0)

    test_cases = [
        "",  # Пустая строка
        "   ",  # Только пробелы
        "a" * 256,  # Слишком длинное имя (>255 символов)
    ]

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        for patient_name in test_cases:
            response = await ac.post(
                "/appointments",
                json={
                    "doctor_id": doctor.id,
                    "patient_name": patient_name,
                    "start_time": appointment_time.isoformat(),
                },
            )
            assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_create_appointment_invalid_time_format(test_db: AsyncSession) -> None:
    """Тест создания записи с некорректным форматом времени."""
    app.dependency_overrides[AsyncSession] = lambda: test_db

    doctor = Doctor(name="Тестовый врач", specialization="Терапевт", is_active=True)
    test_db.add(doctor)
    await test_db.commit()
    await test_db.refresh(doctor)

    test_cases = [
        "invalid-time",  # Неправильный формат
        "2025-13-01T10:00:00Z",  # Некорректный месяц
        "2025-07-32T10:00:00Z",  # Некорректный день
        "2025-07-01T25:00:00Z",  # Некорректный час
        "2025-07-01T10:70:00Z",  # Некорректная минута
        "",  # Пустая строка
    ]

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        for start_time in test_cases:
            response = await ac.post(
                "/appointments",
                json={
                    "doctor_id": doctor.id,
                    "patient_name": "Тестовый пациент",
                    "start_time": start_time,
                },
            )
            assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_create_appointment_past_time(test_db: AsyncSession) -> None:
    """Тест создания записи в прошлом."""
    app.dependency_overrides[AsyncSession] = lambda: test_db

    doctor = Doctor(name="Тестовый врач", specialization="Терапевт", is_active=True)
    test_db.add(doctor)
    await test_db.commit()
    await test_db.refresh(doctor)

    # Время в прошлом
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
    assert "будущем" in response.text


@pytest.mark.asyncio
async def test_create_appointment_weekend(test_db: AsyncSession) -> None:
    """Тест создания записи в выходные дни."""
    app.dependency_overrides[AsyncSession] = lambda: test_db

    doctor = Doctor(name="Тестовый врач", specialization="Терапевт", is_active=True)
    test_db.add(doctor)
    await test_db.commit()
    await test_db.refresh(doctor)

    # Находим ближайшую субботу
    current_time = get_test_time()
    days_until_saturday = (5 - current_time.weekday()) % 7
    if days_until_saturday == 0:  # Если сегодня суббота
        days_until_saturday = 7
    saturday = current_time + timedelta(days=days_until_saturday)
    saturday_time = saturday.replace(hour=10, minute=0, second=0, microsecond=0)

    # Воскресенье
    sunday_time = saturday_time + timedelta(days=1)

    test_cases = [saturday_time, sunday_time]

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        for weekend_time in test_cases:
            response = await ac.post(
                "/appointments",
                json={
                    "doctor_id": doctor.id,
                    "patient_name": "Тестовый пациент",
                    "start_time": weekend_time.isoformat(),
                },
            )
            assert response.status_code == 422
            assert "рабочие дни" in response.text


@pytest.mark.asyncio
async def test_create_appointment_non_working_hours(test_db: AsyncSession) -> None:
    """Тест создания записи в нерабочие часы."""
    app.dependency_overrides[AsyncSession] = lambda: test_db

    doctor = Doctor(name="Тестовый врач", specialization="Терапевт", is_active=True)
    test_db.add(doctor)
    await test_db.commit()
    await test_db.refresh(doctor)

    future_time = get_test_time() + timedelta(days=1)

    # Тестируем различные нерабочие часы
    test_cases = [
        8,  # Раньше 9:00
        18,  # 18:00 и позже
        19,  # Поздний вечер
        0,  # Полночь
        7,  # Раннее утро
    ]

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        for hour in test_cases:
            appointment_time = future_time.replace(
                hour=hour, minute=0, second=0, microsecond=0
            )
            response = await ac.post(
                "/appointments",
                json={
                    "doctor_id": doctor.id,
                    "patient_name": "Тестовый пациент",
                    "start_time": appointment_time.isoformat(),
                },
            )
            assert response.status_code == 422
            assert "9:00 до 17:30" in response.text


@pytest.mark.asyncio
async def test_create_appointment_invalid_minutes(test_db: AsyncSession) -> None:
    """Тест создания записи с некорректными минутами."""
    app.dependency_overrides[AsyncSession] = lambda: test_db

    doctor = Doctor(name="Тестовый врач", specialization="Терапевт", is_active=True)
    test_db.add(doctor)
    await test_db.commit()
    await test_db.refresh(doctor)

    future_time = get_test_time() + timedelta(days=1)

    # Тестируем неправильные минуты (не 0 или 30)
    test_cases = [15, 45, 1, 29, 31, 59]

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        for minute in test_cases:
            appointment_time = future_time.replace(
                hour=10, minute=minute, second=0, microsecond=0
            )
            response = await ac.post(
                "/appointments",
                json={
                    "doctor_id": doctor.id,
                    "patient_name": "Тестовый пациент",
                    "start_time": appointment_time.isoformat(),
                },
            )
            assert response.status_code == 422
            assert "начале часа или в половину" in response.text


@pytest.mark.asyncio
async def test_create_appointment_with_seconds(test_db: AsyncSession) -> None:
    """Тест создания записи с секундами/микросекундами."""
    app.dependency_overrides[AsyncSession] = lambda: test_db

    doctor = Doctor(name="Тестовый врач", specialization="Терапевт", is_active=True)
    test_db.add(doctor)
    await test_db.commit()
    await test_db.refresh(doctor)

    future_time = get_test_time() + timedelta(days=1)

    # Время с секундами
    appointment_time_with_seconds = future_time.replace(
        hour=10, minute=0, second=30, microsecond=0
    )

    # Время с микросекундами
    appointment_time_with_microseconds = future_time.replace(
        hour=10, minute=30, second=0, microsecond=123456
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        for appointment_time in [
            appointment_time_with_seconds,
            appointment_time_with_microseconds,
        ]:
            response = await ac.post(
                "/appointments",
                json={
                    "doctor_id": doctor.id,
                    "patient_name": "Тестовый пациент",
                    "start_time": appointment_time.isoformat(),
                },
            )
            assert response.status_code == 422
            assert "начале часа или в половину" in response.text


@pytest.mark.asyncio
async def test_create_appointment_inactive_doctor(test_db: AsyncSession) -> None:
    """Тест создания записи к неактивному врачу."""
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
    assert "не найден или неактивен" in response.text


@pytest.mark.asyncio
async def test_create_appointment_duplicate_time(test_db: AsyncSession) -> None:
    """Тест создания дублирующей записи на то же время."""
    app.dependency_overrides[AsyncSession] = lambda: test_db

    doctor = Doctor(name="Тестовый врач", specialization="Терапевт", is_active=True)
    test_db.add(doctor)
    await test_db.commit()
    await test_db.refresh(doctor)

    future_time = get_test_time() + timedelta(days=1)
    appointment_time = future_time.replace(hour=10, minute=30, second=0, microsecond=0)

    # Первая запись
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

    # Вторая запись на то же время
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
    assert "занят в это время" in response2.text


@pytest.mark.asyncio
async def test_create_appointment_race_condition(test_db: AsyncSession) -> None:
    """Тест race condition при одновременном создании записей."""

    doctor = Doctor(name="Тестовый врач", specialization="Терапевт", is_active=True)
    test_db.add(doctor)
    await test_db.commit()
    await test_db.refresh(doctor)

    future_time = get_test_time() + timedelta(days=1)
    appointment_time = future_time.replace(hour=11, minute=0, second=0, microsecond=0)

    async def create_appointment(patient_name: str) -> dict:
        try:
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
                return {
                    "status": response.status_code,
                    "patient": patient_name,
                    "data": (
                        response.json()
                        if response.status_code in [200, 201, 400]
                        else None
                    ),
                }
        except Exception as e:
            return {"status": 500, "patient": patient_name, "error": str(e)}

    # Запускаем 3 одновременных запроса (упрощаем для стабильности)
    tasks = []
    for i in range(1, 4):
        task = asyncio.create_task(create_appointment(f"Пациент {i}"))
        tasks.append(task)
        # Небольшая задержка между запросами для детерминированности
        if i < 3:
            await asyncio.sleep(0.001)

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Обрабатываем исключения
    processed_results = []
    for result in results:
        if isinstance(result, Exception):
            processed_results.append({"status": 500, "error": str(result)})
        else:
            processed_results.append(result)

    # Проверяем, что только одна запись прошла успешно
    successful_count = sum(1 for r in processed_results if r.get("status") == 201)
    failed_count = sum(1 for r in processed_results if r.get("status") == 400)

    # В race condition должен быть ровно один успешный результат и остальные - ошибки
    assert (
        successful_count == 1
    ), f"Ожидался 1 успешный запрос, получено {successful_count}"
    assert (
        failed_count >= 2
    ), f"Ожидалось минимум 2 неудачных запроса, получено {failed_count}"
    assert (
        successful_count + failed_count >= 3
    ), "Общее количество результатов меньше ожидаемого"


@pytest.mark.asyncio
async def test_get_appointment_success(test_db: AsyncSession) -> None:
    """Тест успешного получения записи."""
    app.dependency_overrides[AsyncSession] = lambda: test_db

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
    assert "created_at" in data
    assert "updated_at" in data


@pytest.mark.asyncio
async def test_get_appointment_not_found(test_db: AsyncSession) -> None:
    """Тест получения несуществующей записи."""
    app.dependency_overrides[AsyncSession] = lambda: test_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/appointments/999999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Запись не найдена"


@pytest.mark.asyncio
async def test_get_appointment_invalid_id(test_db: AsyncSession) -> None:
    """Тест получения записи с некорректным ID."""
    app.dependency_overrides[AsyncSession] = lambda: test_db

    test_cases = [
        {"id": "abc", "expected": [422]},  # Строка
        {"id": "0", "expected": [404]},  # Ноль
        {"id": "-1", "expected": [404]},  # Отрицательное число
        {"id": "1.5", "expected": [422]},  # Дробное число
        {
            "id": "999999999999999999999999999999",
            "expected": [500],
        },  # Очень большое число (DB error)
    ]

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        for test_case in test_cases:
            response = await ac.get(f"/appointments/{test_case['id']}")
            # FastAPI автоматически валидирует path параметры
            assert response.status_code in test_case["expected"]


@pytest.mark.asyncio
async def test_appointments_wrong_methods(test_db: AsyncSession) -> None:
    """Тест неправильных HTTP методов для эндпоинтов."""
    app.dependency_overrides[AsyncSession] = lambda: test_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # GET на POST эндпоинт
        response = await ac.get("/appointments")
        assert response.status_code == 405  # Method Not Allowed

        # PUT на POST эндпоинт
        response = await ac.put("/appointments", json={})
        assert response.status_code == 405

        # DELETE на GET эндпоинт
        response = await ac.delete("/appointments/1")
        assert response.status_code == 405

        # POST на GET эндпоинт
        response = await ac.post("/appointments/1", json={})
        assert response.status_code == 405


@pytest.mark.asyncio
async def test_create_appointment_invalid_json(test_db: AsyncSession) -> None:
    """Тест создания записи с некорректным JSON."""
    app.dependency_overrides[AsyncSession] = lambda: test_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # Некорректный JSON
        response = await ac.post(
            "/appointments",
            content='{"doctor_id": 1, "patient_name": "Test", invalid_json}',
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422

        # Пустой JSON
        response = await ac.post(
            "/appointments",
            content="",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_appointment_different_content_types(
    test_db: AsyncSession,
) -> None:
    """Тест создания записи с различными Content-Type."""
    app.dependency_overrides[AsyncSession] = lambda: test_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # Без Content-Type
        response = await ac.post(
            "/appointments",
            content=(
                '{"doctor_id": 1, "patient_name": "Test", '
                '"start_time": "2025-07-01T10:00:00Z"}'
            ),
        )
        # FastAPI может обработать данные и вернуть 400 если врач не найден
        assert response.status_code in [422, 415, 400]

        # Неправильный Content-Type
        response = await ac.post(
            "/appointments",
            content=(
                '{"doctor_id": 1, "patient_name": "Test", '
                '"start_time": "2025-07-01T10:00:00Z"}'
            ),
            headers={"Content-Type": "text/plain"},
        )
        assert response.status_code in [422, 415, 400]


@pytest.mark.asyncio
async def test_appointments_performance_multiple_creates(test_db: AsyncSession) -> None:
    """Тест производительности при создании множественных записей."""
    app.dependency_overrides[AsyncSession] = lambda: test_db

    # Создаем врача
    doctor = Doctor(name="Тестовый врач", specialization="Терапевт", is_active=True)
    test_db.add(doctor)
    await test_db.commit()
    await test_db.refresh(doctor)

    # Создаем 10 записей в разное время
    base_time = get_test_time() + timedelta(days=1)
    appointments_data = []

    for i in range(10):
        appointment_time = base_time.replace(
            hour=9 + (i // 2),  # Часы от 9 до 13
            minute=(i % 2) * 30,  # 0 или 30 минут
            second=0,
            microsecond=0,
        )
        appointments_data.append(
            {
                "doctor_id": doctor.id,
                "patient_name": f"Пациент {i+1}",
                "start_time": appointment_time.isoformat(),
            }
        )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # Создаем записи последовательно
        successful_creates = 0
        for appointment_data in appointments_data:
            response = await ac.post("/appointments", json=appointment_data)
            if response.status_code == 201:
                successful_creates += 1

        assert successful_creates == 10  # Все записи должны быть созданы успешно


@pytest.mark.asyncio
async def test_create_appointment_success_edge_cases(test_db: AsyncSession) -> None:
    """Тест успешного создания записи для граничных случаев."""
    app.dependency_overrides[AsyncSession] = lambda: test_db

    doctor = Doctor(name="Тестовый врач", specialization="Терапевт", is_active=True)
    test_db.add(doctor)
    await test_db.commit()
    await test_db.refresh(doctor)

    future_time = get_test_time() + timedelta(days=1)

    # Тестируем крайние случаи валидных времен
    test_cases = [
        {"hour": 9, "minute": 0},  # Первый слот
        {"hour": 17, "minute": 30},  # Последний слот
        {"hour": 12, "minute": 0},  # Середина дня, ровный час
        {"hour": 15, "minute": 30},  # Середина дня, полчаса
    ]

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        for i, time_case in enumerate(test_cases):
            appointment_time = future_time.replace(
                hour=time_case["hour"],
                minute=time_case["minute"],
                second=0,
                microsecond=0,
            )

            response = await ac.post(
                "/appointments",
                json={
                    "doctor_id": doctor.id,
                    "patient_name": f"Пациент {i+1}",
                    "start_time": appointment_time.isoformat(),
                },
            )
            assert response.status_code == 201


@pytest.mark.asyncio
async def test_create_appointment_patient_name_trimming(test_db: AsyncSession) -> None:
    """Тест обрезки пробелов в имени пациента."""
    app.dependency_overrides[AsyncSession] = lambda: test_db

    doctor = Doctor(name="Тестовый врач", specialization="Терапевт", is_active=True)
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
                "patient_name": "  Пациент с пробелами  ",  # Пробелы по краям
                "start_time": appointment_time.isoformat(),
            },
        )

    assert response.status_code == 201
    data = response.json()
    assert data["patient_name"] == "Пациент с пробелами"  # Пробелы должны быть обрезаны


@pytest.mark.asyncio
async def test_create_appointment_timezone_handling(test_db: AsyncSession) -> None:
    """Тест обработки различных часовых поясов."""
    app.dependency_overrides[AsyncSession] = lambda: test_db

    doctor = Doctor(name="Тестовый врач", specialization="Терапевт", is_active=True)
    test_db.add(doctor)
    await test_db.commit()
    await test_db.refresh(doctor)

    future_time = get_test_time() + timedelta(days=1)
    appointment_time = future_time.replace(hour=10, minute=0, second=0, microsecond=0)

    # Тестируем различные форматы времени - все должны быть валидны
    test_cases = [
        {
            "time": appointment_time.isoformat(),  # С timezone (локальный TZ)
            "patient": "Пациент с локальным TZ",
        },
        {
            "time": appointment_time.replace(hour=11, minute=0)
            .replace(tzinfo=ZoneInfo("Europe/Moscow"))
            .isoformat(),  # С timezone, другое время
            "patient": "Пациент с timezone",
        },
        {
            "time": (
                appointment_time.replace(hour=12, minute=0).strftime(
                    "%Y-%m-%dT%H:%M:%S"
                )
                + "Z"
            ),  # UTC формат, третье время
            "patient": "Пациент UTC",
        },
    ]

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        for test_case in test_cases:
            response = await ac.post(
                "/appointments",
                json={
                    "doctor_id": doctor.id,
                    "patient_name": test_case["patient"],
                    "start_time": test_case["time"],
                },
            )
            # Все запросы должны быть успешными (разное время)
            assert response.status_code == 201


@pytest.mark.asyncio
async def test_create_appointment_stress_concurrent(test_db: AsyncSession) -> None:
    """Стресс-тест параллельных запросов на создание записей."""
    app.dependency_overrides[AsyncSession] = lambda: test_db

    # Создаем несколько врачей
    doctors = []
    for i in range(3):
        doctor = Doctor(name=f"Врач {i+1}", specialization="Терапевт", is_active=True)
        test_db.add(doctor)
        doctors.append(doctor)

    await test_db.commit()
    for doctor in doctors:
        await test_db.refresh(doctor)

    future_time = get_test_time() + timedelta(days=1)

    async def create_appointments_for_doctor(doctor_id: int, count: int) -> list[int]:
        """Создаем множество записей для одного врача."""
        successful_creates = []
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            for i in range(count):
                appointment_time = future_time.replace(
                    hour=9 + (i // 2), minute=(i % 2) * 30, second=0, microsecond=0
                )
                response = await ac.post(
                    "/appointments",
                    json={
                        "doctor_id": doctor_id,
                        "patient_name": f"Пациент {i+1}",
                        "start_time": appointment_time.isoformat(),
                    },
                )
                if response.status_code == 201:
                    successful_creates.append(response.json()["id"])
        return successful_creates

    # Запускаем параллельные задачи для разных врачей
    tasks = [create_appointments_for_doctor(doctor.id, 8) for doctor in doctors]

    results = await asyncio.gather(*tasks)

    # Проверяем, что все записи созданы успешно
    total_successful = sum(len(result) for result in results)
    assert total_successful == 24  # 3 врача * 8 записей каждому


@pytest.mark.asyncio
async def test_create_appointment_data_validation_unicode(
    test_db: AsyncSession,
) -> None:
    """Тест валидации данных с Unicode символами."""
    app.dependency_overrides[AsyncSession] = lambda: test_db

    doctor = Doctor(name="Тестовый врач", specialization="Терапевт", is_active=True)
    test_db.add(doctor)
    await test_db.commit()
    await test_db.refresh(doctor)

    future_time = get_test_time() + timedelta(days=1)
    appointment_time = future_time.replace(hour=10, minute=0, second=0, microsecond=0)

    # Тестируем различные Unicode символы в имени
    test_cases = [
        "Иван Петрович Сидоров",  # Кириллица
        "José María García",  # Испанские символы
        "张三",  # Китайские символы
        "محمد",  # Арабские символы
        "Müller",  # Немецкие символы
        "Пациент с эмодзи 😊",  # Эмодзи
    ]

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        for i, patient_name in enumerate(test_cases):
            # Каждый пациент в разное время
            current_time = appointment_time.replace(minute=(i % 2) * 30)
            if i >= 2:
                current_time = current_time.replace(hour=10 + (i // 2))

            response = await ac.post(
                "/appointments",
                json={
                    "doctor_id": doctor.id,
                    "patient_name": patient_name,
                    "start_time": current_time.isoformat(),
                },
            )
            assert response.status_code == 201
            data = response.json()
            assert data["patient_name"] == patient_name


@pytest.mark.asyncio
async def test_appointments_options_method(test_db: AsyncSession) -> None:
    """Тест OPTIONS запросов для CORS."""
    app.dependency_overrides[AsyncSession] = lambda: test_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # OPTIONS для коллекции
        response = await ac.options("/appointments")
        # FastAPI автоматически обрабатывает OPTIONS
        assert response.status_code in [200, 405]

        # OPTIONS для конкретной записи
        response = await ac.options("/appointments/1")
        assert response.status_code in [200, 405]


@pytest.mark.asyncio
async def test_timezone_validation_missing_timezone(test_db: AsyncSession) -> None:
    """Тест: время без timezone должно вызывать ошибку валидации."""
    app.dependency_overrides[AsyncSession] = lambda: test_db

    # Создаем активного врача
    doctor = Doctor(name="Тестовый врач", specialization="Терапевт", is_active=True)
    test_db.add(doctor)
    await test_db.commit()
    await test_db.refresh(doctor)

    # Пытаемся создать запись БЕЗ timezone (naive datetime)
    tomorrow = datetime.now() + timedelta(days=1)
    future_time_naive = tomorrow.replace(
        hour=12, minute=0, second=0, microsecond=0
    ).strftime(
        "%Y-%m-%dT%H:%M:%S"
    )  # БЕЗ timezone!

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post(
            "/appointments",
            json={
                "doctor_id": doctor.id,
                "patient_name": "Тестовый пациент",
                "start_time": future_time_naive,  # БЕЗ timezone!
            },
        )

    # Должна быть ошибка валидации
    assert response.status_code == 422
    response_data = response.json()

    # Проверяем, что сообщение содержит информацию о timezone
    error_detail = str(response_data)
    assert "Timezone обязателен" in error_detail
    assert "+03:00" in error_detail  # Должен показать пример с Moscow timezone
    assert "Z" in error_detail  # Должен показать пример с UTC


@pytest.mark.asyncio
async def test_timezone_validation_different_timezones_same_logical_time(
    test_db: AsyncSession,
) -> None:
    """
    Тест: одинаковое логическое время в разных timezone должно
    обрабатываться корректно.
    """
    app.dependency_overrides[AsyncSession] = lambda: test_db

    # Создаем активного врача
    doctor = Doctor(name="Тестовый врач", specialization="Терапевт", is_active=True)
    test_db.add(doctor)
    await test_db.commit()
    await test_db.refresh(doctor)

    # Одинаковое логическое время 12:00 в разных timezone
    tomorrow = datetime.now() + timedelta(days=1)
    moscow_tz = ZoneInfo("Europe/Moscow")
    moscow_12_00 = tomorrow.replace(
        hour=12, minute=0, second=0, microsecond=0, tzinfo=moscow_tz
    ).isoformat()  # 12:00 Moscow
    utc_09_00 = tomorrow.replace(
        hour=9, minute=0, second=0, microsecond=0, tzinfo=timezone.utc
    ).isoformat()  # 09:00 UTC = 12:00 Moscow

    # Первая запись: 12:00 Moscow time
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response1 = await ac.post(
            "/appointments",
            json={
                "doctor_id": doctor.id,
                "patient_name": "Пациент Moscow",
                "start_time": moscow_12_00,
            },
        )

    assert response1.status_code == 201

    # Вторая запись: то же время, но в UTC (09:00 UTC = 12:00 Moscow)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response2 = await ac.post(
            "/appointments",
            json={
                "doctor_id": doctor.id,
                "patient_name": "Пациент UTC",
                "start_time": utc_09_00,
            },
        )

    # Должна быть ошибка конфликта, так как это одно и то же время
    assert response2.status_code == 400
    assert "занят в это время" in response2.json()["detail"]


@pytest.mark.asyncio
async def test_timezone_validation_different_timezones_different_logical_time(
    test_db: AsyncSession,
) -> None:
    """Тест: разное логическое время в разных timezone должно работать нормально."""
    app.dependency_overrides[AsyncSession] = lambda: test_db

    # Создаем активного врача
    doctor = Doctor(name="Тестовый врач", specialization="Терапевт", is_active=True)
    test_db.add(doctor)
    await test_db.commit()
    await test_db.refresh(doctor)

    # Разное логическое время в разных timezone
    tomorrow = datetime.now() + timedelta(days=1)
    moscow_tz = ZoneInfo("Europe/Moscow")
    moscow_12_00 = tomorrow.replace(
        hour=12, minute=0, second=0, microsecond=0, tzinfo=moscow_tz
    ).isoformat()  # 12:00 Moscow
    utc_12_00 = tomorrow.replace(
        hour=12, minute=0, second=0, microsecond=0, tzinfo=timezone.utc
    ).isoformat()  # 12:00 UTC = 15:00 Moscow

    # Первая запись: 12:00 Moscow time
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response1 = await ac.post(
            "/appointments",
            json={
                "doctor_id": doctor.id,
                "patient_name": "Пациент Moscow 12:00",
                "start_time": moscow_12_00,
            },
        )

    assert response1.status_code == 201

    # Вторая запись: 12:00 UTC (что соответствует 15:00 Moscow)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response2 = await ac.post(
            "/appointments",
            json={
                "doctor_id": doctor.id,
                "patient_name": "Пациент UTC 12:00",
                "start_time": utc_12_00,
            },
        )

    assert response2.status_code == 201  # Разное время - должно работать


@pytest.mark.asyncio
async def test_timezone_validation_working_hours_different_timezones(
    test_db: AsyncSession,
) -> None:
    """Тест: валидация рабочих часов должна работать по времени клиники."""
    app.dependency_overrides[AsyncSession] = lambda: test_db

    # Создаем активного врача
    doctor = Doctor(name="Тестовый врач", specialization="Терапевт", is_active=True)
    test_db.add(doctor)
    await test_db.commit()
    await test_db.refresh(doctor)

    # Берем завтрашний день для теста
    tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
    # 06:00 UTC = 09:00 Moscow (рабочее время клиники)
    utc_06_00 = tomorrow.replace(hour=6, minute=0, second=0, microsecond=0).isoformat()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post(
            "/appointments",
            json={
                "doctor_id": doctor.id,
                "patient_name": "Тестовый пациент",
                "start_time": utc_06_00,
            },
        )

    assert response.status_code == 201  # Должно работать

    # 05:00 UTC = 08:00 Moscow (НЕ рабочее время клиники)
    utc_05_00 = tomorrow.replace(hour=5, minute=0, second=0, microsecond=0).isoformat()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post(
            "/appointments",
            json={
                "doctor_id": doctor.id,
                "patient_name": "Тестовый пациент 2",
                "start_time": utc_05_00,
            },
        )

    assert response.status_code == 422
    error_text = response.text
    assert "9:00 до 17:30" in error_text
    assert "времени клиники" in error_text
