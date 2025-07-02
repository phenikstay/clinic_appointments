"""
Обработчик анализа симптомов пациентов

ВНИМАНИЕ: Это STUB-реализация для демонстрации архитектуры!
"""

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from bot.ai.analyzer import SymptomAnalyzer
from bot.api.clinic_client import ClinicAPIClient
from bot.config.settings import bot_settings

router = Router()


class AppointmentStates(StatesGroup):
    """Состояния для записи на прием"""

    choosing_doctor = State()
    selecting_time = State()


@router.message(F.text & ~F.text.startswith("/"))
async def handle_symptoms(message: Message, state: FSMContext) -> None:
    """
    Обработчик описания симптомов от пациента.
    STUB: Демонстрирует архитектуру ИИ-анализа и выбора врача.
    """
    symptoms = message.text or ""

    # Показать индикатор печати
    if message.bot:
        await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")

    try:
        analyzer = SymptomAnalyzer()
        recommendations = await analyzer.analyze_symptoms(symptoms)

        if not recommendations:
            await message.answer(
                "❌ Не удалось проанализировать симптомы. "
                "Попробуйте описать их более подробно."
            )
            return

        # Создание клавиатуры с рекомендациями врачей
        keyboard = []
        for rec in recommendations[:3]:  # Показываем топ-3 рекомендации
            confidence_text = f"{rec.confidence}%" if rec.confidence else ""
            button_text = f"{rec.specialist_name} {confidence_text}".strip()

            keyboard.append(
                [
                    InlineKeyboardButton(
                        text=button_text, callback_data=f"select_doctor_{rec.doctor_id}"
                    )
                ]
            )

        # Добавляем кнопку "Показать всех врачей"
        keyboard.append(
            [
                InlineKeyboardButton(
                    text="📋 Показать всех врачей", callback_data="show_all_doctors"
                )
            ]
        )

        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)

        response_text = (
            "🤖 *Анализ симптомов завершён*\n\n"
            "На основе описанных симптомов рекомендую:\n\n"
        )

        for i, rec in enumerate(recommendations[:3], 1):
            response_text += f"{i}. {rec.specialist_name}"
            if rec.confidence:
                response_text += f" - {rec.confidence}% соответствие"
            if rec.reasoning:
                response_text += f"\n   _{rec.reasoning}_"
            response_text += "\n\n"

        response_text += "Выберите специалиста для записи:"

        await message.answer(
            response_text, reply_markup=reply_markup, parse_mode="Markdown"
        )

        # Сохраняем контекст пользователя
        await state.update_data(symptoms=symptoms, recommendations=recommendations)
        await state.set_state(AppointmentStates.choosing_doctor)

    except Exception as e:
        await message.answer(
            f"❌ STUB: Произошла ошибка при анализе симптомов: {str(e)}\n"
            "В реальной реализации здесь будет обработка ошибок."
        )


@router.callback_query(F.data == "show_all_doctors")
async def show_all_doctors(query: CallbackQuery, state: FSMContext) -> None:
    """STUB: Показать список всех доступных врачей"""
    clinic_client = ClinicAPIClient(bot_settings.clinic_api_url)

    try:
        doctors = await clinic_client.get_all_doctors()

        keyboard = []
        for doctor in doctors:
            keyboard.append(
                [
                    InlineKeyboardButton(
                        text=f"{doctor.name} ({doctor.specialty})",
                        callback_data=f"select_doctor_{doctor.id}",
                    )
                ]
            )

        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)

        if query.message and hasattr(query.message, "edit_text"):
            await query.message.edit_text(
                "👨‍⚕️ *Все доступные врачи (STUB):*\n\n" "Выберите специалиста:",
                reply_markup=reply_markup,
                parse_mode="Markdown",
            )

    except Exception as e:
        if query.message and hasattr(query.message, "edit_text"):
            await query.message.edit_text(
                f"❌ STUB: Ошибка получения списка врачей: {str(e)}"
            )

    await query.answer()


@router.callback_query(F.data.startswith("select_doctor_"))
async def handle_doctor_selection(query: CallbackQuery, state: FSMContext) -> None:
    """STUB: Обработчик выбора врача пациентом"""
    if query.data:
        doctor_id = int(query.data.split("_")[2])
        await show_available_slots(query, state, doctor_id)


async def show_available_slots(
    query: CallbackQuery, state: FSMContext, doctor_id: int
) -> None:
    """STUB: Показать доступные слоты времени для выбранного врача"""
    clinic_client = ClinicAPIClient(bot_settings.clinic_api_url)

    try:
        # Получаем информацию о враче
        doctor = await clinic_client.get_doctor(doctor_id)

        if not doctor:
            if query.message and hasattr(query.message, "edit_text"):
                await query.message.edit_text("❌ STUB: Врач не найден")
            return

        # STUB: Получаем свободные слоты
        available_slots = await clinic_client.get_available_slots(
            doctor_id, days_ahead=7
        )

        if not available_slots:
            if query.message and hasattr(query.message, "edit_text"):
                await query.message.edit_text(
                    f"😕 STUB: У врача {doctor.name} нет свободных слотов "
                    "на ближайшую неделю.\n\n"
                    "В реальной реализации здесь будет интеграция с календарём."
                )
            await query.answer()
            return

        keyboard = []
        for slot in available_slots[:5]:  # Показываем максимум 5 слотов в STUB
            slot_text = f"{slot.date_str} в {slot.time_str}"
            keyboard.append(
                [
                    InlineKeyboardButton(
                        text=slot_text,
                        callback_data=f"book_{doctor_id}_{slot.datetime_str}",
                    )
                ]
            )

        # Кнопка "Назад к выбору врача"
        keyboard.append(
            [
                InlineKeyboardButton(
                    text="⬅️ Назад к выбору врача", callback_data="back_to_doctors"
                )
            ]
        )

        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)

        message_text = (
            f"📅 *STUB: Доступное время у {doctor.name}*\n"
            f"_{doctor.specialty}_\n\n"
            "Выберите удобное время:"
        )

        if query.message and hasattr(query.message, "edit_text"):
            await query.message.edit_text(
                message_text, reply_markup=reply_markup, parse_mode="Markdown"
            )

        # Сохраняем выбранного врача в контексте
        await state.update_data(selected_doctor_id=doctor_id)
        await state.set_state(AppointmentStates.selecting_time)

    except Exception as e:
        if query.message and hasattr(query.message, "edit_text"):
            await query.message.edit_text(
                f"❌ STUB: Ошибка получения расписания: {str(e)}"
            )

    await query.answer()


