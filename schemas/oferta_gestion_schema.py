from pydantic import BaseModel, Field, validator
from typing import Dict, Any, List, Optional
from datetime import datetime


# ==========================================
# SCHEMAS DE CATÁLOGOS
# ==========================================

class AccionCatalogoResponse(BaseModel):
    """Schema para respuesta de acción del catálogo"""
    id: str
    nombre: str
    descripcion: Optional[str]
    is_active: bool
    orden: int
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class SubaccionCatalogoResponse(BaseModel):
    """Schema para respuesta de subacción del catálogo"""
    id: str
    accion_id: str
    nombre: str
    is_active: bool
    orden: int
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class AccionConSubaccionesResponse(BaseModel):
    """Schema para respuesta de acción con sus subacciones"""
    id: str
    nombre: str
    descripcion: Optional[str]
    is_active: bool
    orden: int
    subacciones: List[SubaccionCatalogoResponse]


class CreateAccionRequest(BaseModel):
    """Schema para crear una acción"""
    nombre: str = Field(..., min_length=1, max_length=100)
    descripcion: Optional[str] = None
    orden: int = Field(default=0, ge=0)


class UpdateAccionRequest(BaseModel):
    """Schema para actualizar una acción"""
    nombre: Optional[str] = Field(None, min_length=1, max_length=100)
    descripcion: Optional[str] = None
    orden: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None


class CreateSubaccionRequest(BaseModel):
    """Schema para crear una subacción"""
    accion_id: str
    nombre: str = Field(..., min_length=1)
    orden: int = Field(default=0, ge=0)


class UpdateSubaccionRequest(BaseModel):
    """Schema para actualizar una subacción"""
    nombre: Optional[str] = Field(None, min_length=1)
    orden: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None


class ConceptoCountResponse(BaseModel):
    """Schema para respuesta de concepto con cantidad"""
    concepto: str
    cantidad: int


# ==========================================
# SCHEMAS DE GESTIÓN DE OFERTAS
# ==========================================

class CongelarOfertaRequest(BaseModel):
    """Schema para congelar una oferta (opcional: por número específico o por concepto)"""
    oferta: Optional[str] = Field(None, description="Número específico de oferta a congelar (tiene prioridad sobre concepto)")
    concepto: Optional[str] = Field(None, description="Concepto específico a buscar (se ignora si se envía oferta)")


class CongelarOfertaResponse(BaseModel):
    """Schema para respuesta al congelar una oferta"""
    oferta: str
    estado: str
    usuario_asignado: str
    usuario_nombre: str
    fecha_asignacion: datetime
    campos_dinamicos: Dict[str, Any]


class MiOfertaResponse(BaseModel):
    """Schema para consultar oferta actual del usuario"""
    oferta: str
    estado: str
    fecha_asignacion: datetime
    tiempo_transcurrido_minutos: int
    campos_dinamicos: Dict[str, Any]


class GestionarOfertaRequest(BaseModel):
    """Schema para gestionar/cerrar una oferta"""
    oferta: str = Field(..., min_length=1)
    accion_id: str
    subaccion_id: str
    observacion: Optional[str] = None


class GestionarOfertaResponse(BaseModel):
    """Schema para respuesta al gestionar una oferta (normal, MALO o RFS)"""
    oferta: str
    estado: str
    # Campos para gestión normal
    accion: Optional[str] = None
    subaccion: Optional[str] = None
    # Campos para conceptos especiales (MALO, RFS)
    concepto: Optional[str] = None
    concepto_anterior: Optional[str] = None
    # Campo común
    fecha_gestion: datetime


class DescongelarOfertaRequest(BaseModel):
    """Schema para descongelar una oferta (Supervisor)"""
    oferta: str = Field(..., min_length=1)
    motivo: Optional[str] = None


class DescongelarOfertaResponse(BaseModel):
    """Schema para respuesta al descongelar"""
    oferta: str
    estado: str
    asesor_anterior: Optional[str]
    mensaje: str


class ReasignarOfertaRequest(BaseModel):
    """Schema para reasignar una oferta (Supervisor)"""
    oferta: str = Field(..., min_length=1)
    asesor_login: str = Field(..., min_length=1)
    motivo: Optional[str] = None


class ReasignarOfertaResponse(BaseModel):
    """Schema para respuesta al reasignar"""
    oferta: str
    asesor_anterior: Optional[str]
    asesor_nuevo: str
    asesor_nuevo_nombre: str
    reasignado_por: str
    mensaje: str


# ==========================================
# SCHEMAS DE CONFIGURACIÓN
# ==========================================

