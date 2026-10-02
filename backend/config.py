from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DB_HOST: str
    DB_PORT: int = 3306
    DB_NAME: str
    DB_USER: str
    DB_PASSWORD: str = ""
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_HOURS: int = 8
    ENVIRONMENT: str = "development"
    # Safe-by-default: un env var olvidado = prod bloqueado (no prod abierto).
    # El dev local pone DEBUG=True explícito en su .env (eso sobreescribe este default).
    DEBUG: bool = False
    # Orígenes CORS permitidos en producción (DEBUG=False), separados por coma.
    # Ej: "https://inventario.midominio.com,https://otro.midominio.com"
    ALLOWED_ORIGINS: str = ""
    BASE_URL: str = "http://localhost:8000"
    APP_BASE_URL: str = "http://localhost:8000"

    # Email
    MAIL_USERNAME:   str  = ""
    MAIL_PASSWORD:   str  = ""
    MAIL_FROM:       str  = ""
    MAIL_FROM_NAME:  str  = "Inventario TI"
    MAIL_SERVER:     str  = "smtp.gmail.com"
    MAIL_PORT:       int  = 587
    MAIL_STARTTLS:   bool = True
    MAIL_SSL_TLS:    bool = False

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
            f"?charset=utf8mb4"
        )

    class Config:
        env_file = ".env"

settings = Settings()