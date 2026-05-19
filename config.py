"""
config.py — VoidERP UI settings

Reads from environment variables or a .env file in the project root.
Never hardcode credentials — pass them via Docker env or a .env file.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # RabbitMQ connection string
    # Format: amqp://user:password@host:5672/vhost
    AMQP_URL: str = "amqp://guest:guest@localhost:5672/"

    # How often (seconds) Streamlit polls for new agent output
    # Lower = more responsive, higher CPU; 2–5s is sensible for financial dashboards
    REFRESH_INTERVAL_S: float = 3.0

    # Log level
    LOG_LEVEL: str = "INFO"


settings = Settings()