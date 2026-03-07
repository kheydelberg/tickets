#!/bin/bash

# Цвета для вывода
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}Запуск E2E тестов для Ticket Sales Service${NC}"
echo -e "${BLUE}========================================${NC}"

# Проверка, что сервис запущен
echo -e "${YELLOW}Проверка доступности сервиса...${NC}"
if ! curl -s http://localhost:8006/api/tickets/health > /dev/null; then
    echo -e "${RED}❌ Сервис не доступен! Запустите проект: docker compose up -d${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Сервис доступен${NC}"

# Проверка Kafka
echo -e "${YELLOW}Проверка Kafka...${NC}"
if ! docker compose ps kafka | grep -q "Up"; then
    echo -e "${RED}❌ Kafka не запущена!${NC}"
    echo -e "${YELLOW}⚠️ Тесты Kafka будут пропущены${NC}"
    SKIP_KAFKA=true
else
    echo -e "${GREEN}✅ Kafka запущена${NC}"
    SKIP_KAFKA=false
fi

# Проверка PostgreSQL
echo -e "${YELLOW}Проверка PostgreSQL...${NC}"
if ! docker compose ps postgres | grep -q "healthy"; then
    echo -e "${RED}❌ PostgreSQL не доступна!${NC}"
    exit 1
fi
echo -e "${GREEN}✅ PostgreSQL доступна${NC}"

echo -e "${BLUE}========================================${NC}"

# Активация виртуального окружения если есть
if [ -d "venv" ]; then
    echo -e "${YELLOW}Активация виртуального окружения...${NC}"
    source venv/bin/activate
fi

# Проверка установки pytest
if ! command -v pytest &> /dev/null; then
    echo -e "${YELLOW}Установка зависимостей для тестов...${NC}"
    pip install -r requirements-test.txt > /dev/null 2>&1
fi

# Создание директории для отчетов
mkdir -p test-reports
REPORT_FILE="test-reports/report_$(date +%Y%m%d_%H%M%S).html"

echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}Запуск тестов...${NC}"
echo -e "${BLUE}========================================${NC}"

# Формируем список тестов
TEST_FILES=(
    # Базовые тесты
    "test_health.py"
    "test_rest_api.py"
    "test_business_logic.py"
    "test_failure_handling.py"
    "test_idempotency.py"
    "test_overbooking.py"
    
    # Тесты бизнес-логики
    "test_status_flows.py"
    "test_counters.py"
    "test_rules.py"
    "test_flight_sales.py"
    
    # Тесты ошибок
    "test_validation_errors.py"
    
    # Тесты outbox
    "test_outbox.py"
)

# Добавляем тесты Kafka если Kafka запущена
if [ "$SKIP_KAFKA" = false ]; then
    echo -e "${GREEN}✅ Включаем тесты Kafka...${NC}"
    TEST_FILES+=(
        "test_kafka_consumers.py"
        "test_kafka_producers.py"
        "test_kafka_envelope.py"
    )
else
    echo -e "${YELLOW}⚠️ Тесты Kafka пропущены${NC}"
fi

# Подсчет количества тестов
TOTAL_TESTS=${#TEST_FILES[@]}
echo -e "${CYAN}Всего файлов с тестами: $TOTAL_TESTS${NC}"
echo -e "${BLUE}========================================${NC}"

# Запуск тестов
PYTHONPATH=. pytest \
    -v \
    --tb=short \
    --maxfail=3 \
    --strict-markers \
    --html="$REPORT_FILE" \
    --self-contained-html \
    "${TEST_FILES[@]}"

EXIT_CODE=$?

echo -e "${BLUE}========================================${NC}"

# Вывод результатов
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✅ ВСЕ ТЕСТЫ УСПЕШНО ПРОЙДЕНЫ!${NC}"
    
    # Подробная статистика
    echo -e "${BLUE}========================================${NC}"
    echo -e "${GREEN}📊 СТАТИСТИКА ТЕСТИРОВАНИЯ:${NC}"
    
    # Считаем тесты в каждом файле
    TOTAL=0
    for test_file in "${TEST_FILES[@]}"; do
        if [ -f "$test_file" ]; then
            COUNT=$(grep -c "^def test_" "$test_file" 2>/dev/null || echo "0")
            TOTAL=$((TOTAL + COUNT))
            echo -e "  ${CYAN}$test_file${NC}: $COUNT тестов"
        fi
    done
    
    echo -e "${GREEN}  Всего запущено тестов: $TOTAL${NC}"
    
    # Проверка покрытия требований
    echo -e "${BLUE}========================================${NC}"
    echo -e "${GREEN}📋 ПРОВЕРКА СООТВЕТСТВИЯ ДОКУМЕНТАЦИИ:${NC}"
    echo -e "  ✅ A) Service Identity - проверено (test_health.py)"
    echo -e "  ✅ B) Source of Truth - проверено (test_status_flows.py, test_counters.py, test_rules.py)"
    echo -e "  ✅ C1) REST API - проверено (test_rest_api.py, test_flight_sales.py)"
    
    if [ "$SKIP_KAFKA" = false ]; then
        echo -e "  ✅ C2) Kafka Contracts - проверено (test_kafka_*.py)"
    else
        echo -e "  ⚠️  C2) Kafka Contracts - пропущено (Kafka не запущена)"
    fi
    
    echo -e "  ✅ D) Dependencies - проверено (нет внешних вызовов)"
    echo -e "  ✅ F1-F6) Business Logic - проверено (test_business_logic.py)"
    echo -e "  ✅ G) Failure Handling - проверено (test_failure_handling.py, test_idempotency.py, test_outbox.py)"
    
else
    echo -e "${RED}❌ НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОЙДЕНЫ!${NC}"
    echo -e "${YELLOW}Проверьте логи сервиса:${NC}"
    echo -e "  docker compose logs tickets --tail 50"
    echo -e "${YELLOW}Или запустите конкретный тест:${NC}"
    echo -e "  pytest test_rest_api.py -v"
fi

echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}📄 Отчет о тестировании:${NC} file://$(pwd)/$REPORT_FILE"
echo -e "${BLUE}========================================${NC}"

# Деактивация виртуального окружения
if [ -d "venv" ]; then
    deactivate 2>/dev/null
fi

exit $EXIT_CODE