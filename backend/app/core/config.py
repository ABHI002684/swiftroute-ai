from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "SwiftRoute AI"
    API_V1_PREFIX: str = "/api/v1"
    DATABASE_URL: str = "sqlite:///./swiftroute.db"
    DEBUG: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()