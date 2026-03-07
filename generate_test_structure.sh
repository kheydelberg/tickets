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


echo -e "${YELLOW}Создаю пустые файлы...${NC}"

# Создаем __init__.py
touch tests/__init__.py

# === БАЗОВЫЕ ФАЙЛЫ ===
touch tests/conftest.py
touch tests/utils.py
touch tests/requirements-test.txt

# === ТЕСТЫ REST API ===
touch tests/test_health.py
touch tests/test_rest_api.py

# === ТЕСТЫ БИЗНЕС-ЛОГИКИ ===
touch tests/test_business_logic.py
touch tests/test_failure_handling.py
touch tests/test_idempotency.py
touch tests/test_overbooking.py

# === НОВЫЕ ТЕСТЫ (ПОЛНОЕ ПОКРЫТИЕ) ===
touch tests/test_kafka_consumers.py      # Тесты consumers (F1, F2, F3, F6)
touch tests/test_kafka_producers.py      # Тесты producers (ticket.bought/refunded/bumped)
touch tests/test_kafka_envelope.py       # Проверка формата Envelope
touch tests/test_status_flows.py         # Проверка всех статусов (active/returned/bumped/fake)
touch tests/test_counters.py             # Проверка счетчиков sold_total/active_total/sales_open
touch tests/test_rules.py                # Проверка правил продаж/возвратов
touch tests/test_validation_errors.py    # Проверка всех error responses из OpenAPI
touch tests/test_flight_sales.py         # Тесты для flight-sales endpoints
touch tests/test_filtering.py            # Тесты фильтрации по параметрам
touch tests/test_pagination.py           # Тесты пагинации (если будет)
touch tests/test_outbox.py               # Тесты outbox pattern

# === СКРИПТ ЗАПУСКА ===
touch tests/run_tests.sh

# Делаем run_tests.sh исполняемым
chmod +x tests/run_tests.sh

echo -e "${GREEN}✅ Структура тестов успешно создана!${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "${YELLOW}Создана структура (24 файла):${NC}"
echo "  ├── tests/"
echo "  │   ├── __init__.py"
echo "  │   ├── conftest.py"
echo "  │   ├── utils.py"
echo "  │   ├── requirements-test.txt"
echo "  │   ├── run_tests.sh"
echo "  │   ├── test-reports/"
echo "  │   │"
echo "  │   ├── БАЗОВЫЕ ТЕСТЫ:"
echo "  │   │   ├── test_health.py"
echo "  │   │   ├── test_rest_api.py"
echo "  │   │   ├── test_business_logic.py"
echo "  │   │   ├── test_failure_handling.py"
echo "  │   │   ├── test_idempotency.py"
echo "  │   │   └── test_overbooking.py"
echo "  │   │"
echo "  │   ├── KAFKA ТЕСТЫ:"
echo "  │   │   ├── test_kafka_consumers.py"
echo "  │   │   ├── test_kafka_producers.py"
echo "  │   │   └── test_kafka_envelope.py"
echo "  │   │"
echo "  │   ├── БИЗНЕС-ЛОГИКА:"
echo "  │   │   ├── test_status_flows.py"
echo "  │   │   ├── test_counters.py"
echo "  │   │   ├── test_rules.py"
echo "  │   │   └── test_flight_sales.py"
echo "  │   │"
echo "  │   ├── ДОПОЛНИТЕЛЬНО:"
echo "  │   │   ├── test_validation_errors.py"
echo "  │   │   ├── test_filtering.py"
echo "  │   │   ├── test_pagination.py"
echo "  │   │   └── test_outbox.py"
echo "  │   │"
echo "  └───── (всего 24 файла)"

echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}Созданы все необходимые файлы для тестирования!${NC}"
echo -e "${YELLOW}Теперь можешь наполнять файлы содержимым из предыдущих сообщений.${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "Список всех созданных файлов:"
ls -la tests/ | grep -v total | awk '{print "  📄 " $9}'
echo -e "${BLUE}========================================${NC}"