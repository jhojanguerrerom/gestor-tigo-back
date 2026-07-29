from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    MYSQL_URL: str
    MYSQL_URL_GESTOR: str
    POSTGRES_URL: str
    ORACLE_URL_FENIX_STBDY: str
    ORACLE_URL_MSS_STBDY: str
    ORACLE_URL_SIEBEL_STBDY: str
    SQLSERVER_GESTION_OPERATIVA_URL: str
    MONGO_URL: str
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 15
    JWT_REFRESH_EXPIRE_MINUTES: int = 60*24*7
    REDIS_URL: str
    APP_ENV: str
    # 🔐 SINGLE SESSION: Configuración de modo de sesión
    SINGLE_SESSION_MODE: bool = True  # True = solo 1 sesión activa, False = múltiples sesiones
    # 🔐 MAX SESSION: Límite absoluto de duración de sesión (en días)
    MAX_SESSION_DAYS: int = 30  # Después de 30 días desde login original, se requiere re-login
    # 📊 ENLISTMENT: Control de ofertas para cierre automático
    ENLISTMENT_CARGAS_INACTIVIDAD: int = 3  # Número de cargas consecutivas sin aparecer para cerrar automáticamente

    class Config:
        env_file = ".env"

settings = Settings()
