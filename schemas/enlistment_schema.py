from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime


# ==========================================
# SCHEMAS DE RESPUESTA
# ==========================================

class EnlistmentDataResponse(BaseModel):
    """Schema para datos de enlistment_manager"""
    id: str
    oferta: str
    ticket_carga: str
    hash_registro: str
    estado_oferta: str
    usuario_asignado_login: Optional[str]
    usuario_asignado_nombre: Optional[str]
    campos_dinamicos: Dict[str, Any]
    created_at: Optional[str]
    updated_at: Optional[str]

    class Config:
        from_attributes = True


class PaginationMeta(BaseModel):
    """Schema para metadata de paginación"""
    page: int
    limit: int
    total: int
    total_pages: int


class EnlistmentListResponse(BaseModel):
    """Schema para respuesta de lista paginada"""
    data: List[EnlistmentDataResponse]
    pagination: PaginationMeta


class EnlistmentHistoryResponse(BaseModel):
    """Schema para registro de histórico"""
    id: str
    oferta: str
    ticket_carga: str
    create_date_automation: Optional[str]
    tipo_operacion: str
    hash_registro: str
    campos_dinamicos: Dict[str, Any]
    campos_modificados: Optional[Dict[str, Any]]
    created_at: Optional[str]

    class Config:
        from_attributes = True


class EnlistmentControlResponse(BaseModel):
    """Schema para registro de control"""
    ticket_carga: str
    create_date_automation: Optional[str]
    total_registros_procesados: int
    total_registros_nuevos: int
    total_registros_actualizados: int
    total_registros_sin_cambios: int
    tiempo_ejecucion_segundos: Optional[float]
    estado: str
    mensaje_error: Optional[str]
    columnas_detectadas: Optional[List[str]]

    class Config:
        from_attributes = True


class EnlistmentLoadStatsResponse(BaseModel):
    """Schema para estadísticas de carga"""
    ticket_carga: str
    total_procesados: int
    nuevos: int
    modificados: int
    sin_cambios: int
    tiempo_ejecucion: float


class EnlistmentFieldStats(BaseModel):
    """Schema para estadísticas por campo"""
    valor: str
    total: int


class EnlistmentFieldStatsResponse(BaseModel):
    """Schema para respuesta de estadísticas por campo"""
    field_name: str
    stats: List[EnlistmentFieldStats]


# ==========================================
# SCHEMAS GENÉRICOS
# ==========================================

class SuccessResponse(BaseModel):
    """Schema para respuestas exitosas genéricas"""
    type: str = "success"
    msg: Any


class ErrorResponse(BaseModel):
    """Schema para respuestas de error"""
    type: str = "error"
    msg: str
