from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

engine_mysql = create_engine(settings.MYSQL_URL, pool_pre_ping=True)
SessionLocalMySQL = sessionmaker(autocommit=False, autoflush=False, bind=engine_mysql)