class ConfiguracionResponse(BaseModel):
    """Schema para respuesta de configuración"""
    id: str
    profile_id: int
    orden_busqueda: str
    descripcion: Optional[str]
    is_active: bool
    updated_by: Optional[str]
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class UpdateConfiguracionRequest(BaseModel):
    """Schema para actualizar configuración de orden"""
    profile_id: int = Field(..., ge=1, le=5)
    orden_busqueda: str = Field(..., pattern="^(ASC|DESC)$")
    descripcion: Optional[str] = None

    @validator('orden_busqueda')
    def validate_orden(cls, v):
        if v not in ['ASC', 'DESC']:
            raise ValueError('orden_busqueda debe ser ASC o DESC')
        return v


# ==========================================
# SCHEMAS DE HISTÓRICO Y REPORTES
# ==========================================

class HistoricoEstadoResponse(BaseModel):
    """Schema para histórico de estados de una oferta"""
    id: str
    accion: str
    estado_anterior: str
    estado_nuevo: str
    usuario: str
    usuario_nombre: str
    asesor_asignado: Optional[str]
    asesor_asignado_nombre: Optional[str]
    motivo: Optional[str]
    fecha: datetime

    class Config:
        from_attributes = True


class GestionDetalleResponse(BaseModel):
    """Schema para detalle de gestión de una oferta"""
    id: str
    oferta: str
    accion: str
    subaccion: str
    observacion: Optional[str]
    usuario: str
    usuario_nombre: str
    fecha_gestion: datetime

    class Config:
        from_attributes = True


class OfertaEnTramiteResponse(BaseModel):
    """Schema para ofertas en trámite (Dashboard Supervisor)"""
    oferta: str
    usuario_asignado: str
    usuario_nombre: str
    fecha_asignacion: datetime
    tiempo_transcurrido_minutos: int
    campos_dinamicos: Dict[str, Any]


class PaginationMeta(BaseModel):
    """Schema para metadata de paginación"""
    page: int
    limit: int
    total: int
    total_pages: int


class OfertasEnTramiteListResponse(BaseModel):
    """Schema para lista paginada de ofertas en trámite"""
    data: List[OfertaEnTramiteResponse]
    pagination: PaginationMeta


class ProductividadResponse(BaseModel):
    """Schema para reporte de productividad"""
    usuario: str
    usuario_nombre: str
    total_gestionadas: int
    por_accion: Dict[str, int]
    tiempo_promedio_gestion_minutos: Optional[float]


# ==========================================
# SCHEMAS GENÉRICOS
# ==========================================

class SuccessResponse(BaseModel):
    """Schema para respuestas exitosas genéricas"""
    success: bool = True
    message: str
    data: Optional[Any] = None


class ErrorResponse(BaseModel):
    """Schema para respuestas de error"""
    success: bool = False
    error: str
    details: Optional[Any] = None


# ==========================================
# SCHEMAS PARA OFERTA PAUSADA
# ==========================================

class PausarOfertaRequest(BaseModel):
    """Schema para pausar una oferta"""
    oferta: str = Field(..., min_length=1, description="Número de oferta a pausar")


class PausarOfertaResponse(BaseModel):
    """Schema para respuesta al pausar una oferta"""
    oferta: str
    concepto_anterior: str
    concepto_nuevo: str
    estado: str
    fecha_pausa: datetime


class ReanudarOfertaRequest(BaseModel):
    """Schema para reanudar una oferta pausada"""
    oferta: str = Field(..., min_length=1, description="Número de oferta a reanudar")


class ReanudarOfertaResponse(BaseModel):
    """Schema para respuesta al reanudar una oferta"""
    oferta: str
    concepto_restaurado: str
    estado: str
    fecha_reanudacion: datetime


class OfertaPausadaItem(BaseModel):
    """Schema para un item de oferta pausada en la lista"""
    oferta: str
    concepto_anterior: str
    fecha_pausa: datetime
    tiempo_pausado_minutos: int


class OfertaPausadaListResponse(BaseModel):
    """Schema para lista de ofertas pausadas"""
    ofertas: List[OfertaPausadaItem]
    total: int


class ConfiguracionPausadaResponse(BaseModel):
    """Schema para configuración de ofertas pausadas"""
    tiempo_minimo_pausa_minutos: int
    max_ofertas_pausadas_por_asesor: int
    updated_by: Optional[str]
    updated_at: Optional[datetime]


class UpdateConfiguracionPausadaRequest(BaseModel):
    """Schema para actualizar configuración de pausas"""
    tiempo_minimo_pausa_minutos: Optional[int] = Field(None, ge=0, description="Tiempo mínimo en minutos")
    max_ofertas_pausadas_por_asesor: Optional[int] = Field(None, ge=1, description="Cantidad máxima de ofertas pausadas")


class LiberarOfertaPausadaRequest(BaseModel):
    """Schema para liberar una oferta pausada (supervisor)"""
    oferta: str = Field(..., min_length=1, description="Número de oferta a liberar")
    motivo: Optional[str] = Field(None, description="Motivo de la liberación")


