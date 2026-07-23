from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str

    EMAIL_ADDRESS: str
    EMAIL_PASSWORD: str

    GEMINI_API_KEY: str 
    GEMINI_API_KEY_2: str | None = None
    GEMINI_API_KEY_3: str | None = None
    
    SECRET_KEY: str
    ALGORITHM: str

    QDRANT_URL:str
    QDRANT_API_KEY:str
    
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )


settings = Settings()