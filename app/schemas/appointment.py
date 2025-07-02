"""Схемы записей на прием."""

import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.settings import settings

logger = logging.getLogger(__name__)


class AppointmentBase(BaseModel):
    """Базовая схема записи на прием."""

    doctor_id: int = Field(
        ..., ge=1, description="ID врача (должен быть положительным)", examples=[1]
    )
    patient_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Имя пациента",
        examples=["Иван Иванов"],
    )
    start_time: datetime = Field(
        ...,
        description=(
            "Время начала приема (с обязательным timezone, " "хранится в UTC)"
        ),
        examples=["2025-07-15T11:30:00+03:00", "2025-07-15T11:30:00Z"],
    )


class AppointmentCreate(AppointmentBase):
    """Схема для создания записи на прием."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "doctor_id": 1,
                "patient_name": "Иван Иванов",
                "start_time": "2025-07-15T11:30:00+03:00",
            }
        }
    )

    @field_validator("patient_name")
    @classmethod
    def validate_patient_name(_, v: str) -> str:
        """Валидация имени пациента."""
        if not v.strip():
            raise ValueError("Имя пациента не может быть пустым")
        return v.strip()

    @field_validator("start_time")
    @classmethod
    def validate_start_time(_, v: datetime) -> datetime:
        """
        Валидация времени записи с обязательным timezone.
        - Требуем обязательный timezone для избежания путаницы
        - Валидируем в том timezone, который указал пользователь
        - Храним в UTC
        """
        # ТРЕБУЕМ обязательный timezone для избежания путаницы
        if v.tzinfo is None:
            raise ValueError(
                "Timezone обязателен! Укажите время с timezone, например: "
                "2025-07-01T12:00:00+03:00 (Moscow) или "
                "2025-07-01T12:00:00Z (UTC). "
                f"Локальный timezone клиники: {settings.timezone}"
            )

        # Валидируем время в том timezone, который указал пользователь
        user_timezone = v.tzinfo

        # Текущее время в timezone пользователя для корректного сравнения
        now_user_tz = datetime.now(user_timezone)

        # Проверка, что время в будущем (в timezone пользователя)
        if v <= now_user_tz:
            raise ValueError("Время записи должно быть в будущем")

        # Получаем клинический timezone для валидации рабочих часов
        clinic_tz = ZoneInfo(settings.timezone)
        v_clinic_tz = v.astimezone(clinic_tz)

        # Проверка рабочих часов клиники (9:00 - 17:30 по времени клиники)
        if (
            v_clinic_tz.hour < 9
            or v_clinic_tz.hour > 17
            or (v_clinic_tz.hour == 17 and v_clinic_tz.minute > 30)
        ):
            raise ValueError(
                f"Записи принимаются с 9:00 до 17:30 по времени клиники "
                f"({settings.timezone}). Ваше время {v.strftime('%H:%M')} "
                f"соответствует {v_clinic_tz.strftime('%H:%M')} времени клиники"
            )

        # Проверка рабочих дней (по времени клиники)
        if v_clinic_tz.weekday() > 4:  # 5=суббота, 6=воскресенье
            raise ValueError("Записи принимаются только в рабочие дни (пн-пт)")

        # Проверка интервала записи (кратно 30 минутам) по времени клиники
        if (
            v_clinic_tz.minute not in [0, 30]
            or v_clinic_tz.second != 0
            or v_clinic_tz.microsecond != 0
        ):
            raise ValueError(
                "Запись возможна только в начале часа или в половину "
                "(по времени клиники)"
            )

        # Логируем для отладки
        logger.info(
            f"Время записи: {v.isoformat()} ({user_timezone}) -> "
            f"время клиники: {v_clinic_tz.strftime('%H:%M %Z')} -> "
            f"UTC: {v.astimezone(timezone.utc).isoformat()}"
        )

        # Храним в UTC
        return v.astimezone(timezone.utc)


class AppointmentResponse(AppointmentBase):
    """Схема ответа записи на прием."""

    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
