from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Engine para SQL Server 2019 con configuración de pool
engine_sqlserver_gestion = create_engine(
    settings.SQLSERVER_GESTION_OPERATIVA_URL,
    pool_pre_ping=True,      # Verificar conexión antes de usar
    pool_size=5,             # Número de conexiones en el pool
    max_overflow=10,         # Conexiones adicionales si se necesitan
    pool_recycle=3600,       # Reciclar conexiones cada hora
    echo=False               # True para debug SQL
)

# Session maker
SessionLocalSQLServerGestion = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine_sqlserver_gestion
)
