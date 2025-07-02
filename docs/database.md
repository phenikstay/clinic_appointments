# Схема базы данных

## Таблицы

### doctors
Справочник врачей (добавлена сверх ТЗ для валидации)

```sql
CREATE TABLE doctors (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    specialization VARCHAR(255) NOT NULL, 
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
```

### appointments  
Записи пациентов на прием

```sql
CREATE TABLE appointments (
    id SERIAL PRIMARY KEY,
    doctor_id INTEGER NOT NULL REFERENCES doctors(id) ON DELETE CASCADE,
    patient_name VARCHAR(255) NOT NULL,
    start_time TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
```

## Ограничения

### Уникальность
```sql
ALTER TABLE appointments 
ADD CONSTRAINT unique_doctor_time 
UNIQUE (doctor_id, start_time);
```
Один врач не может принимать двух пациентов одновременно.

### Foreign Key
```sql
doctor_id REFERENCES doctors(id) ON DELETE CASCADE
```
Запись привязана к существующему врачу.

## Индексы

```sql
CREATE INDEX idx_doctors_is_active ON doctors(is_active);
CREATE INDEX idx_appointments_doctor_id ON appointments(doctor_id);
CREATE INDEX idx_appointments_start_time ON appointments(start_time);
CREATE INDEX idx_appointments_created_at ON appointments(created_at);
```

## Триггеры

Автоматическое обновление `updated_at`:

```sql
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE 'plpgsql';

CREATE TRIGGER update_doctors_updated_at 
    BEFORE UPDATE ON doctors 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_appointments_updated_at 
    BEFORE UPDATE ON appointments 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();
```

## Тестовые данные

```sql
INSERT INTO doctors (id, name, specialization, is_active) VALUES
    (1, 'Доктор Иванов', 'Терапевт', TRUE),
    (2, 'Доктор Петров', 'Кардиолог', TRUE),
    (3, 'Доктор Сидорова', 'Невролог', TRUE),
    (4, 'Доктор Козлов', 'Хирург', TRUE),
    (5, 'Доктор Смирнова', 'Педиатр', TRUE);
```

## Валидация на уровне приложения

Дополнительные проверки в Pydantic схемах (`app/schemas/appointment.py`):
- Рабочие часы: 9:00-17:30 по времени клиники
- Рабочие дни: понедельник-пятница (0-4 в weekday())
- Интервалы: кратно 30 минутам (минуты 0 или 30)
- Время в будущем (с учетом timezone пользователя)
- Обязательный timezone для избежания путаницы
- Врач должен быть активным (is_active = TRUE)

## Часовые пояса

- Все данные хранятся в UTC (`TIMESTAMPTZ`)
- Валидация происходит в timezone клиники (Europe/Moscow)  
- Конвертация на уровне приложения

## Отличия от ТЗ

ТЗ требовало только модель `Appointment` с `doctor_id` как число. Таблица `doctors` добавлена для:
- Валидации существования врача
- Проверки активности врача  
- Возможности расширения функциональности 