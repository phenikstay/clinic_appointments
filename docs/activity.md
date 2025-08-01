# Процесс записи на прием

## Основной сценарий

**POST /appointments** - создание записи на прием

### Шаги обработки

1. **Прием запроса**
   - Получение JSON с `doctor_id`, `patient_name`, `start_time`

2. **Валидация Pydantic**
   - `doctor_id ≥ 1`
   - `patient_name` не пустое (≤ 255 символов)
   - `start_time` с обязательным timezone
   - Время в будущем
   - Рабочие часы: 9:00-17:30
   - Рабочие дни: понедельник-пятница  
   - Интервалы: кратно 30 минутам

3. **Проверка врача**
   - Врач существует в таблице doctors
   - Врач активен (is_active = TRUE)

4. **Проверка доступности**
   - Уникальность пары (doctor_id, start_time)
   - Нет конфликтующих записей

5. **Создание записи**
   - INSERT в таблицу appointments
   - Возврат данных записи

## Возможные ошибки

### HTTP 422 - Ошибки валидации
```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "start_time"],
      "msg": "Время записи должно быть в будущем"
    }
  ]
}
```

**Причины:**
- Прошедшее время
- Выходной день (суббота/воскресенье)
- Нерабочие часы (до 9:00 или после 17:30)
- Неправильный интервал (не кратно 30 минутам)
- Отсутствие timezone
- Пустое имя пациента

### HTTP 400 - Бизнес-ошибки
```json
{"detail": "Врач не найден или неактивен"}
{"detail": "Врач уже занят в это время"}
```

### HTTP 500 - Ошибки сервера
```json
{"detail": "Произошла ошибка базы данных"}
```

## Успешный ответ (HTTP 201)

```json
{
  "id": 15,
  "doctor_id": 1,
  "patient_name": "Иван Иванов",
  "start_time": "2025-07-01T10:00:00+03:00",
  "created_at": "2025-06-28T10:37:23.854112",
  "updated_at": "2025-06-28T10:37:23.854119"
}
```

## Примеры запросов

### Успешная запись
```bash
curl -X POST http://localhost:8000/appointments \
  -H "Content-Type: application/json" \
  -d '{
    "doctor_id": 1,
    "patient_name": "Иван Иванов",
    "start_time": "2025-07-01T10:00:00+03:00"
  }'
```

### Ошибка времени
```bash
# Запрос на прошедшее время
curl -X POST http://localhost:8000/appointments \
  -d '{"doctor_id": 1, "patient_name": "Пациент", 
       "start_time": "2024-01-01T10:00:00+03:00"}'
# → HTTP 422: "Время записи должно быть в будущем"
```

### Конфликт времени
```bash
# Повторный запрос на то же время
curl -X POST http://localhost:8000/appointments \
  -d '{"doctor_id": 1, "patient_name": "Другой пациент",
       "start_time": "2025-07-01T10:00:00+03:00"}'
# → HTTP 400: "Врач уже занят в это время"
```
