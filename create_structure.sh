#!/bin/bash

# скрипт, чтобы создавать папочки и файлики проекта 

# Цвета для вывода
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}Создание структуры проекта Ticket Sales${NC}"
echo -e "${BLUE}========================================${NC}"

# Проверяем, что мы в правильной директории
if [ "$(basename $(pwd))" != "tickets" ]; then
    echo -e "${RED}Ошибка: Запусти скрипт из директории tickets${NC}"
    echo "Текущая директория: $(pwd)"
    exit 1
fi

echo -e "${GREEN}Создаю структуру директорий...${NC}"

# Создаем директории
mkdir -p app/models
mkdir -p app/services
mkdir -p app/api/v1/endpoints
mkdir -p app/consumers
mkdir -p app/utils
mkdir -p scripts
mkdir -p migrations/versions

echo -e "${GREEN}Создаю пустые файлы...${NC}"

# Корневые файлы
touch requirements.txt
touch Dockerfile
touch docker-compose.yml
touch .env.example
touch .env

# __init__.py файлы
touch app/__init__.py
touch app/models/__init__.py
touch app/services/__init__.py
touch app/api/__init__.py
touch app/api/v1/__init__.py
touch app/api/v1/endpoints/__init__.py
touch app/consumers/__init__.py
touch app/utils/__init__.py

# Файлы приложения
touch app/main.py
touch app/config.py
touch app/database.py
touch app/kafka.py

# Модели
touch app/models/ticket.py
touch app/models/flight_sales.py
touch app/models/processed_events.py
touch app/models/outbox.py
touch app/models/kafka_models.py

# Сервисы
touch app/services/ticket_service.py
touch app/services/flight_sales_service.py

# API эндпоинты
touch app/api/v1/endpoints/tickets.py
touch app/api/v1/endpoints/sales.py
touch app/api/v1/errors.py

# Консьюмеры
touch app/consumers/base.py
touch app/consumers/flight_consumer.py
touch app/consumers/passenger_consumer.py
touch app/consumers/boarding_consumer.py

# Утилиты
touch app/utils/idempotency.py

# Скрипты
touch scripts/wait_for_db.py

echo -e "${GREEN}Готово! Создана структура проекта:${NC}"
tree -L 4 --filelimit 10

echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}Теперь можешь наполнять файлы кодом${NC}"
echo -e "${BLUE}========================================${NC}"