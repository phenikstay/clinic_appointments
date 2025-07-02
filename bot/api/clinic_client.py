"""Клиент для взаимодействия с API клиники."""

from datetime import datetime, timedelta, timezone
from typing import List, Optional, Union
from zoneinfo import ZoneInfo

import aiohttp
from pydantic import BaseModel, field_validator

from bot.config.settings import bot_settings


def get_clinic_timezone() -> ZoneInfo:
    """Получить timezone клиники."""
    return ZoneInfo(bot_settings.timezone)


def get_local_time() -> datetime:
    """Получить текущее время в timezone клиники."""
    return datetime.now(get_clinic_timezone())


def to_utc(dt: datetime) -> datetime:
    """Преобразовать datetime в UTC."""
    if dt.tzinfo is None:
        # Если timezone не указан, считаем, что это время клиники
        dt = dt.replace(tzinfo=get_clinic_timezone())
    return dt.astimezone(timezone.utc)


def to_clinic_timezone(dt: datetime) -> datetime:
    """Преобразовать datetime в timezone клиники для отображения."""
    if dt.tzinfo is None:
        # Если timezone не указан, считаем, что это UTC
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(get_clinic_timezone())


class AvailableSlot(BaseModel):
    """Доступный слот для записи."""

    datetime_obj: datetime
    datetime_str: str

    @property
    def date_str(self) -> str:
        """Дата слота в формате YYYY-MM-DD (по времени клиники)."""
        clinic_time = to_clinic_timezone(self.datetime_obj)
        return clinic_time.strftime("%Y-%m-%d")

    @property
    def time_str(self) -> str:
        """Время слота в формате HH:MM (по времени клиники)."""
        clinic_time = to_clinic_timezone(self.datetime_obj)
        return clinic_time.strftime("%H:%M")

    @property
    def display_datetime(self) -> datetime:
        """Время слота в timezone клиники для отображения пользователю."""
        return to_clinic_timezone(self.datetime_obj)


class Doctor(BaseModel):
    """Информация о враче."""

    id: int
    name: str
    specialization: str

    # Alias для совместимости со STUB-обработчиками
    @property
    def specialty(self) -> str:
        """Возврат specialization (alias)."""
        return self.specialization


class AppointmentResponse(BaseModel):
    """Ответ с данными записи."""

    id: int
    doctor_id: int
    patient_name: str
    start_time: datetime
    created_at: datetime

    @field_validator("start_time", "created_at", mode="before")
    @classmethod
    def parse_datetime_with_timezone(_, v: Union[str, datetime]) -> datetime:
        """Парсинг datetime с правильной обработкой timezone."""
        if isinstance(v, str):
            dt = datetime.fromisoformat(v)
            # Если timezone не указан, считаем что это UTC (как в API)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        return v

    @property
    def start_time_clinic(self) -> datetime:
        """Время начала записи в timezone клиники."""
        return to_clinic_timezone(self.start_time)

    @property
    def created_at_clinic(self) -> datetime:
        """Время создания записи в timezone клиники."""
        return to_clinic_timezone(self.created_at)


class ClinicAPIClient:
    """Клиент для работы с API клиники."""

    def __init__(self, base_url: str):
        """Инициализация клиента."""
        self.base_url = base_url.rstrip("/")

    async def get_doctors(self) -> List[Doctor]:
        """STUB: Получить список врачей."""
        # Заглушка - возвращаем тестовых врачей
        return [
            Doctor(id=1, name="Доктор Иванов", specialization="Терапевт"),
            Doctor(id=2, name="Доктор Петров", specialization="Кардиолог"),
            Doctor(id=3, name="Доктор Сидоров", specialization="Невролог"),
        ]

    async def get_available_slots(
        self, doctor_id: int, days_ahead: int = 7
    ) -> List[AvailableSlot]:
        """STUB: Получить доступные слоты для записи."""
        slots = []
        # clinic_tz = get_clinic_timezone()

        for day_offset in range(1, days_ahead + 1):
            # Генерируем дату в timezone клиники
            date = get_local_time() + timedelta(days=day_offset)

            # Пропускаем выходные
            if date.weekday() >= 5:
                continue

            # Генерируем слоты с 9:00 до 17:30 каждые 30 минут (по времени клиники)
            for hour in range(9, 18):
                for minute in [0, 30]:
                    # Создаем время в timezone клиники
                    slot_time_clinic = date.replace(
                        hour=hour, minute=minute, second=0, microsecond=0
                    )

                    # Конвертируем в UTC для передачи в API
                    slot_time_utc = to_utc(slot_time_clinic)

                    slots.append(
                        AvailableSlot(
                            datetime_obj=slot_time_utc,
                            datetime_str=slot_time_utc.isoformat(),
                        )
                    )

        return slots

    async def create_appointment(
        self, doctor_id: int, patient_name: str, start_time: Union[str, datetime]
    ) -> Optional[AppointmentResponse]:
        """
        Создать запись на прием.

        Args:
            doctor_id: ID врача
            patient_name: Имя пациента
            start_time: Время записи (строка с timezone или datetime)
        """
        # Приводим start_time к нужному формату для API
        if isinstance(start_time, datetime):
            # Если datetime, конвертируем в UTC и сериализуем
            start_time_api = to_utc(start_time).isoformat()
        else:
            # Если строка, используем как есть (полагаемся на jsonable_encoder FastAPI)
            start_time_api = start_time

        appointment_data = {
            "doctor_id": doctor_id,
            "patient_name": patient_name,
            "start_time": start_time_api,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/appointments",
                    json=appointment_data,
                    headers={"Content-Type": "application/json"},
                ) as response:
                    if response.status == 201:
                        data = await response.json()
                        return AppointmentResponse.model_validate(data)
                    else:
                        print(f"Ошибка создания записи: {response.status}")
                        error_text = await response.text()
                        print(f"Детали ошибки: {error_text}")
                        return None

        except Exception as e:
            print(f"Ошибка при создании записи: {e}")
            return None

    async def get_appointment(
        self, appointment_id: int
    ) -> Optional[AppointmentResponse]:
        """Получить запись по ID."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/appointments/{appointment_id}"
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return AppointmentResponse.model_validate(data)
                    else:
                        return None

        except Exception as e:
            print(f"Ошибка при получении записи: {e}")
            return None

    # STUB-методы, требуемые обработчиками Telegram-бота
    async def get_all_doctors(self) -> List[Doctor]:
        """STUB: Возвращает всех врачей (эквивалент get_doctors)."""
        return await self.get_doctors()

    async def get_doctor(self, doctor_id: int) -> Optional[Doctor]:
        """STUB: Получить врача по ID."""
        doctors = await self.get_doctors()
        for d in doctors:
            if d.id == doctor_id:
                return d
        return None
