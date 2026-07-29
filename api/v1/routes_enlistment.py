import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional
from datetime import date
from sqlalchemy.orm import Session
from app.decorators.auth_decorator import jwt_required
from app.services.enlistment_service import EnlistmentService
from app.dependencies import get_db_pg
from app.schemas.enlistment_schema import (
    EnlistmentListResponse,
    EnlistmentDataResponse,
    EnlistmentHistoryResponse,
    EnlistmentControlResponse,
    EnlistmentFieldStatsResponse,
    SuccessResponse,
    ErrorResponse
)

router = APIRouter(prefix="/v1/enlistment", tags=["enlistment"])
logger = logging.getLogger("enlistment_routes")

# ==========================================
# ENDPOINTS DE UTILIDAD
# ==========================================

@router.get("/health", dependencies=[Depends(jwt_required)])
async def health_check(db: Session = Depends(get_db_pg)):
    """
    Health check del módulo enlistment.
    """
    service = EnlistmentService(db)
    try:
        # Verificar que el servicio puede acceder a la BD
        stats = await service.get_last_load_stats()
        
        return {
            "status": "healthy",
            "module": "enlistment_manager",
            "last_load": stats.get("create_date_automation") if stats else None
        }
        
    except Exception as e:
        logger.error(f"Health check falló: {e}")
        return {
            "status": "unhealthy",
            "module": "enlistment_manager",
            "error": str(e)
        }


# ==========================================
# CONSULTAS DE DATOS
# ==========================================

@router.get("", response_model=EnlistmentListResponse, dependencies=[Depends(jwt_required)])
async def get_enlistment_data(
    page: int = Query(1, ge=1, description="Número de página"),
    limit: int = Query(100, ge=1, le=1000, description="Registros por página"),
    offer: Optional[str] = Query(None, description="Filtrar por oferta"),
    responsible: Optional[str] = Query(None, description="Filtrar por responsable"),
    offer_state: Optional[str] = Query(None, description="Filtrar por estado de oferta"),
    technology: Optional[str] = Query(None, description="Filtrar por tecnología"),
    uen: Optional[str] = Query(None, description="Filtrar por UEN"),
    from_date: Optional[date] = Query(None, description="Fecha desde (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, description="Fecha hasta (YYYY-MM-DD)"),
    db: Session = Depends(get_db_pg)
):
    """
    Obtiene datos de enlistment_manager con filtros opcionales y paginación.
    
    Los filtros se aplican sobre los campos del JSONB campos_dinamicos.
    """
    service = EnlistmentService(db)
    try:
        logger.info(f"Consulta de datos: page={page}, limit={limit}, filtros={locals()}")
        
        # Construir diccionario de filtros
        filters = {}
        if offer:
            filters['oferta'] = offer
        if responsible:
            filters['responsable'] = responsible
        if offer_state:
            filters['estado_oferta'] = offer_state
        if technology:
            filters['tecnologia'] = technology
        if uen:
            filters['uen'] = uen
        if from_date:
            filters['fecha_desde'] = from_date
        if to_date:
            filters['fecha_hasta'] = to_date
        
        result = await service.get_data_with_filters(page, limit, filters if filters else None)
        
        return result
        
    except Exception as e:
        logger.error(f"Error al obtener datos: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/{offer}", response_model=EnlistmentDataResponse, dependencies=[Depends(jwt_required)])
async def get_enlistment_by_oferta(offer: str, db: Session = Depends(get_db_pg)):
    """
    Obtiene los datos actuales de una oferta específica.
    """
    service = EnlistmentService(db)
    try:
        logger.info(f"Consulta de oferta: {offer}")
        
        result = await service.get_by_oferta(offer)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Oferta {offer} no encontrada"
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al obtener oferta {offer}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ==========================================
# CONSULTAS DE HISTÓRICO
# ==========================================

@router.get("/history/{offer}", dependencies=[Depends(jwt_required)])
async def get_history_by_oferta(
    offer: str,
    limit: int = Query(50, ge=1, le=500, description="Límite de registros históricos"),
    db: Session = Depends(get_db_pg)
):
    """
    Obtiene el histórico completo de cambios de una oferta.
    Ordenado por fecha descendente (más reciente primero).
    """
    service = EnlistmentService(db)
    try:
        logger.info(f"Consulta histórico de oferta: {offer}, limit={limit}")
        
        history = await service.get_history_by_oferta(offer, limit)
        
        return {
            "oferta": offer,
            "total_cambios": len(history),
            "history": history
        }
        
    except Exception as e:
        logger.error(f"Error al obtener histórico de {offer}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ==========================================
# ESTADÍSTICAS Y CONTROL
# ==========================================

@router.get("/stats/last", response_model=EnlistmentControlResponse, dependencies=[Depends(jwt_required)])
async def get_last_load_stats(db: Session = Depends(get_db_pg)):
    """
    Obtiene las estadísticas de la última carga ejecutada.
    Incluye información de performance, cantidad de registros procesados, etc.
    """
    service = EnlistmentService(db)
    try:
        logger.info("Consulta de última carga")
        
        stats = await service.get_last_load_stats()
        
        if not stats:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No hay cargas registradas"
            )
        
        return stats
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al obtener estadísticas: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/stats/by-field/{field_name}", response_model=EnlistmentFieldStatsResponse, dependencies=[Depends(jwt_required)])
async def get_stats_by_field(
    field_name: str,
    limit: int = Query(10, ge=1, le=100, description="Límite de resultados"),
    db: Session = Depends(get_db_pg)
):
    """
    Obtiene estadísticas agrupadas por un campo específico del JSONB.
    Útil para ver distribución de valores (ej: responsables, tecnologías, estados).
    
    Ejemplos de field_name:
    - responsable
    - estado_oferta
    - tecnologia
    - uen
    - concepto
    """
    service = EnlistmentService(db)
    try:
        logger.info(f"Estadísticas por campo: {field_name}, limit={limit}")
        
        stats = await service.get_stats_by_field(field_name, limit)
        
        return {
            "field_name": field_name,
            "stats": stats
        }
        
    except Exception as e:
        logger.error(f"Error al obtener stats por campo {field_name}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ==========================================
# BÚSQUEDA Y FILTROS AVANZADOS
# ==========================================

@router.get("/search/field", dependencies=[Depends(jwt_required)])
async def search_by_field(
    field: str = Query(..., description="Nombre del campo en campos_dinamicos"),
    value: str = Query(..., description="Valor a buscar"),
    offer_state: Optional[str] = Query(None, description="Filtrar por estado de oferta"),
    page: int = Query(1, ge=1),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db_pg)
):
    """
    Búsqueda genérica por cualquier campo del JSONB.
    Permite consultar campos dinámicos que no están definidos como parámetros fijos.
    """
    service = EnlistmentService(db)
    try:
        logger.info(f"Búsqueda por campo: {field}={value}")
        
        filters = {field: value}
        if offer_state:
            filters['estado_oferta'] = offer_state
        
        logger.info(f"Búsqueda por campos: {filters}")
        
        result = await service.get_data_with_filters(page, limit, filters)
        
        return result
        
    except Exception as e:
        logger.error(f"Error en búsqueda por campo: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
