"""CRUD операции для записей на прием."""

from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.doctor import check_doctor_availability
from app.models.appointment import Appointment
from app.schemas.appointment import AppointmentCreate


async def create_appointment_with_validation(
    db: AsyncSession, appointment: AppointmentCreate
) -> Appointment:
    """
    Создать новую запись на прием с полной валидацией и проверкой конфликтов.

    Эта функция НЕ управляет транзакциями - вызывающий код должен
    управлять commit/rollback.
    """
    # Проверяем доступность врача с блокировкой
    is_available, doctor = await check_doctor_availability(
        db, appointment.doctor_id, appointment.start_time
    )

    if doctor is None:
        raise ValueError(f"Врач с ID {appointment.doctor_id} не найден или неактивен")

    if not is_available:
        raise ValueError("Врач уже занят в это время")

    # Создаем запись
    db_appointment = Appointment(**appointment.model_dump())
    db.add(db_appointment)

    # НЕ делаем flush/refresh здесь - оставляем управление транзакциями вызывающему коду
    return db_appointment


async def get_appointment(
    db: AsyncSession, appointment_id: int
) -> Optional[Appointment]:
    """Получить запись на прием по ID."""
    result = await db.execute(
        select(Appointment).where(Appointment.id == appointment_id)
    )
    return result.scalar_one_or_none()


async def get_doctor_appointments(
    db: AsyncSession, doctor_id: int, start_time: datetime, end_time: datetime
) -> list[Appointment]:
    """Получить все записи врача в указанном временном диапазоне."""
    result = await db.execute(
        select(Appointment)
        .where(
            Appointment.doctor_id == doctor_id,
            Appointment.start_time >= start_time,
            Appointment.start_time < end_time,
        )
        .order_by(Appointment.start_time)
    )
    return list(result.scalars().all())
