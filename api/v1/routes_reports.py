"""
Router para endpoints de reportería.
Módulo independiente con restricción de acceso por perfil.
"""

import logging
import io
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from datetime import date, datetime
from typing import Optional
from sqlalchemy.orm import Session
from app.decorators.auth_decorator import jwt_required
from app.decorators.role_decorator import require_profile
from app.services.report_service import ReportService
from app.dependencies import get_db_pg, get_db_gestorv1
from app.schemas.report_schema import (
    ManagedByHourResponse,
    DailyProductivityResponse,
    HistoricalIncomeVsManagedResponse,
    IncomeByHourResponse,
    DailyIncomeManagedResponse,
    IncomeByConceptResponse,
    AvailableOffersByConceptResponse,
    DataTypeEnum,
    BusinessUnitEnum,
    ConceptGroupEnum,
    DateFieldEnum,
    ExportFormatEnum,
    ErrorResponse
)

router = APIRouter(prefix="/v1/reports", tags=["reports"])
logger = logging.getLogger("reports_routes")


# ==========================================
# REPORTE 1: Gestiones por Hora/Asesor
# ==========================================

@router.get(
    "/managed-by-hour",
    response_model=ManagedByHourResponse,
    dependencies=[Depends(jwt_required), Depends(require_profile([1, 3, 5]))],
    summary="Tabla de ofertas gestionadas por hora/asesor (día actual)",
    description="Muestra la cantidad de ofertas gestionadas por cada asesor en intervalos de 1 hora (6 AM - 9 PM) del día actual."
)
async def get_managed_by_hour(db: Session = Depends(get_db_pg)):
    """
    Obtiene las ofertas gestionadas por hora y asesor del día actual.
    
    - **Rango horario**: 6:00 AM - 9:00 PM
    - **Filtro**: Solo día actual
    - **Permisos**: SuperUsuario (1), Supervisor (3), Viewer (5)
    """
    service = ReportService(db)
    try:
        result = service.get_managed_by_hour_today()
        return result
    except Exception as e:
        logger.error(f"Error en endpoint managed-by-hour: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener reporte: {str(e)}"
        )


# ==========================================
# REPORTE 2: Productividad Diaria por Asesor
# ==========================================

@router.get(
    "/daily-productivity",
    response_model=DailyProductivityResponse,
    dependencies=[Depends(jwt_required), Depends(require_profile([1, 3, 5]))],
    summary="Tabla de productividad diaria por asesor",
    description="Muestra el conteo de ofertas gestionadas por asesor con filtro de fecha."
)
async def get_daily_productivity(
    date_from: date = Query(..., description="Fecha de inicio (YYYY-MM-DD)"),
    date_to: date = Query(..., description="Fecha de fin (YYYY-MM-DD)"),
    db: Session = Depends(get_db_pg)
):
    """
    Obtiene la productividad diaria de cada asesor.
    
    - **Filtros**: Rango de fechas
    - **Métricas**: Total gestiones, promedio diario, gestiones por día
    - **Permisos**: SuperUsuario (1), Supervisor (3), Viewer (5)
    """
    service = ReportService(db)
    try:
        # Validar fechas
        if date_from > date_to:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La fecha de inicio no puede ser mayor que la fecha de fin"
            )

        result = service.get_daily_productivity_by_advisor(date_from, date_to)
        return result
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        logger.error(f"Error en endpoint daily-productivity: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener reporte: {str(e)}"
        )


# ==========================================
# REPORTE 3: Histórico Ingresos vs Gestiones
# ==========================================

