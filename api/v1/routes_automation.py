import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.decorators.auth_decorator import jwt_required
from app.services.automation_service import AutomationService
from app.dependencies import get_db_pg
from app.schemas.automation_schema import AutomationResponse, DataFenixResponse, DataSiebelResponse, DataProcessResponse

router = APIRouter(prefix="/v1", tags=["automation"])
logger = logging.getLogger("automation_routes")


# ============================
# GET DATA FENIX
# ============================
# @router.get("/getdatafenix", response_model=DataFenixResponse, dependencies=[Depends(jwt_required)])
# async def get_data_fenix():
#     """
#     Obtiene los datos de la base de datos Fenix Standby.
#     Ejecuta la consulta y retorna los resultados.
#     """
#     try:
#         logger.info("Inicio: Obtener datos de Fenix")
#         result = await service.get_data_fenix(is_returnable=False)

#         if result["type"] == "error":
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail=result["msg"]
#             )

#         return result

#     except HTTPException as e:
#         logger.error(f"Error HTTP al obtener datos de Fenix: {e.detail}")
#         raise e
#     except Exception as e:
#         logger.error(f"Error al obtener datos de Fenix: {e}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=str(e)
#         )
#     finally:
#         logger.info("Fin: Obtener datos de Fenix")

# ============================
# GET DATA SIEBEL
# ============================
# @router.get("/getdatasiebel", response_model=DataSiebelResponse, dependencies=[Depends(jwt_required)])
# async def get_data_siebel():
#     """
#     Obtiene los datos de la base de datos Siebel Standby.
#     Ejecuta la consulta y retorna los resultados.
#     """
#     try:
#         logger.info("Inicio: Obtener datos de Siebel")
#         result = await service.get_data_siebel(is_returnable=False)

#         if result["type"] == "error":
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail=result["msg"]
#             )

#         return result

#     except HTTPException as e:
#         logger.error(f"Error HTTP al obtener datos de Siebel: {e.detail}")
#         raise e
#     except Exception as e:
#         logger.error(f"Error al obtener datos de Siebel: {e}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=str(e)
#         )
#     finally:
#         logger.info("Fin: Obtener datos de Siebel")

# ============================
# PROCESS GESTOR DATA
# ============================
@router.post("/processdatagestor", response_model=DataProcessResponse, dependencies=[Depends(jwt_required)])
async def process_data_gestor(db: Session = Depends(get_db_pg)):
    """
    Procesa los datos siebel y fenix para tabular la data del gestor
    """
    service = AutomationService(db)
    try:
        logger.info("Inicio: Procesar data")
        result = await service.process_data_gestor(is_returnable=False)

        if result["type"] == "error":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result["msg"]
            )

        return result

    except HTTPException as e:
        logger.error(f"Error HTTP al Procesar data: {e.detail}")
        raise e
    except Exception as e:
        logger.error(f"Error al Procesar data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    finally:
        logger.info("Fin: Procesar data")

# ============================
# SET DATA GESTOR OPERACION FENIX
# ============================
# @router.post("/setdatagestoroperacionfenix", response_model=AutomationResponse)
# async def set_data_gestor_operacion_fenix():
#     """
#     Procesa los datos de Fenix y los carga en la tabla gestor_operacion.
#     - Obtiene datos de Fenix
#     - Valida y mapea campos a tablas de catálogo
#     - Crea o actualiza registros en gestor_operacion
#     """
#     try:
#         logger.info("Inicio: Procesar datos de Fenix a gestor_operacion")
#         result = await service.set_data_gestor_operacion_fenix()

#         if result["type"] == "error":
#             raise HTTPException(
#                 status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#                 detail=result["msg"]
#             )

#         return result

#     except HTTPException as e:
#         logger.error(f"Error HTTP al procesar datos de Fenix: {e.detail}")
#         raise e
#     except Exception as e:
#         logger.error(f"Error al procesar datos de Fenix: {e}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=str(e)
#         )
#     finally:
#         logger.info("Fin: Procesar datos de Fenix a gestor_operacion")


# ============================
# SET DATA GESTOR OPERACION SIEBEL
# ============================
# @router.post("/setdatagestoroperacionsiebel", response_model=AutomationResponse)
# async def set_data_gestor_operacion_siebel():
#     """
#     Procesa los datos de Siebel y los carga en la tabla gestor_operacion.
#     - Obtiene datos de Siebel
#     - Valida y mapea campos a tablas de catálogo
#     - Crea o actualiza registros en gestor_operacion
#     """
#     try:
#         logger.info("Inicio: Procesar datos de Siebel a gestor_operacion")
#         result = await service.set_data_gestor_operacion_siebel()

#         if result["type"] == "error":
#             raise HTTPException(
#                 status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#                 detail=result["msg"]
#             )

#         return result

#     except HTTPException as e:
#         logger.error(f"Error HTTP al procesar datos de Siebel: {e.detail}")
#         raise e
#     except Exception as e:
#         logger.error(f"Error al procesar datos de Siebel: {e}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=str(e)
#         )
#     finally:
#         logger.info("Fin: Procesar datos de Siebel a gestor_operacion")
