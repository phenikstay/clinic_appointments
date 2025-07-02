# Clinic Appointments

Микросервис для записи пациентов на прием к врачам.

## Быстрый старт

```bash
# Клонируем проект
git clone https://github.com/phenikstay/clinic_appointments.git
cd clinic_appointments

# Копируем пример переменных окружения
cp .env.example .env

# Запускаем сервисы
docker compose up -d --build

# Проверяем работу API
curl http://localhost:8000/health

curl -X POST http://localhost:8000/appointments \
  -H "Content-Type: application/json" \
  -d '{"doctor_id": 1, "patient_name": "Иван Иванов", "start_time": "2025-07-15T10:00:00+03:00"}'
```

## Разработка

```bash
# Установка зависимостей
pip install -r requirements.txt

# Линтинг
make lint

# Тесты  
make test

# Запуск локально
make up

# Остановка
make down
```

## API

- `POST /appointments` - создать запись на прием
- `GET /appointments/{id}` - получить запись по ID
- `GET /health` - проверка здоровья сервиса

## Архитектура

FastAPI + PostgreSQL. Уникальность записей по паре `doctor_id + start_time`.

## Документация

- [Архитектура](docs/architecture.md)
- [База данных](docs/database.md)
- [Процесс записи](docs/activity.md)
- [Бизнес-процессы](docs/business-process.md)
- [Telegram-бот](docs/telegram-bot.md)
- [Проектирование](docs/design-to-implementation.md)

## Бизнес-правила

- Рабочие дни: понедельник-пятница
- Рабочие часы: 9:00-17:30 
- Интервалы: 30 минут
- Время должно быть в будущем 