@router.get(
    "/historical-income-vs-managed",
    response_model=HistoricalIncomeVsManagedResponse,
    dependencies=[Depends(jwt_required), Depends(require_profile([1, 3, 5]))],
    summary="Gráfico de líneas: Ingresos Enlistment vs Gestiones",
    description="Histórico comparativo de ingresos diarios vs gestiones cerradas. Máximo 2 meses. Filtros independientes por UEN y agrupación de conceptos."
)
async def get_historical_income_vs_managed(
    date_from: date = Query(..., description="Fecha de inicio (YYYY-MM-DD)"),
    date_to: date = Query(..., description="Fecha de fin (YYYY-MM-DD)"),
    business_unit: BusinessUnitEnum = Query(BusinessUnitEnum.ALL, description="Filtro por UEN"),
    concept_group: ConceptGroupEnum = Query(ConceptGroupEnum.ALL, description="Filtro por agrupación de conceptos (ANULAR/RECONFIGURACION/ASIGNACION/ALL)"),
    db: Session = Depends(get_db_pg)
):
    """
    Obtiene histórico de ingresos vs gestiones.
    
    - **Filtros**: UEN (independiente), rango de fechas (máximo 2 meses), agrupación de conceptos
    - **Ingresos**: Todas las ofertas ingresadas (sin importar estado actual)
    - **Gestiones**: Ofertas cerradas/gestionadas
    - **Agrupación ANULAR**: ANULA, ANULA-C, ANULA-D
    - **Agrupación RECONFIGURACION**: Premisas Extendidas, 14, RECONFIGURACION BOT
    - **Agrupación ASIGNACION**: Cobertura, Conservar Numero, PETEC, PRESI, PSIEB, PUMED, etc.
    - **Permisos**: SuperUsuario (1), Supervisor (3), Viewer (5)
    """
    service = ReportService(db)
    try:
        # Validar fechas
        if date_from > date_to:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La fecha de inicio no puede ser mayor que la fecha de fin"
            )

        result = service.get_historical_income_vs_managed(
            business_unit.value, date_from, date_to, concept_group.value
        )
        return result
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        logger.error(f"Error en endpoint historical-income-vs-managed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener reporte: {str(e)}"
        )


# ==========================================
# REPORTE 4: Ingresos por Intervalo de Hora
# ==========================================

@router.get(
    "/income-by-hour",
    response_model=IncomeByHourResponse,
    dependencies=[Depends(jwt_required), Depends(require_profile([1, 3, 5]))],
    summary="Gráfico de barras: Ingresos por intervalo de hora",
    description="Distribución de ingresos de enlistment por hora (conteo real o promedio según rango)."
)
async def get_income_by_hour(
    date_from: Optional[date] = Query(None, description="Fecha de inicio (YYYY-MM-DD). Por defecto: hoy"),
    date_to: Optional[date] = Query(None, description="Fecha de fin (YYYY-MM-DD). Por defecto: igual a date_from"),
    concept_group: ConceptGroupEnum = Query(ConceptGroupEnum.ALL, description="Filtro por agrupación de conceptos (ANULAR/RECONFIGURACION/ASIGNACION/ALL)"),
    db: Session = Depends(get_db_pg)
):
    """
    Obtiene la distribución de ingresos por hora.
    
    - **Comportamiento**:
      - Un solo día: conteo real de ingresos por hora
      - Rango de días: promedio de ingresos por hora (máximo 30 días)
    - **Filtros**: Rango de fechas (opcional, por defecto día actual), agrupación de conceptos
    - **Datos**: Ingresos por hora (0-23), total y flag is_average
    - **Agrupación ANULAR**: ANULA, ANULA-C, ANULA-D
    - **Agrupación RECONFIGURACION**: Premisas Extendidas, 14, RECONFIGURACION BOT
    - **Agrupación ASIGNACION**: Cobertura, Conservar Numero, PETEC, PRESI, PSIEB, PUMED, etc.
    - **Permisos**: SuperUsuario (1), Supervisor (3), Viewer (5)
    """
    service = ReportService(db)
    try:
        # Si no se proporciona date_from, usar hoy
        start_date = date_from if date_from else date.today()
        # Si no se proporciona date_to, usar date_from
        end_date = date_to if date_to else start_date
        
        # Validar que date_from <= date_to
        if start_date > end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La fecha de inicio no puede ser mayor que la fecha de fin"
            )
        
        result = service.get_income_by_hour_interval(start_date, end_date, concept_group.value)
        return result
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        logger.error(f"Error en endpoint income-by-hour: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener reporte: {str(e)}"
        )


# ==========================================
# REPORTE 5: Ingresos y Gestiones Diario
# ==========================================