@router.callback_query(F.data.startswith("book_"))
async def handle_appointment_booking(query: CallbackQuery, state: FSMContext) -> None:
    """Обработчик записи на приём с реальным созданием через API"""
    if not query.data:
        return

    parts = query.data.split("_", 2)
    doctor_id = int(parts[1])
    datetime_str = parts[2]

    clinic_client = ClinicAPIClient(bot_settings.clinic_api_url)

    try:
        # Получаем имя пользователя как имя пациента
        patient_name = query.from_user.full_name or f"Пользователь {query.from_user.id}"

        # Получаем информацию о враче для отображения
        doctor = await clinic_client.get_doctor(doctor_id)
        doctor_name = doctor.name if doctor else f"Врач ID {doctor_id}"

        # Показываем индикатор загрузки
        if query.message and hasattr(query.message, "edit_text"):
            await query.message.edit_text(
                "⏳ Создаю запись на приём...",
                parse_mode="Markdown",
            )

        # Создаем запись через API (используем datetime_str как есть - с UTC)
        appointment = await clinic_client.create_appointment(
            doctor_id=doctor_id,
            patient_name=patient_name,
            start_time=datetime_str,  # Передаем строку как есть
        )

        if appointment:
            # Успешное создание записи
            appointment_time_clinic = appointment.start_time_clinic
            time_str = appointment_time_clinic.strftime("%d.%m.%Y в %H:%M")

            success_message = (
                f"✅ *Запись успешно создана!*\n\n"
                f"📋 Номер записи: {appointment.id}\n"
                f"👨‍⚕️ Врач: {doctor_name}\n"
                f"📅 Дата и время: {time_str}\n"
                f"👤 Пациент: {patient_name}\n\n"
                f"💡 Время указано в timezone клиники ({bot_settings.timezone})\n"
                "⏰ Не забудьте прийти на приём вовремя!"
            )

            if query.message and hasattr(query.message, "edit_text"):
                await query.message.edit_text(
                    success_message,
                    parse_mode="Markdown",
                )
        else:
            # Ошибка создания записи
            error_message = (
                "❌ *Не удалось создать запись*\n\n"
                "Возможные причины:\n"
                "• Время уже занято другим пациентом\n"
                "• Врач недоступен\n"
                "• Проблемы с подключением к серверу\n\n"
                "Попробуйте выбрать другое время."
            )

            if query.message and hasattr(query.message, "edit_text"):
                await query.message.edit_text(
                    error_message,
                    parse_mode="Markdown",
                )

    except Exception as e:
        if query.message and hasattr(query.message, "edit_text"):
            await query.message.edit_text(
                f"❌ *Ошибка при записи на приём*\n\n"
                f"Техническая ошибка: {str(e)}\n\n"
                f"Попробуйте позже или обратитесь к администратору.",
                parse_mode="Markdown",
            )

    await query.answer()
    await state.clear()


@router.callback_query(F.data == "back_to_doctors")
async def handle_back_to_doctors(query: CallbackQuery, state: FSMContext) -> None:
    """STUB: Возврат к выбору врача"""
    user_data = await state.get_data()
    recommendations = user_data.get("recommendations", [])

    if recommendations:
        # Восстанавливаем исходное меню с рекомендациями
        keyboard = []
        for rec in recommendations[:3]:
            confidence_text = f"{rec.confidence}%" if rec.confidence else ""
            button_text = f"{rec.specialist_name} {confidence_text}".strip()

            keyboard.append(
                [
                    InlineKeyboardButton(
                        text=button_text, callback_data=f"select_doctor_{rec.doctor_id}"
                    )
                ]
            )

        keyboard.append(
            [
                InlineKeyboardButton(
                    text="📋 Показать всех врачей", callback_data="show_all_doctors"
                )
            ]
        )

        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)

        response_text = (
            "🤖 *Анализ симптомов завершён*\n\n"
            "На основе описанных симптомов рекомендую:\n\n"
        )

        for i, rec in enumerate(recommendations[:3], 1):
            response_text += f"{i}. {rec.specialist_name}"
            if rec.confidence:
                response_text += f" - {rec.confidence}% соответствие"
            if rec.reasoning:
                response_text += f"\n   _{rec.reasoning}_"
            response_text += "\n\n"

        response_text += "Выберите специалиста для записи:"

        if query.message and hasattr(query.message, "edit_text"):
            await query.message.edit_text(
                response_text, reply_markup=reply_markup, parse_mode="Markdown"
            )
    else:
        await show_all_doctors(query, state)

    await state.set_state(AppointmentStates.choosing_doctor)
    await query.answer()
