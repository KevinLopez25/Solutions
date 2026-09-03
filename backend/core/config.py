from pathlib import Path
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# Ruta ABSOLUTA del .env del backend: aunque uvicorn se ejecute desde otra
# carpeta, siempre se carga este archivo.
_BACKEND_DIR = Path(__file__).resolve().parent.parent
dotenv_path = _BACKEND_DIR / '.env'
load_dotenv(dotenv_path=dotenv_path, override=True)


class Settings(BaseSettings):
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_NAME: str = "solutions_db"
    DB_USER: str = "root"
    DB_PASSWORD: str = "sena"

    TEMPLATES_DIR: str = "templates"
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://localhost:3000"
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "groq/compound-mini"
    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"

    model_config = SettingsConfigDict(
        env_file=str(dotenv_path), env_file_encoding="utf-8"
    )

    @property
    def groq_configurada(self) -> bool:
        return bool(self.GROQ_API_KEY and self.GROQ_API_KEY.strip())

    @property
    def database_url(self) -> str:
        return (
            f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"
        )

    @property
    def templates_path(self) -> Path:
        return Path(__file__).resolve().parent.parent / self.TEMPLATES_DIR

    @property
    def origins(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",")]


settings = Settings()