@router.get(
    "/daily-income-managed",
    response_model=DailyIncomeManagedResponse,
    dependencies=[Depends(jwt_required), Depends(require_profile([1, 3, 5]))],
    summary="Gráfico de barras: Ingresos y/o Gestiones por día",
    description="Comparación diaria de ingresos y gestiones con filtros personalizables."
)
async def get_daily_income_managed(
    date_from: date = Query(..., description="Fecha de inicio (YYYY-MM-DD)"),
    date_to: date = Query(..., description="Fecha de fin (YYYY-MM-DD)"),
    data_type: DataTypeEnum = Query(DataTypeEnum.BOTH, description="Tipo de datos a mostrar"),
    concept_group: ConceptGroupEnum = Query(ConceptGroupEnum.ALL, description="Filtro por agrupación de conceptos (ANULAR/RECONFIGURACION/ASIGNACION/ALL)"),
    db: Session = Depends(get_db_pg)
):
    """
    Obtiene ingresos y/o gestiones por día.
    
    - **Filtros**: Tipo de dato (INCOME/MANAGED/BOTH), rango de fechas, agrupación de conceptos
    - **Datos**: Comparación diaria configurable
    - **Agrupación ANULAR**: ANULA, ANULA-C, ANULA-D
    - **Agrupación RECONFIGURACION**: Premisas Extendidas, 14, RECONFIGURACION BOT
    - **Agrupación ASIGNACION**: Cobertura, Conservar Numero, PETEC, PRESI, PSIEB, PUMED, etc.
    - **Permisos**: SuperUsuario (1), Supervisor (3), Viewer (5)
    """
    service = ReportService(db)
    try:
        # Validar fechas
        if date_from > date_to:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La fecha de inicio no puede ser mayor que la fecha de fin"
            )

        result = service.get_daily_income_managed(
            data_type.value, date_from, date_to, concept_group.value
        )
        return result
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        logger.error(f"Error en endpoint daily-income-managed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener reporte: {str(e)}"
        )


# ==========================================
# REPORTE 6: Ingresos por Concepto
# ==========================================

@router.get(
    "/income-by-concept",
    response_model=IncomeByConceptResponse,
    dependencies=[Depends(jwt_required), Depends(require_profile([1, 3, 5]))],
    summary="Gráfico de barras: Ingresos diarios por concepto",
    description="Histórico de ingresos agrupados por concepto con comparación mensual."
)
async def get_income_by_concept(
    month: str = Query(..., description="Mes a consultar (formato: YYYY-MM)", regex=r"^\d{4}-\d{2}$"),
    concept: Optional[str] = Query(None, description="Filtro por concepto específico"),
    concept_group: ConceptGroupEnum = Query(ConceptGroupEnum.ALL, description="Filtro por agrupación de conceptos (ANULAR/RECONFIGURACION/ASIGNACION/ALL)"),
    db: Session = Depends(get_db_pg)
):
    """
    Obtiene ingresos diarios agrupados por concepto.
    
    - **Filtros**: Mes (YYYY-MM), concepto individual (opcional), agrupación de conceptos
    - **Filtros combinados**: Puede usar ambos filtros simultáneamente (ej: grupo ASIGNACION + concepto PETEC)
    - **Datos**: Distribución de ingresos por concepto cada día del mes
    - **Agrupación ANULAR**: ANULA, ANULA-C, ANULA-D
    - **Agrupación RECONFIGURACION**: Premisas Extendidas, 14, RECONFIGURACION BOT
    - **Agrupación ASIGNACION**: Cobertura, Conservar Numero, PETEC, PRESI, PSIEB, PUMED, etc.
    - **Permisos**: SuperUsuario (1), Supervisor (3), Viewer (5)
    """
    service = ReportService(db)
    try:
        result = service.get_income_by_concept_month(month, concept, concept_group.value)
        return result
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        logger.error(f"Error en endpoint income-by-concept: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener reporte: {str(e)}"
        )


# ==========================================
# REPORTE 7: Ofertas Disponibles por Concepto
# ==========================================

