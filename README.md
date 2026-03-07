# Ticket Sales Service (Касса)

Сервис для продажи билетов в аэропорту. Отвечает за:
- Покупку и возврат билетов
- Управление квотами мест (с учетом овербукинга)
- Интеграцию с другими сервисами через Kafka

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

## 🚀 Быстрый старт

### Предварительные требования
- Docker и Docker Compose
- Make (опционально, для удобства)

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

## 🐳 Docker контейнеры

| Контейнер | Имя | Назначение |
|-----------|-----|------------|
| Tickets Service | `tickets_service` | Основной сервис |
| PostgreSQL | `tickets_postgres` | База данных |
| Kafka | `tickets_kafka` | Брокер сообщений |
| Zookeeper | `tickets_zookeeper` | Координация Kafka |

## 🧪 Тестирование

```bash
# Перейти в директорию тестов
cd tests

# Создать виртуальное окружение
python3 -m venv venv
source venv/bin/activate

# Установить зависимости
pip install -r requirements-test.txt

# Запустить тесты
./run_tests.sh
```

## 📊 Мониторинг

### Проверка здоровья
```bash
curl http://localhost:8006/api/tickets/health
```

### Логи
```bash
# Все сервисы
docker compose logs -f

# Только tickets
docker compose logs -f tickets

# Только Kafka
docker compose logs -f kafka
```

### Доступ к БД
```bash
# Подключиться к PostgreSQL
docker exec -it tickets_postgres psql -U ticket_user -d ticket_db
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

## 👥 Автор

Морозова Мария Дмитриевна, МО12


