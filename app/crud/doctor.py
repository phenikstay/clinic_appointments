"""CRUD операции для врачей."""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.appointment import Appointment
from app.models.doctor import Doctor


async def get_doctor(
    db: AsyncSession, doctor_id: int, active_only: bool = True
) -> Optional[Doctor]:
    """Получить врача по ID. Если active_only=True, то только активного."""
    query = select(Doctor).where(Doctor.id == doctor_id)
    if active_only:
        query = query.where(Doctor.is_active)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_doctors(db: AsyncSession, active_only: bool = True) -> List[Doctor]:
    """Получить список врачей."""
    query = select(Doctor)
    if active_only:
        query = query.where(Doctor.is_active)

    result = await db.execute(query.order_by(Doctor.name))
    return list(result.scalars().all())


async def get_valid_doctor_ids(db: AsyncSession) -> set[int]:
    """Получить множество ID активных врачей для валидации."""
    result = await db.execute(select(Doctor.id).where(Doctor.is_active))
    return set(result.scalars().all())


async def check_doctor_availability(
    db: AsyncSession, doctor_id: int, start_time: datetime
) -> tuple[bool, Optional[Doctor]]:
    """
    Проверить доступность врача с блокировкой для предотвращения race condition.

    Возвращает (is_available, doctor) где:
    - is_available: True если врач доступен, False если занят
    - doctor: объект врача или None если врач не найден/неактивен
    """
    # Сначала проверяем и блокируем врача
    doctor_result = await db.execute(
        select(Doctor)
        .where(Doctor.id == doctor_id, Doctor.is_active.is_(True))
        .with_for_update()  # Блокируем врача для предотвращения race condition
    )
    doctor = doctor_result.scalar_one_or_none()

    if doctor is None:
        return False, None

    # Проверяем, нет ли конфликтующих записей (с блокировкой)
    existing_appointment = await db.execute(
        select(Appointment)
        .where(Appointment.doctor_id == doctor_id, Appointment.start_time == start_time)
        .with_for_update()  # Блокируем существующие записи
    )

    if existing_appointment.scalar_one_or_none() is not None:
        return False, doctor

    return True, doctor
