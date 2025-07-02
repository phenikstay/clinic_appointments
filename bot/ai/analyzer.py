"""
ИИ-анализатор симптомов пациентов

ВНИМАНИЕ: Это STUB-реализация для демонстрации архитектуры!
"""

import json
from dataclasses import dataclass
from typing import List, Optional, cast

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam

from bot.config.settings import bot_settings


@dataclass
class DoctorRecommendation:
    """Рекомендация врача на основе анализа симптомов"""

    doctor_id: int
    specialist_name: str
    confidence: Optional[int]  # Процент соответствия 0-100
    reasoning: Optional[str]  # Обоснование рекомендации


class SymptomAnalyzer:
    """
    STUB: Анализатор симптомов с использованием ИИ

    Демонстрирует архитектуру интеграции с OpenAI GPT-4
    и fallback на rule-based анализ.
    """

    def __init__(self) -> None:
        self.client: Optional[AsyncOpenAI] = None
        if bot_settings.openai_api_key:
            self.client = AsyncOpenAI(api_key=bot_settings.openai_api_key)

        # STUB: Мапинг специальностей на ID врачей (в реальности будет из API)
        self.specialties_map = {
            "терапевт": [1, 2],
            "невролог": [3, 4],
            "кардиолог": [5],
            "офтальмолог": [6],
            "лор": [7],
            "дерматолог": [8],
            "гастроэнтеролог": [9],
        }

    async def analyze_symptoms(self, symptoms: str) -> List[DoctorRecommendation]:
        """
        STUB: Анализирует симптомы и возвращает список рекомендаций врачей.

        Args:
            symptoms: Описание симптомов от пациента

        Returns:
            Список рекомендаций врачей, отсортированный по релевантности
        """
        print(f"STUB: Анализируем симптомы: {symptoms}")

        try:
            if self.client:
                return await self._analyze_with_openai(symptoms)
            else:
                return await self._analyze_with_rules(symptoms)
        except Exception as e:
            # Переключение на анализ по правилам при ошибках ИИ
            print(f"STUB: Ошибка ИИ-анализа: {str(e)}, переключаемся на rule-based")
            return await self._analyze_with_rules(symptoms)

    async def _analyze_with_openai(self, symptoms: str) -> List[DoctorRecommendation]:
        """STUB: Анализ симптомов через OpenAI GPT"""

        prompt = f"""
        Ты медицинский ИИ-помощник в клинике. Проанализируй симптомы пациента и
        рекомендуй подходящих специалистов.

        Симптомы пациента: {symptoms}

        Доступные специалисты:
        - Терапевт (общие заболевания)
        - Невролог (нервная система, головные боли)
        - Кардиолог (сердце и сосуды)
        - Офтальмолог (глаза и зрение)
        - ЛОР (ухо, горло, нос)
        - Дерматолог (кожа)
        - Гастроэнтеролог (пищеварение)

        Верни ответ в формате JSON:
        {{
            "recommendations": [
                {{
                    "specialty": "название специальности",
                    "confidence": процент от 0 до 100,
                    "reasoning": "краткое обоснование"
                }}
            ]
        }}

        Отсортируй рекомендации по релевантности (наиболее подходящие первые).
        Максимум 3 рекомендации.
        """

        print("STUB: Отправляем запрос к OpenAI...")

        if not self.client:
            return []

        # Формируем сообщения в корректном типе
        messages: List[ChatCompletionMessageParam] = cast(
            List[ChatCompletionMessageParam],
            [
                {"role": "system", "content": "Ты опытный медицинский консультант."},
                {"role": "user", "content": prompt},
            ],
        )

        response = await self.client.chat.completions.create(
            model=bot_settings.ai_model,
            messages=messages,
            temperature=bot_settings.ai_temperature,
            max_tokens=500,
        )

        content = response.choices[0].message.content
        return self._parse_openai_response(content or "")

    async def _analyze_with_rules(self, symptoms: str) -> List[DoctorRecommendation]:
        """STUB: Fallback анализ на основе правил"""

        print("STUB: Используем rule-based анализ симптомов")

        symptoms_lower = symptoms.lower()
        recommendations = []

        # Неврологические симптомы
        if any(
            keyword in symptoms_lower
            for keyword in ["головная боль", "головокружение", "мигрень", "невралгия"]
        ):
            recommendations.append(
                DoctorRecommendation(
                    doctor_id=3,
                    specialist_name="Невролог",
                    confidence=85,
                    reasoning="Симптомы указывают на неврологические проблемы",
                )
            )

        # Кардиологические симптомы
        if any(
            keyword in symptoms_lower
            for keyword in ["боль в груди", "сердцебиение", "одышка", "аритмия"]
        ):
            recommendations.append(
                DoctorRecommendation(
                    doctor_id=5,
                    specialist_name="Кардиолог",
                    confidence=90,
                    reasoning="Симптомы могут указывать на проблемы с сердцем",
                )
            )

        # Офтальмологические симптомы
        if any(
            keyword in symptoms_lower
            for keyword in ["зрение", "глаза", "слезотечение", "резь в глазах"]
        ):
            recommendations.append(
                DoctorRecommendation(
                    doctor_id=6,
                    specialist_name="Офтальмолог",
                    confidence=95,
                    reasoning="Проблемы со зрением требуют консультации офтальмолога",
                )
            )

        # ЛОР симптомы
        if any(
            keyword in symptoms_lower
            for keyword in ["горло", "насморк", "кашель", "ухо", "слух"]
        ):
            recommendations.append(
                DoctorRecommendation(
                    doctor_id=7,
                    specialist_name="ЛОР",
                    confidence=88,
                    reasoning="Симптомы ЛОР-заболеваний",
                )
            )

        # Дерматологические симптомы
        if any(
            keyword in symptoms_lower
            for keyword in ["сыпь", "зуд", "кожа", "пятна", "дерматит"]
        ):
            recommendations.append(
                DoctorRecommendation(
                    doctor_id=8,
                    specialist_name="Дерматолог",
                    confidence=92,
                    reasoning="Кожные проблемы требуют осмотра дерматолога",
                )
            )

        # Гастроэнтерологические симптомы
        if any(
            keyword in symptoms_lower
            for keyword in ["желудок", "тошнота", "рвота", "диарея", "запор"]
        ):
            recommendations.append(
                DoctorRecommendation(
                    doctor_id=9,
                    specialist_name="Гастроэнтеролог",
                    confidence=87,
                    reasoning="Проблемы с пищеварением",
                )
            )

        # Если ничего специфического не найдено - рекомендуем терапевта
        if not recommendations:
            recommendations.append(
                DoctorRecommendation(
                    doctor_id=1,
                    specialist_name="Терапевт",
                    confidence=70,
                    reasoning="Общие симптомы, начните с консультации терапевта",
                )
            )

        # Всегда добавляем терапевта как альтернативу
        if not any(rec.specialist_name == "Терапевт" for rec in recommendations):
            recommendations.append(
                DoctorRecommendation(
                    doctor_id=2,
                    specialist_name="Терапевт",
                    confidence=60,
                    reasoning="Альтернативный вариант для общей консультации",
                )
            )

        # Сортируем по уверенности
        recommendations.sort(key=lambda x: x.confidence or 0, reverse=True)

        return recommendations[:3]  # Возвращаем топ-3

    def _parse_openai_response(self, response_text: str) -> List[DoctorRecommendation]:
        """STUB: Парсинг ответа от OpenAI"""
        try:
            print(f"STUB: Парсим ответ OpenAI: {response_text}")
            data = json.loads(response_text)
            recommendations = []

            for rec in data.get("recommendations", []):
                specialty = rec.get("specialty", "").lower()
                doctor_ids = self.specialties_map.get(specialty, [1])

                recommendations.append(
                    DoctorRecommendation(
                        doctor_id=doctor_ids[0] if doctor_ids else 1,
                        specialist_name=rec.get("specialty", "Терапевт"),
                        confidence=rec.get("confidence", 70),
                        reasoning=rec.get("reasoning", ""),
                    )
                )

            return recommendations

        except (json.JSONDecodeError, KeyError) as e:
            print(f"STUB: Ошибка парсинга ответа OpenAI: {str(e)}")
            # Переключение на анализ по правилам
            return []
