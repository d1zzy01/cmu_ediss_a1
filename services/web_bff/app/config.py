from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    book_service_url: str = "http://book-service:8001"
    customer_service_url: str = "http://customer-service:8002"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
