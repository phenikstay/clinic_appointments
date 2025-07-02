.PHONY: help lint test up down build clean install type-check format migrate
.DEFAULT_GOAL := help

help: ## Показать это справочное сообщение
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Установить зависимости
	pip install -r requirements.txt

lint: ## Запустить инструменты линтинга
	black --check app tests
	isort --check-only app tests
	flake8 app tests
	mypy app

format: ## Форматировать код
	black app tests
	isort app tests

type-check: ## Запустить проверку типов
	mypy app

test: ## Запустить тесты
	pytest tests/ -v --tb=short

test-cov: ## Запустить тесты с покрытием
	pytest tests/ -v --tb=short --cov=app --cov-report=html --cov-report=term

up: ## Запустить сервисы с docker-compose
	docker compose up -d --build

down: ## Остановить сервисы
	docker compose down

logs: ## Показать логи
	docker compose logs -f

build: ## Собрать Docker образ
	docker build -t clinic-appointments .

clean: ## Очистить контейнеры и тома
	docker compose down -v
	docker system prune -f

shell: ## Открыть shell в API контейнере
	docker compose exec api bash

db-shell: ## Открыть PostgreSQL shell
	docker compose exec db psql -U clinic_user -d clinic_db

restart: ## Перезапустить сервисы
	docker compose restart

status: ## Показать статус контейнеров
	docker compose ps

# CI/CD цели
ci-lint: install ## CI: Запустить линтинг
	black --check app tests
	isort --check-only app tests
	flake8 app tests
	mypy app

ci-test: install ## CI: Запустить тесты
	pytest tests/ -v

ci-all: ci-lint ci-test ## CI: Запустить все проверки

migrate: ## Применить миграции (init.sql) к базе в контейнере
	docker compose exec db psql -U $$POSTGRES_USER -d $$POSTGRES_DB -f /docker-entrypoint-initdb.d/init.sql
