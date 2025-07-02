-- =================================================================
-- Инициализация базы данных клиники
-- Часовой пояс устанавливается через переменные PGTZ/TZ
-- в docker-compose.yml, обеспечивая единую конфигурацию.
-- =================================================================

-- Гарантируем, что сессия работает в UTC
SET TIME ZONE 'UTC';

-- Создание таблицы врачей
CREATE TABLE IF NOT EXISTS doctors (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    specialization VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Создание таблицы записей на прием
CREATE TABLE IF NOT EXISTS appointments (
    id SERIAL PRIMARY KEY,
    doctor_id INTEGER NOT NULL REFERENCES doctors(id) ON DELETE CASCADE,
    patient_name VARCHAR(255) NOT NULL,
    start_time TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Создание функции для автоматического обновления поля updated_at
-- CURRENT_TIMESTAMP будет использовать часовой пояс сессии (PGTZ).
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE 'plpgsql';

-- Создание триггеров для автоматического обновления поля updated_at
CREATE TRIGGER update_doctors_updated_at
    BEFORE UPDATE ON doctors
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_appointments_updated_at
    BEFORE UPDATE ON appointments
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Создание уникального ограничения для doctor_id + start_time
-- Это предотвращает двойное бронирование одного врача на одно время.
ALTER TABLE appointments
ADD CONSTRAINT unique_doctor_time
UNIQUE (doctor_id, start_time);

-- Создание индексов для ускорения запросов
CREATE INDEX IF NOT EXISTS idx_doctors_is_active ON doctors(is_active);
CREATE INDEX IF NOT EXISTS idx_appointments_doctor_id ON appointments(doctor_id);
CREATE INDEX IF NOT EXISTS idx_appointments_start_time ON appointments(start_time);
CREATE INDEX IF NOT EXISTS idx_appointments_created_at ON appointments(created_at);

-- Заполнение таблицы врачей базовыми данными
INSERT INTO doctors (id, name, specialization, is_active) VALUES
    (1, 'Доктор Иванов', 'Терапевт', TRUE),
    (2, 'Доктор Петров', 'Кардиолог', TRUE),
    (3, 'Доктор Сидорова', 'Невролог', TRUE),
    (4, 'Доктор Козлов', 'Хирург', TRUE),
    (5, 'Доктор Смирнова', 'Педиатр', TRUE)
ON CONFLICT (id) DO NOTHING;

-- Обновляем последовательность для корректной работы SERIAL
SELECT setval('doctors_id_seq', (SELECT GREATEST(MAX(id), 5) FROM doctors));

-- Вывод информации о созданных таблицах
\echo 'Таблицы "doctors" и "appointments" и связанные объекты успешно созданы.' 