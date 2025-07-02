"""Модульные тесты для CRUD операций."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, Mock
from zoneinfo import ZoneInfo

import pytest
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import settings
from app.crud.appointment import create_appointment_with_validation, get_appointment
from app.models.appointment import Appointment
from app.schemas.appointment import AppointmentCreate


def get_test_time() -> datetime:
    """Получить текущее время в тестовом timezone."""
    return datetime.now(ZoneInfo(settings.timezone))


@pytest.mark.asyncio
async def test_create_appointment() -> None:
    """Тест создания записи на прием."""
    # Подготовка
    db_mock = AsyncMock(spec=AsyncSession)

    # Моки для врача (должен существовать и быть активным)
    mock_doctor = Mock()
    mock_doctor.id = 1
    mock_doctor.name = "Тестовый врач"
    mock_doctor.is_active = True

    mock_doctor_result = MagicMock()
    mock_doctor_result.scalar_one_or_none.return_value = mock_doctor

    # Мок для проверки конфликтующих записей (должен вернуть None - нет конфликтов)
    mock_appointment_result = MagicMock()
    mock_appointment_result.scalar_one_or_none.return_value = None

    # Настройка последовательности вызовов execute:
    # 1-й вызов - поиск врача, 2-й вызов - поиск конфликтующих записей
    db_mock.execute.side_effect = [mock_doctor_result, mock_appointment_result]

    future_time = get_test_time() + timedelta(days=1)
    test_time = future_time.replace(hour=10, minute=0, second=0, microsecond=0)

    appointment_data = AppointmentCreate(
        doctor_id=1,
        patient_name="Тестовый пациент",
        start_time=test_time,
    )

    # Мокируем добавление объекта
    def mock_add(obj):
        obj.id = 1
        obj.doctor_id = 1
        obj.patient_name = "Тестовый пациент"
        obj.start_time = test_time
        return obj

    db_mock.add.side_effect = mock_add

    # Выполнение
    result = await create_appointment_with_validation(
        db=db_mock, appointment=appointment_data
    )

    # Проверка
    assert result.id == 1
    assert result.doctor_id == 1
    assert result.patient_name == "Тестовый пациент"
    assert result.start_time == test_time

    # Проверяем что были сделаны правильные вызовы
    assert db_mock.execute.call_count == 2  # Поиск врача + поиск конфликтов
    db_mock.add.assert_called_once()


@pytest.mark.asyncio
async def test_get_appointment() -> None:
    """Тест получения записи на прием."""
    # Подготовка
    db_mock = AsyncMock(spec=AsyncSession)
    mock_appointment = Mock(spec=Appointment)
    mock_appointment.id = 1
    mock_appointment.doctor_id = 1
    mock_appointment.patient_name = "Тестовый пациент"

    # Настройка mock для успешного результата
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_appointment
    db_mock.execute.return_value = mock_result

    # Выполнение
    result = await get_appointment(db=db_mock, appointment_id=1)

    # Проверка
    assert result is not None
    assert result.id == 1
    assert result.doctor_id == 1
    assert result.patient_name == "Тестовый пациент"
    db_mock.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_appointment_not_found() -> None:
    """Тест получения несуществующей записи."""
    # Подготовка
    db_mock = AsyncMock(spec=AsyncSession)

    # Настройка mock для отсутствующего результата
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    db_mock.execute.return_value = mock_result

    # Выполнение
    result = await get_appointment(db=db_mock, appointment_id=999)

    # Проверка
    assert result is None
    db_mock.execute.assert_called_once()


class TestAppointmentValidation:
    """Тесты валидации данных записи."""

    def test_appointment_validation_past_time(self) -> None:
        """Тест валидации времени в прошлом."""
        past_time = get_test_time() - timedelta(hours=1)

        with pytest.raises(ValidationError) as exc_info:
            AppointmentCreate(
                doctor_id=1,
                patient_name="Тестовый пациент",
                start_time=past_time,
            )

        assert "Время записи должно быть в будущем" in str(exc_info.value)

    def test_appointment_validation_working_hours(self) -> None:
        """Тест валидации рабочих часов."""
        future_time = get_test_time() + timedelta(days=1)
        # Время после 18:00
        late_time = future_time.replace(hour=19, minute=0, second=0, microsecond=0)

        with pytest.raises(ValidationError) as exc_info:
            AppointmentCreate(
                doctor_id=1,
                patient_name="Тестовый пациент",
                start_time=late_time,
            )

        assert "Записи принимаются с 9:00 до 17:30" in str(exc_info.value)

    def test_appointment_validation_weekend(self) -> None:
        """Тест валидации выходных дней."""
        # Найдем следующую субботу
        today = get_test_time()
        days_until_saturday = (5 - today.weekday()) % 7
        if days_until_saturday == 0:  # Если сегодня суббота
            days_until_saturday = 7
        saturday = today + timedelta(days=days_until_saturday)
        weekend_time = saturday.replace(hour=10, minute=0, second=0, microsecond=0)

        with pytest.raises(ValidationError) as exc_info:
            AppointmentCreate(
                doctor_id=1,
                patient_name="Тестовый пациент",
                start_time=weekend_time,
            )

        assert "Записи принимаются только в рабочие дни" in str(exc_info.value)

    def test_appointment_validation_wrong_minutes(self) -> None:
        """Тест валидации неправильных минут."""
        future_time = get_test_time() + timedelta(days=1)
        # Время с минутами не кратными 30
        wrong_time = future_time.replace(hour=10, minute=15, second=0, microsecond=0)

        with pytest.raises(ValidationError) as exc_info:
            AppointmentCreate(
                doctor_id=1,
                patient_name="Тестовый пациент",
                start_time=wrong_time,
            )

        assert "Запись возможна только в начале часа или в половину" in str(
            exc_info.value
        )