class LiberarOfertaPausadaResponse(BaseModel):
    """Schema para respuesta al liberar oferta pausada"""
    oferta: str
    concepto_restaurado: str
    estado: str
    usuario_anterior: str
    liberada_por: str
    fecha_liberacion: datetime


# ==========================================
# SCHEMAS PARA MALO Y RFS - LIBERACIÓN
# ==========================================

class GestionarConceptoEspecialResponse(BaseModel):
    """Schema para respuesta al gestionar con concepto especial"""
    oferta: str
    concepto: str
    concepto_anterior: str
    estado: str
    fecha_gestion: datetime


class LiberarConceptoEspecialRequest(BaseModel):
    """Schema para liberar oferta en concepto especial"""
    oferta: str = Field(..., min_length=1, description="Número de oferta")
    motivo: Optional[str] = Field(None, description="Motivo de la liberación")


class LiberarConceptoEspecialResponse(BaseModel):
    """Schema para respuesta al liberar concepto especial"""
    oferta: str
    concepto_anterior: str
    concepto_restaurado: str
    estado: str
    liberada_por: str
    fecha_liberacion: datetime


# ==========================================
# SCHEMAS PARA CONFIGURACIÓN GLOBAL AVANZADA
# ==========================================

class ConfiguracionGlobalAvanzadaUpdate(BaseModel):
    """Schema para actualizar configuración GLOBAL"""
    nombre_config: Optional[str] = Field(
        default='Configuración Global',
        description="Nombre de la configuración",
        max_length=100
    )
    campo_orden: str = Field(
        default='created_at',
        description="Campo para ordenar: created_at | fecha_creado",
        pattern='^(created_at|fecha_creado)$'
    )
    direccion_orden: str = Field(
        default='ASC',
        description="Dirección del ordenamiento: ASC | DESC",
        pattern='^(ASC|DESC)$'
    )
    filtro_conceptos_tipo: str = Field(
        default='TODOS',
        description="Tipo de filtro de conceptos: TODOS | ESPECIFICOS",
        pattern='^(TODOS|ESPECIFICOS)$'
    )
    conceptos_seleccionados: List[str] = Field(
        default=[],
        description="Lista de conceptos permitidos (solo si filtro='ESPECIFICOS')"
    )
    filtro_tipo_trabajo: str = Field(
        default='TODOS',
        description="Filtro por tipo de trabajo: TODOS | NUEVO | CAMBIO",
        pattern='^(TODOS|NUEVO|CAMBIO)$'
    )
    filtro_regional_tipo: str = Field(
        default='TODOS',
        description="Tipo de filtro de regionales: TODOS | ESPECIFICAS",
        pattern='^(TODOS|ESPECIFICAS)$'
    )
    regionales_seleccionadas: List[str] = Field(
        default=[],
        description="Lista de regionales permitidas (solo si filtro='ESPECIFICAS')"
    )
    descripcion: Optional[str] = Field(
        default=None,
        description="Descripción de la configuración"
    )
    
    @validator('conceptos_seleccionados')
    def validar_conceptos(cls, v, values):
        if values.get('filtro_conceptos_tipo') == 'ESPECIFICOS' and not v:
            raise ValueError('Debe seleccionar al menos un concepto cuando filtro es ESPECIFICOS')
        return v
    
    @validator('regionales_seleccionadas')
    def validar_regionales(cls, v, values):
        if values.get('filtro_regional_tipo') == 'ESPECIFICAS' and not v:
            raise ValueError('Debe seleccionar al menos una regional cuando filtro es ESPECIFICAS')
        return v


class ConfiguracionGlobalAvanzadaResponse(BaseModel):
    """Schema de respuesta de configuración GLOBAL"""
    id: Optional[str]
    nombre_config: str
    campo_orden: str
    direccion_orden: str
    filtro_conceptos_tipo: str
    conceptos_seleccionados: List[str]
    filtro_tipo_trabajo: str
    filtro_regional_tipo: str
    regionales_seleccionadas: List[str]
    descripcion: Optional[str]
    is_active: Optional[bool]
    updated_by: Optional[str]
    updated_at: Optional[datetime]
    configurado: bool


class ConceptoDisponible(BaseModel):
    """Schema para concepto con cantidad"""
    concepto: str
    cantidad: int


class HistorialConfiguracionResponse(BaseModel):
    """Schema de historial de cambios"""
    id: str
    accion: str
    nombre_config: str
    campo_orden: str
    direccion_orden: str
    filtro_conceptos_tipo: str
    conceptos_seleccionados: List[str]
    filtro_tipo_trabajo: str
    filtro_regional_tipo: str
    regionales_seleccionadas: List[str]
    changed_by: Optional[str]
    changed_at: datetime
    cambios_detalle: Optional[Dict[str, Any]]

