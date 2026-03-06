#!/bin/bash

# Цвета для вывода
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}Создание структуры тестов для Ticket Sales Service${NC}"
echo -e "${BLUE}========================================${NC}"

# Проверяем, что мы в директории tickets
if [ "$(basename $(pwd))" != "tickets" ]; then
    echo -e "${RED}Ошибка: Запусти скрипт из директории tickets${NC}"
    echo "Текущая директория: $(pwd)"
    exit 1
fi

# Создаем директорию tests и поддиректории
echo -e "${YELLOW}Создаю структуру директорий...${NC}"
mkdir -p tests
mkdir -p tests/test-reports
mkdir -p tests/__pycache__ 2>/dev/null

echo -e "${YELLOW}Создаю пустые файлы...${NC}"

# Создаем __init__.py
touch tests/__init__.py

# Создаем файлы тестов
touch tests/conftest.py
touch tests/test_health.py
touch tests/test_rest_api.py
touch tests/test_business_logic.py
touch tests/test_failure_handling.py
touch tests/test_idempotency.py
touch tests/test_overbooking.py
touch tests/test_kafka_consumers.py
touch tests/test_kafka_producers.py
touch tests/utils.py
touch tests/requirements-test.txt

# Создаем скрипт для запуска тестов
touch tests/run_tests.sh

# Делаем run_tests.sh исполняемым
chmod +x tests/run_tests.sh

echo -e "${GREEN}✅ Структура тестов успешно создана!${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "${YELLOW}Создана структура:${NC}"
echo "  ├── tests/"
echo "  │   ├── __init__.py"
echo "  │   ├── conftest.py"
echo "  │   ├── test_health.py"
echo "  │   ├── test_rest_api.py"
echo "  │   ├── test_business_logic.py"
echo "  │   ├── test_failure_handling.py"
echo "  │   ├── test_idempotency.py"
echo "  │   ├── test_overbooking.py"
echo "  │   ├── test_kafka_consumers.py"
echo "  │   ├── test_kafka_producers.py"
echo "  │   ├── utils.py"
echo "  │   ├── requirements-test.txt"
echo "  │   ├── run_tests.sh"
echo "  │   └── test-reports/"
echo "  └── (остальные файлы будут созданы позже)"

echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}Готово! Теперь можешь наполнять файлы содержимым.${NC}"
echo -e "${BLUE}========================================${NC}"