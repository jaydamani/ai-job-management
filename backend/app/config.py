from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    AI_MODEL: str = "gemini/gemini-3.5-flash"

    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    S3_BUCKET: str = "gappeo"
    S3_ENDPOINT_URL: str = ""
    MINIO_PUBLIC_URL: str = ""

    CORS_ORIGINS: str = "http://localhost:5173"
    # Set to true in production (HTTPS). Enables secure + SameSite=None cookies
    # required for cross-origin deploys (e.g. Render static site + web service).
    COOKIE_SECURE: bool = False

    @property
    def cors_origins_list(self) -> List[str]:
        if not self.CORS_ORIGINS:
            return []
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