@router.get(
    "/available-offers-by-concept",
    dependencies=[Depends(jwt_required), Depends(require_profile([1, 3, 5]))],
    summary="Reporte de ofertas disponibles por concepto e intervalo de tiempo",
    description="Muestra ofertas ABIERTAS agrupadas por concepto y clasificadas por tiempo transcurrido desde su ingreso."
)
async def get_available_offers_by_concept(
    date_from: Optional[date] = Query(None, description="Fecha desde (YYYY-MM-DD)"),
    date_to: Optional[date] = Query(None, description="Fecha hasta (YYYY-MM-DD)"),
    date_field: DateFieldEnum = Query(DateFieldEnum.GESTOR, description="Campo de fecha a usar para filtros"),
    export_format: ExportFormatEnum = Query(ExportFormatEnum.JSON, description="Formato de exportación"),
    db: Session = Depends(get_db_pg)
):
    """
    Obtiene reporte de ofertas disponibles por concepto e intervalo de tiempo.
    
    - **Intervalos**: 
      - 0-30 minutos
      - 31-60 minutos
      - 1-2 horas
      - 3-5 horas
      - 5-7 horas
      - 7-12 horas
      - 12-24 horas
      - 24-48 horas
      - Más de 48 horas
    
    - **Filtros**:
      - date_from/date_to: Rango de fechas opcional
      - date_field: CRM (fecha_creado en Siebel) o GESTOR (created_at)
    
    - **Exportación**: 
      - JSON: Retorna estructura de datos
      - CSV: Descarga ofertas_disponibles_YYYYMMDDHHmmss.csv
    
    - **Permisos**: SuperUsuario (1), Supervisor (3), Viewer (5)
    """
    service = ReportService(db)
    try:
        # Validar fechas
        if date_from and date_to and date_from > date_to:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La fecha de inicio no puede ser mayor que la fecha de fin"
            )
        
        result = service.get_available_offers_by_concept(
            date_from, date_to, date_field.value, export_format.value
        )
        
        # Si es JSON, retornar directamente
        if export_format == ExportFormatEnum.JSON:
            return result
        
        # Si es CSV, retornar como archivo
        file_content, filename = result
        
        return StreamingResponse(
            io.BytesIO(file_content.encode('utf-8')),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        logger.error(f"Error en endpoint available-offers-by-concept: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener reporte: {str(e)}"
        )


# ==========================================
# REPORTE 8: Exportación CSV Cancelaciones
# ==========================================

@router.get(
    "/export-cancellations-csv",
    dependencies=[Depends(jwt_required), Depends(require_profile([1, 3, 5]))],
    summary="Exportar CSV de ofertas canceladas",
    description="Exporta ofertas con conceptos ANULA, ANULA-C, ANULA-D de los últimos días en formato CSV UTF-8."
)
async def export_cancellations_csv(
    days_back: int = Query(default=3, ge=1, le=30, description="Días hacia atrás desde hoy"),
    db: Session = Depends(get_db_pg)
):
    """
    Exporta ofertas canceladas en formato CSV.
    
    - **days_back**: Días hacia atrás desde hoy (default: 3, máx: 30)
    - **Formato**: CSV UTF-8 separado por comas
    - **Conceptos**: ANULA, ANULA-C, ANULA-D
    - **Permisos**: SuperUsuario (1), Supervisor (3), Viewer (5)
    """
    service = ReportService(db)
    try:
        # Generar contenido CSV
        csv_content = service.generate_cancellations_csv(days_back)
        
        # Timestamp para el nombre del archivo
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"cancelaciones_{timestamp}.csv"
        
        # Retornar como streaming response con BOM para Excel
        return StreamingResponse(
            io.BytesIO(csv_content.encode('utf-8-sig')),
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
        
    except Exception as e:
        logger.error(f"Error en endpoint export-cancellations-csv: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al exportar CSV: {str(e)}"
        )


# ==========================================
# REPORTE 9: Liquidación
# ==========================================

@router.get(
    "/liquidation",
    dependencies=[Depends(jwt_required), Depends(require_profile([1, 3, 5]))],
    summary="Reporte de liquidación de ofertas cerradas",
    description="Obtiene ofertas que pasaron a estado CERRADO con validación de garantía. Soporta JSON paginado y CSV completo."
)
async def get_liquidation_report(
    date_from: date = Query(..., description="Fecha inicio del periodo (YYYY-MM-DD)"),
    date_to: date = Query(..., description="Fecha fin del periodo (YYYY-MM-DD)"),
    export_format: str = Query(default="JSON", regex="^(JSON|CSV)$", description="Formato de exportación: JSON o CSV"),
    page: int = Query(default=1, ge=1, description="Número de página (solo para JSON)"),
    page_size: int = Query(default=100, ge=1, le=1000, description="Registros por página (solo para JSON)"),
    db: Session = Depends(get_db_pg)
):
    """
    Reporte de liquidación de ofertas cerradas.
    
    - **date_from**: Fecha inicio (requerido)
    - **date_to**: Fecha fin (requerido, máx 30 días de diferencia)
    - **export_format**: JSON (paginado) o CSV (completo)
    - **page**: Número de página (solo JSON, default: 1)
    - **page_size**: Tamaño de página (solo JSON, default: 100, máx: 1000)
    - **Permisos**: SuperUsuario (1), Supervisor (3), Viewer (5)
    """
    service = ReportService(db)
    
    try:
        # Validar que date_from <= date_to
        if date_from > date_to:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="date_from debe ser menor o igual a date_to"
            )
        
        # Validar rango máximo de 30 días
        days_diff = (date_to - date_from).days
        if days_diff > 31:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El rango de fechas no puede exceder 30 días"
            )
        
        # Modo CSV: exportar todo sin paginación
        if export_format.upper() == "CSV":
            csv_content = service.generate_liquidation_csv(date_from, date_to)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"liquidacion_{timestamp}.csv"
            
            return StreamingResponse(
                io.BytesIO(csv_content.encode('utf-8-sig')),
                media_type="text/csv; charset=utf-8",
                headers={
                    "Content-Disposition": f"attachment; filename={filename}"
                }
            )
        
        # Modo JSON: retornar con paginación
        else:
            result = service.get_liquidation_report(
                date_from=date_from,
                date_to=date_to,
                page=page,
                page_size=page_size
            )
            return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en endpoint liquidation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener reporte de liquidación: {str(e)}"
        )

