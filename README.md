# Tickets (Касса)

Сервис для продажи билетов в аэропорту. Отвечает за:
- Покупку и возврат билетов
- Управление квотами мест (с учетом овербукинга)
- Интеграцию с другими сервисами через Kafka

## 🚀 Быстрый старт

### Предварительные требования
- Docker и Docker Compose

### Запуск сервиса

```bash
# Клонировать репозиторий
git clone https://github.com/kheydelberg/tickets
cd tickets

# Запустить все контейнеры
docker compose up -d

# Проверить статус
docker compose ps

# Посмотреть логи
docker compose logs -f tickets
```

### Остановка сервиса

```bash
docker compose down
```

### Полная перезагрузка (с пересборкой)

```bash
docker compose down
docker compose up --build -d
```

## 📋 Соответствие документации

### A) Service Identity
- **serviceName (Docker DNS):** `tickets`
- **internalPort:** 8000
- **hostPort:** 8006:8000 (порт изменен, т.к. 8005 занят)
- **nginxPrefix:** `/api/tickets`

### B) Source of Truth
- Билеты (`ticket.status`): active/returned/bumped/fake
- Продажи: счетчики `sold_total`/`active_total`, флаг `sales_open`
- Правила продаж/возвратов по статусу рейса

## 🔧 Конфигурация

### Переменные окружения (.env)

```env
# PostgreSQL
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_USER=ticket_user
POSTGRES_PASSWORD=ticket_pass
POSTGRES_DB=ticket_db

# Kafka
KAFKA_BOOTSTRAP_SERVERS=kafka:9092

# App
ENVIRONMENT=production
DEBUG=false

# Business Logic
OVERBOOK_FACTOR=0.3
```

## 🐳 Docker контейнеры

| Контейнер | Имя | Порты | Назначение |
|-----------|-----|-------|------------|
| Tickets Service | `tickets_service` | `8006:8000` | Основной сервис |
| PostgreSQL | `tickets_postgres` | `5432:5432` | База данных |
| Kafka | `tickets_kafka` | `9092:9092` (внутр), `9093:9093` (внеш) | Брокер сообщений |
| Zookeeper | `tickets_zookeeper` | `2181:2181` | Координация Kafka |
| Kafka Init | `tickets_kafka_init` | - | Инициализация топиков |

### Сеть
Все контейнеры работают в общей сети `airport_network` для взаимодействия с другими микросервисами.

## 🔧 Конфигурация Kafka

Kafka настроена с двумя слушателями для обеспечения доступа как из контейнеров, так и с хоста:

- **Внутренний (INTERNAL):** `kafka:9092` - для сервисов внутри Docker сети
- **Внешний (EXTERNAL):** `localhost:9093` - для тестов и отладки с хоста

### Топики Kafka
Автоматически создаются при старте через `kafka-init` контейнер:
- `flights.events` - события рейсов
- `passengers.events` - события пассажиров
- `board.events` - события посадки
- `tickets.events` - события билетов (производные)

## 📡 API Endpoints

| Метод | Endpoint | Описание |
|-------|----------|----------|
| GET | `/api/tickets/health` | Проверка здоровья сервиса |
| GET | `/api/tickets/v1/tickets` | Список билетов (с фильтрацией) |
| GET | `/api/tickets/v1/tickets/{ticketId}` | Получить билет по ID |
| GET | `/api/tickets/v1/tickets/passenger/{passengerId}` | Билеты пассажира |
| POST | `/api/tickets/v1/tickets/buy` | Купить билет |
| POST | `/api/tickets/v1/tickets/{ticketId}/refund` | Вернуть билет |
| GET | `/api/tickets/v1/flight-sales/{flightId}` | Статистика продаж по рейсу |

### Формат ошибок

```json
{
  "code": "error_code",
  "message": "Описание ошибки"
}
```

Возможные коды ошибок:
- `validation_error` - ошибка валидации
- `not_found` - ресурс не найден
- `sales_closed` - продажи закрыты
- `sold_out` - лимит продаж достигнут
- `already_has_active_ticket` - уже есть активный билет
- `refund_closed` - возврат невозможен после закрытия продаж
- `internal_error` - внутренняя ошибка сервера

## 🗄️ Kafka Contracts

### Потребляемые топики (Consumes)
- `flights.events` - flight.created, flight.status.changed
- `passengers.events` - passenger.created
- `board.events` - board.boarding.result

### Производимые топики (Produces)
- `tickets.events` - ticket.bought, ticket.refunded, ticket.bumped

### Формат сообщений (Envelope)

