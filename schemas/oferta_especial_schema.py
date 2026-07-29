"""
Schemas para el listado de ofertas especiales.

Define los modelos de request y response para las consultas de ofertas
con conceptos especiales (PAUSADAS, MALO, RFS).
"""

from pydantic import BaseModel, Field, validator
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum


# ==========================================
# ENUMS
# ==========================================

class OrderByEnum(str, Enum):
    """Campos de ordenamiento disponibles"""
    OFERTA = "oferta"
    FECHA_PAUSA = "fecha_pausa"
    FECHA_GESTION = "fecha_gestion"


class OrderDirectionEnum(str, Enum):
    """Dirección de ordenamiento"""
    ASC = "ASC"
    DESC = "DESC"


# ==========================================
# SCHEMAS DE DATOS COMUNES
# ==========================================

class UsuarioAsignadoData(BaseModel):
    """Datos del usuario asignado"""
    login: str
    nombre: str
    profile_id: int


class UsuarioQueMarcaData(BaseModel):
    """Datos del usuario que marcó la oferta (MALO/RFS)"""
    login: str
    nombre: str
    profile_id: int


class GestionData(BaseModel):
    """Datos de la gestión realizada"""
    accion: str
    subaccion: str
    observacion: str


# ==========================================
# SCHEMAS DE ITEMS DE LISTADO
# ==========================================

class OfertaPausadaListItem(BaseModel):
    """Item de listado de oferta pausada"""
    oferta: str
    concepto_anterior: str
    estado: str
    usuario_asignado: UsuarioAsignadoData
    fecha_pausa: datetime
    tiempo_pausada_minutos: float
    pausada_por: str
    campos_oferta: Dict[str, Any]


class OfertaMaloListItem(BaseModel):
    """Item de listado de oferta MALO"""
    oferta: str
    concepto: str
    concepto_anterior: str
    estado: str
    usuario_que_marco: UsuarioQueMarcaData
    fecha_gestion: datetime
    dias_cerrada: int
    gestion: GestionData
    campos_oferta: Dict[str, Any]


class OfertaRfsListItem(BaseModel):
    """Item de listado de oferta RFS"""
    oferta: str
    concepto: str
    concepto_anterior: str
    estado: str
    usuario_que_marco: UsuarioQueMarcaData
    fecha_gestion: datetime
    dias_cerrada: int
    gestion: GestionData
    campos_oferta: Dict[str, Any]


# ==========================================
# RESPONSES DE LISTADO
# ==========================================

class OfertasPausadasListResponse(BaseModel):
    """Response para listado de ofertas pausadas"""
    total: int = Field(description="Total de ofertas pausadas")
    limit: int = Field(description="Límite de registros")
    offset: int = Field(description="Desplazamiento aplicado")
    data: List[OfertaPausadaListItem]


class OfertasMaloListResponse(BaseModel):
    """Response para listado de ofertas MALO"""
    total: int = Field(description="Total de ofertas MALO")
    limit: int = Field(description="Límite de registros")
    offset: int = Field(description="Desplazamiento aplicado")
    data: List[OfertaMaloListItem]


class OfertasRfsListResponse(BaseModel):
    """Response para listado de ofertas RFS"""
    total: int = Field(description="Total de ofertas RFS")
    limit: int = Field(description="Límite de registros")
    offset: int = Field(description="Desplazamiento aplicado")
    data: List[OfertaRfsListItem]


# ==========================================
# RESPONSE DE RESUMEN DASHBOARD
# ==========================================

class ConceptoEspecialResumen(BaseModel):
    """Resumen de un concepto especial"""
    total: int
    tipo: str
    estado: str


class OfertasEspecialesResumenResponse(BaseModel):
    """Response para resumen consolidado de ofertas especiales"""
    pausadas: ConceptoEspecialResumen
    malo: ConceptoEspecialResumen
    rfs: ConceptoEspecialResumen
    total_general: int = Field(description="Total general de todas las ofertas especiales")


# ==========================================
# ERROR RESPONSE
# ==========================================

class ErrorResponse(BaseModel):
    """Response genérico de error"""
    detail: str

