from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # App settings
    app_name: str = "Ticket Sales Service"
    environment: str = "development"
    debug: bool = False
    
    # Database settings
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "ticket_user"
    postgres_password: str = "ticket_pass"
    postgres_db: str = "ticket_db"
    
    @property
    def database_url(self) -> str:
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
    
    # Kafka settings
    kafka_bootstrap_servers: str = "kafka:9092" # В Docker используем имя сервиса, не localhost
    kafka_group_id: str = "ticket-sales-consumer"
    
    # Kafka Topics (из документации)
    kafka_topic_flights_events: str = "flights.events"
    kafka_topic_passengers_events: str = "passengers.events"
    kafka_topic_board_events: str = "board.events"
    kafka_topic_tickets_events: str = "tickets.events"
    
    # Business Logic (overbook_limit = planned_capacity * OVERBOOK_FACTOR)
    overbook_factor: float = 0.3
    
    # Connection pools
    db_pool_size: int = 20
    db_max_overflow: int = 10
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()