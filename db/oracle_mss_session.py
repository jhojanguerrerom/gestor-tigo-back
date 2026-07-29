from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
import oracledb

# oracledb 1.x con Oracle 11g en modo thick
try:
    oracledb.init_oracle_client(lib_dir="/opt/oracle/instantclient")
except:
    pass  # Ya inicializado o no necesario

engine_mss = create_engine(
    settings.ORACLE_URL_MSS_STBDY,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    pool_recycle=3600
)
SessionLocalMss = sessionmaker(autocommit=False, autoflush=False, bind=engine_mss)