```json
{
  "eventId": "uuid",
  "type": "string",
  "ts": "ISO-8601",
  "producer": "tickets",
  "correlationId": "uuid|null",
  "entity": {"kind": "ticket", "id": "uuid"},
  "payload": {}
}
```

## 📁 Структура проекта

```
├── app/                    # Основной код приложения
│   ├── api/                # REST API endpoints
│   │   └── v1/
│   │       ├── endpoints/   # tickets.py, sales.py
│   │       └── errors.py    # Обработка ошибок
│   ├── consumers/          # Kafka consumers
│   │   ├── flight_consumer.py
│   │   ├── passenger_consumer.py
│   │   └── boarding_consumer.py
│   ├── models/             # SQLAlchemy модели
│   │   ├── ticket.py
│   │   ├── flight_sales.py
│   │   ├── outbox.py
│   │   └── idempotency.py
│   ├── services/           # Бизнес-логика
│   │   ├── ticket_service.py
│   │   └── flight_sales_service.py
│   └── utils/              # Утилиты
│       ├── idempotency.py
│       └── json_encoder.py
├── tests/                  # Тесты (55 тестов)
│   ├── test_rest_api.py    # Тесты REST API
│   ├── test_kafka_*.py     # Тесты Kafka интеграции
│   ├── test_business_logic.py
│   └── test_reports/       # Отчеты о тестировании
├── scripts/                 # Вспомогательные скрипты
│   └── wait_for_db.py
├── docker-compose.yml       # Docker Compose конфигурация
├── Dockerfile              # Docker образ
└── requirements.txt        # Зависимости Python
```

## 🏗️ Архитектура

### Паттерны проектирования
- **Outbox Pattern** - гарантированная доставка событий в Kafka
- **Idempotency Keys** - защита от дублирования операций
- **Database per Service** - изоляция данных
- **Event-Driven Architecture** - асинхронное взаимодействие

### Основные компоненты
1. **REST API** - синхронные операции (покупка/возврат)
2. **Kafka Consumers** - обработка событий от других сервисов
3. **Business Logic Layer** - правила продаж и овербукинга
4. **Data Layer** - PostgreSQL с блокировками строк

## 🧪 Тестирование

### Запуск тестов

```bash
# Перейти в директорию тестов
cd tests

# Создать виртуальное окружение
python3 -m venv venv
source venv/bin/activate

# Установить зависимости
pip install -r requirements-test.txt

# Запустить все тесты
./run_tests.sh
```

### Запуск отдельных тестов

```bash
# Запустить конкретный тест
pytest tests/test_rest_api.py -v -k "test_buy_ticket"

# Запустить тесты с отчетом
pytest --html=report.html

# Запустить Kafka тесты
pytest tests/test_kafka_consumers.py tests/test_kafka_producers.py -v
```

### 📊 Тестовое покрытие

Проект содержит **55 интеграционных тестов**, покрывающих:

| Категория | Количество тестов |
|-----------|-------------------|
| REST API | 6 |
| Бизнес-логика (F1-F6) | 5 |
| Kafka интеграция | 7 |
| Обработка ошибок | 11 |
| Статусы билетов | 4 |
| Идемпотентность | 1 |
| Outbox паттерн | 4 |
| Валидация | 7 |
| **Всего** | **55** |

✅ **Все тесты успешно проходят!**

## 📊 Мониторинг и отладка

### Проверка здоровья
```bash
curl http://localhost:8006/api/tickets/health
```

### Статистика продаж по рейсу
```bash
curl http://localhost:8006/api/tickets/v1/flight-sales/FL123
```

### Логи
```bash
# Все сервисы
docker compose logs -f

# Только tickets
docker compose logs -f tickets

# Только Kafka
docker compose logs -f kafka

# Логи с фильтром
docker compose logs tickets_service | grep ERROR
```

### Доступ к БД
```bash
# Подключиться к PostgreSQL
docker exec -it tickets_postgres psql -U ticket_user -d ticket_db

# Основные запросы
SELECT * FROM tickets WHERE flight_id = 'FL123';
SELECT * FROM flight_sales;
SELECT * FROM outbox_messages WHERE processed = false;
```

## 🔄 Интеграция с другими сервисами

Для связи с другими модулями используйте:
- **Docker DNS:** `tickets:8000`
- **API Gateway:** `http://localhost:8080/api/tickets`
- **Kafka:** через топики `*.events`

## 📝 Примечания

- Порт изменен с 8005 на 8006 (т.к. 8005 может быть занят)
- Все контейнеры работают в сети `airport_network`
- Для production используйте `ENVIRONMENT=production`
- Kafka доступна для тестов с хоста на порту `9093`

## 👥 Автор

Морозова Мария Дмитриевна, МО12
```
