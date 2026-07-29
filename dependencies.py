"""
FastAPI Dependencies para inyección de dependencias de base de datos.
Proporciona sesiones de base de datos que se crean por request y se cierran automáticamente.
"""

from typing import Generator
from sqlalchemy.orm import Session
from app.db.postgres import SessionLocalPG
from app.db.oracle_fenix_session import SessionLocalFenix
from app.db.oracle_siebel_session import SessionLocalSiebel
from app.db.sqlserver_gestion_operativa_session import SessionLocalSQLServerGestion
from app.db.mysql_session_gestor import SessionLocalMySQL

def get_db_pg() -> Generator[Session, None, None]:
    """
    Dependency para obtener sesión de PostgreSQL.
    Se crea una nueva sesión por request y se cierra automáticamente al finalizar.
    
    Usage:
        @router.get("/endpoint")
        async def endpoint(db: Session = Depends(get_db_pg)):
            # usar db aquí
    """
    db = SessionLocalPG()
    try:
        yield db
    finally:
        db.close()


def get_db_fenix() -> Generator[Session, None, None]:
    """
    Dependency para obtener sesión de Oracle Fenix.
    Se crea una nueva sesión por request y se cierra automáticamente al finalizar.
    """
    db = SessionLocalFenix()
    try:
        yield db
    finally:
        db.close()


def get_db_siebel() -> Generator[Session, None, None]:
    """
    Dependency para obtener sesión de Oracle Siebel.
    Se crea una nueva sesión por request y se cierra automáticamente al finalizar.
    """
    db = SessionLocalSiebel()
    try:
        yield db
    finally:
        db.close()


def get_db_sqlserver() -> Generator[Session, None, None]:
    """
    Dependency para obtener sesión de SQL Server.
    Se crea una nueva sesión por request y se cierra automáticamente al finalizar.
    """
    db = SessionLocalSQLServerGestion()
    try:
        yield db
    finally:
        db.close()

def get_db_gestorv1() -> Generator[Session, None, None]:
    """
    Dependency para obtener sesión de SQL Server.
    Se crea una nueva sesión por request y se cierra automáticamente al finalizar.
    """
    db = SessionLocalMySQL()
    try:
        yield db
    finally:
        db.close()