# ==========================================
# REPORTES EMTELCO
# ==========================================

@router.get(
    "/history-ad",
    dependencies=[Depends(jwt_required), Depends(require_profile([2]))],
    summary="Reporte de A&D Historico Activación",
    description="Reporte para Emtelco Gestor V1."
)
async def get_history_activation_gestor_v1(
    date_from: date = Query(..., description="Fecha inicio del periodo (YYYY-MM-DD)"),
    date_to: date = Query(..., description="Fecha fin del periodo (YYYY-MM-DD)"),
    db: Session = Depends(get_db_gestorv1)
):
    """
    Reporte de liquidación de ofertas cerradas.
    
    - **date_from**: Fecha inicio (requerido)
    - **date_to**: Fecha fin (requerido, máx 30 días de diferencia)
    - **Permisos**: M2M (2)
    """
    service = ReportService(db)
    
    try:
        # Validar que date_from <= date_to
        if date_from > date_to:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="date_from debe ser menor o igual a date_to"
            )
        
        # Validar rango máximo de 30 días
        days_diff = (date_to - date_from).days
        if days_diff >= 15:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El rango de fechas no puede exceder 15 días"
            )
        
        result = service.get_history_activation_gestor_v1(
            date_from=date_from,
            date_to=date_to,
        )
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en endpoint liquidation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener reporte de liquidación: {str(e)}"
        )

@router.get(
    "/enlistment-manager-emt",
    dependencies=[Depends(jwt_required), Depends(require_profile([2]))],
    summary="Reporte de Gestor de Alistamiento EMT",
    description="Reporte para Emtelco Gestor de Alistamiento."
)
async def get_enlistment_manager_emt(
    date_from: date = Query(..., description="Fecha inicio del periodo (YYYY-MM-DD)"),
    date_to: date = Query(..., description="Fecha fin del periodo (YYYY-MM-DD)"),
    db: Session = Depends(get_db_pg)
):
    """
    Reporte de liquidación de ofertas cerradas.
    
    - **date_from**: Fecha inicio (requerido)
    - **date_to**: Fecha fin (requerido, máx 30 días de diferencia)
    - **Permisos**: M2M (2)
    """
    service = ReportService(db)
    
    try:
        # Validar que date_from <= date_to
        if date_from > date_to:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="date_from debe ser menor o igual a date_to"
            )
        
        # Validar rango máximo de 30 días
        days_diff = (date_to - date_from).days
        if days_diff >= 15:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El rango de fechas no puede exceder 15 días"
            )
        
        result = service.get_enlistment_manager_emt(
            date_from=date_from,
            date_to=date_to,
        )
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en endpoint liquidation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener reporte de liquidación: {str(e)}"
        )
