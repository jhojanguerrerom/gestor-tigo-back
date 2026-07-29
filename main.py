import logging
import time
from fastapi import FastAPI, HTTPException
from psycopg2 import OperationalError
from app.api.v1 import routes_auth, routes_automation, routes_enlistment, routes_ofertas, routes_reports, routes_users
from app.core.logging_config import setup_logging
from app.db import mongodb_client, oracle_fenix_session, oracle_mss_session, oracle_siebel_session, postgres, sqlserver_gestion_operativa_session, mysql_session_gestor
from app.core.config import settings

from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

# Configurar logs
setup_logging(settings.APP_ENV)
logger = logging.getLogger("app")

app = FastAPI(title="Gestor API")
app.include_router(routes_auth.router)
app.include_router(routes_automation.router)
app.include_router(routes_enlistment.router)
app.include_router(routes_ofertas.router)
app.include_router(routes_reports.router)
app.include_router(routes_users.router)

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.error({
            "status": "error",
            "code": exc.status_code,
            "message": str(exc.detail),
            "path": str(request.url.path)
        })
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "type": "error",
            "message": str(exc.detail),
        },
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    
    logger.error(str(exc.errors()))

    return JSONResponse(
        status_code=422,
        content={
            "type": "error",
            "message": exc._errors[0].get('msg', '')
        },
    )

def wait_for_db(engine, retries=10, delay=2):
    try:
        for i in range(retries):
            try:
                conn = engine.connect()
                conn.close()
                logger.info("✅ Conexión satisfactoria.")
                logger.info(f"Engine: {engine.url}")
                return True
            except Exception as e:
                logger.error(f"An unexpected error occurred: {e}")
                logger.error(f"❌ Reintentando conexion: numero {i}.")
                time.sleep(delay)
        logger.error("Fallo la conexión a la base de datos.")
        return False
    except OperationalError as e:
        logger.error(f"An operational error occurred: {e}")
        return False

@app.on_event("startup")
def startup():
    # wait for DBs
    wait_for_db(postgres.engine_pg, retries=2, delay=2)
    wait_for_db(oracle_fenix_session.engine_fenix, retries=2, delay=2)
    wait_for_db(oracle_mss_session.engine_mss, retries=2, delay=2)
    wait_for_db(oracle_siebel_session.engine_siebel, retries=2, delay=2)
    wait_for_db(sqlserver_gestion_operativa_session.engine_sqlserver_gestion, retries=2, delay=2)
    wait_for_db(mysql_session_gestor.engine_mysql, retries=2, delay=2)
    
    try:
        mongodb_client.client.admin.command("ping")
        logger.info("✅ Conectado exitosamente a MongoDB")
    except Exception as e:
        logger.error(f"❌ Error al conectar a MongoDB: {e}")

@app.get("/")
def root():
    return {"message": "Gestor API"}
