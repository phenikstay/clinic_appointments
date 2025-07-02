# Telegram-бот с ИИ (STUB)

STUB-реализация согласно ТЗ. Полностью рабочий Telegram-бот с демонстрационными данными.

## Структура

```
bot/
├── main.py                    # Точка входа, aiogram Bot + Dispatcher
├── ai/
│   └── analyzer.py           # SymptomAnalyzer: OpenAI + rule-based fallback
├── api/
│   └── clinic_client.py      # ClinicAPIClient: HTTP запросы к API
├── handlers/
│   └── symptoms.py           # Обработчики сообщений, FSM состояния
├── config/
│   └── settings.py           # BotSettings через Pydantic
└── utils/                    # Утилиты
```

## Процесс записи

1. Пользователь присылает текст с симптомами в Telegram
2. `SymptomAnalyzer` анализирует через OpenAI или правила
3. Возвращается список `DoctorRecommendation` с confidence
4. Пользователь выбирает врача из inline клавиатуры
5. `ClinicAPIClient` генерирует слоты (9:00-17:30, пн-пт, 30 мин)
6. Пользователь выбирает время
7. Создается запись через `POST /appointments`
8. Пользователь получает подтверждение с номером записи

## Компоненты

### SymptomAnalyzer
- OpenAI GPT-4.1 для анализа симптомов  
- Rule-based fallback при ошибках ИИ
- Возвращает врачей с confidence и reasoning

```python
@dataclass
class DoctorRecommendation:
    doctor_id: int
    specialist_name: str  
    confidence: Optional[int]
    reasoning: Optional[str]
```

### ClinicAPIClient
- HTTP клиент с aiohttp
- Методы: `create_appointment()`, `get_doctors()`, `get_available_slots()`
- Обработка timezone (UTC в API, Europe/Moscow для пользователя)

### FSM состояния
```python
class AppointmentStates(StatesGroup):
    choosing_doctor = State()
    selecting_time = State()
```

### Обработчики
- `/start` - приветствие с инструкциями
- Текстовые сообщения → анализ симптомов
- Inline кнопки для выбора врача и времени
- Создание реальных записей через API

## Запуск

```bash
# Зависимости
pip install aiogram aiohttp openai pydantic-settings

# Настройки в .env
TELEGRAM_BOT_TOKEN=your_token
OPENAI_API_KEY=your_key
CLINIC_API_URL=http://localhost:8000
AI_MODEL=gpt-4
AI_TEMPERATURE=0.3
TIMEZONE=Europe/Moscow

# Запуск API клиники
make up

# Запуск бота
python -m bot.main
```

## ИИ анализ

### OpenAI промпт
Медицинский ИИ-помощник анализирует симптомы и возвращает JSON:
```json
{
  "recommendations": [
    {
      "specialty": "Невролог",
      "confidence": 85,
      "reasoning": "Головная боль и тошнота"
    }
  ]
}
```

### Rule-based fallback
Keyword matching по симптомам:
- "головная боль" → Невролог (85%)
- "боль в груди" → Кардиолог (90%)  
- "зрение, глаза" → Офтальмолог (95%)

## Функциональность

### Полностью работает
- Подключение к Telegram API через aiogram
- Обработка сообщений и команд
- Inline клавиатуры и callback queries
- FSM для ведения диалога
- HTTP запросы к API клиники
- Создание реальных записей на прием

### STUB ограничения (демо данные)
- Моковые данные врачей (3 штуки)
- Упрощенные слоты
- Генерация слотов в коде, не из календаря врачей
- Базовая обработка ошибок

## Соответствие ТЗ

✅ Текстовый сценарий  
✅ STUB-пакет с точкой входа bot/main.py  
✅ OpenAI для ИИ-анализа симптомов  
✅ Вызов API клиники для создания записей