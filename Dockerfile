FROM python:3.12-slim

# Создание пользователя приложения
RUN groupadd -r app && useradd -r -g app app

# Установка рабочей директории
WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Копирование и установка Python зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование кода приложения
COPY . .

# Изменение владельца на пользователя app
RUN chown -R app:app /app

# Переключение на пользователя app
USER app

# Открытие порта
EXPOSE 8000

# Проверка здоровья
HEALTHCHECK CMD curl -f http://localhost:8000/health || exit 1

# Запуск приложения
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"] 