"""API эндпоинты для записей на прием."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.appointment import create_appointment_with_validation, get_appointment
from app.db.database import get_db
from app.schemas.appointment import AppointmentCreate, AppointmentResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/appointments", tags=["appointments"])


@router.post(
    "", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED
)
async def create_new_appointment(
    appointment: AppointmentCreate, db: AsyncSession = Depends(get_db)
) -> AppointmentResponse:
    """
    Создать новую запись на прием.

    Полная валидация включает:
    - Проверку существования и активности врача
    - Проверку доступности времени (нет конфликтующих записей)
    - Валидацию рабочих часов (9:00-17:30)
    - Валидацию рабочих дней (пн-пт)
    - Валидацию интервалов времени (кратность 30 минутам)
    - Проверку, что время записи в будущем

    Все операции выполняются в единой транзакции с блокировкой
    для предотвращения race condition.
    """
    try:
        # Создаем запись с валидацией (без коммита)
        db_appointment = await create_appointment_with_validation(
            db=db, appointment=appointment
        )

        # Сбрасываем изменения в БД для получения ID (но не коммитим)
        await db.flush()
        await db.refresh(db_appointment)

        # Фиксируем транзакцию только после успешного создания
        await db.commit()

        logger.info(
            f"Создана запись {db_appointment.id} для врача "
            f"{db_appointment.doctor_id} на {db_appointment.start_time}"
        )
        return AppointmentResponse.model_validate(db_appointment)

    except ValueError as e:
        # Бизнес-логические ошибки (врач не найден, занят и т.д.)
        await db.rollback()
        logger.warning(f"Ошибка валидации при создании записи: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except IntegrityError as e:
        # Ошибки целостности БД (constraint violations)
        await db.rollback()
        logger.warning(f"Ошибка целостности при создании записи: {e}")
        # Дополнительная проверка для понятного сообщения об ошибке
        if "unique_doctor_time" in str(e):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Врач уже занят в это время",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Нарушение ограничений целостности данных",
            )
    except SQLAlchemyError as e:
        # Общие ошибки БД
        await db.rollback()
        logger.error(f"Ошибка базы данных при создании записи: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка базы данных",
        )
    except Exception as e:
        # Неожиданные ошибки
        try:
            await db.rollback()
        except Exception:  # noqa: BLE001
            pass
        logger.error(f"Неожиданная ошибка при создании записи: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Внутренняя ошибка сервера",
        )


@router.get("/{appointment_id}", response_model=AppointmentResponse)
async def read_appointment(
    appointment_id: int, db: AsyncSession = Depends(get_db)
) -> AppointmentResponse:
    """Получить запись на прием по ID."""
    try:
        db_appointment = await get_appointment(db=db, appointment_id=appointment_id)
        if db_appointment is None:
            logger.warning(f"Запись {appointment_id} не найдена")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Запись не найдена"
            )
        logger.info(f"Получена запись {appointment_id}")
        return AppointmentResponse.model_validate(db_appointment)
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Ошибка базы данных при получении записи {appointment_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка базы данных",
        )
    except Exception as e:
        logger.error(f"Неожиданная ошибка при получении записи {appointment_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Внутренняя ошибка сервера",
        )
