from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    book_database_url: str = "sqlite:///./book_service.db"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-3-flash-preview"
    recommendation_service_url: str = "http://34.195.107.7"
    recommendation_timeout_seconds: float = 3.0
    circuit_breaker_state_path: str = "./circuit_breaker_state.json"
    circuit_breaker_reset_timeout_seconds: float = 60.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
