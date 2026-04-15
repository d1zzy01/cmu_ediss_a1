from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    kafka_brokers: str = "98.88.99.206:9092,34.195.107.7:9092,54.221.160.63:9092"
    kafka_topic: str = "davidzhu.customer.evt"
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    sender_email: str = ""
    andrew_id: str = "davidzhu"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
