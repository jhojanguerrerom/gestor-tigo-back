from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

engine_pg = create_engine(settings.POSTGRES_URL, pool_pre_ping=True)

# Establecer timezone America/Bogota en cada conexión a PostgreSQL
@event.listens_for(engine_pg, "connect")
def set_timezone(dbapi_conn, connection_record):
    """Configura la zona horaria de Colombia en cada conexión a la base de datos"""
    cursor = dbapi_conn.cursor()
    cursor.execute("SET timezone='America/Bogota'")
    cursor.close()

SessionLocalPG = sessionmaker(autocommit=False, autoflush=False, bind=engine_pg)
