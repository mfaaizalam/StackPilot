from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str

    EMAIL_ADDRESS: str
    EMAIL_PASSWORD: str

    # One key is enough. The _2/_3 keys are legacy and optional.
    GEMINI_API_KEY: str
    GEMINI_API_KEY_2: str | None = None
    GEMINI_API_KEY_3: str | None = None
    # Change this if your Google account uses a different model name.
    GEMINI_MODEL: str = "gemini-3.6-flash"

    SECRET_KEY: str
    ALGORITHM: str

    QDRANT_URL: str
    QDRANT_API_KEY: str

    # Comma-separated list of deployed frontend URLs, e.g. https://stackpilot.vercel.app
    FRONTEND_ORIGINS: str = ""
    # Set to "1" to use canned LLM answers (tests / offline demo)
    LLM_FAKE: str = "0"

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )


settings = Settings()
