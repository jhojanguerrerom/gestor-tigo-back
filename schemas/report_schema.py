"""
Schemas para el módulo de reportería.
Incluye request y response para todos los reportes.
"""

from pydantic import BaseModel, Field, validator
from typing import Dict, List, Optional
from datetime import date, datetime
from enum import Enum


# ==========================================
# ENUMS
# ==========================================

class DataTypeEnum(str, Enum):
    """Tipos de datos para reportes"""
    INCOME = "INCOME"
    MANAGED = "MANAGED"
    BOTH = "BOTH"


class BusinessUnitEnum(str, Enum):
    """Unidades de negocio"""
    RESIDENCIAL = "RESIDENCIAL"
    EMPRESARIAL = "EMPRESARIAL"
    ALL = "ALL"


class DateFieldEnum(str, Enum):
    """Campo de fecha a usar en filtros"""
    CRM = "CRM"
    GESTOR = "GESTOR"


class ExportFormatEnum(str, Enum):
    """Formatos de exportación"""
    JSON = "JSON"
    CSV = "CSV"


class ConceptGroupEnum(str, Enum):
    """Agrupación de conceptos por categoría funcional"""
    ANULAR = "ANULAR"                    # ANULA, ANULA-C, ANULA-D
    RECONFIGURACION = "RECONFIGURACION"  # Premisas Extendidas, 14, RECONFIGURACION BOT
    ASIGNACION = "ASIGNACION"            # Cobertura, Conservar Numero, PETEC, PRESI, PSIEB, PUMED, etc.
    ALL = "ALL"                          # Sin filtro


# ==========================================
# REPORTE 1: Gestiones por Hora/Asesor
# ==========================================

class HourManagedData(BaseModel):
    """Datos de gestiones por hora para un asesor"""
    user_login: str
    user_name: str
    hours: Dict[str, int]  # {"6": 2, "7": 5, ...}
    total_user: int
    passed_to_order: int
    effectiveness_percentage: float
    average_ratio: Optional[float]


class ManagedByHourResponse(BaseModel):
    """Response para reporte de gestiones por hora"""
    date: date
    total_offers: int
    data: List[HourManagedData]


# ==========================================
# REPORTE 2: Productividad Diaria
# ==========================================

class ManagedByDay(BaseModel):
    """Gestiones de un día específico"""
    date: date
    quantity: int


class AdvisorProductivityData(BaseModel):
    """Productividad de un asesor"""
    user_login: str
    user_name: str
    user_profile_id: int
    total_managed: int
    daily_average: float
    managed_by_day: List[ManagedByDay]


class DailyProductivityResponse(BaseModel):
    """Response para reporte de productividad diaria"""
    date_from: date
    date_to: date
    total_managed: int
    data: List[AdvisorProductivityData]


# ==========================================
# REPORTE 3: Histórico Ingresos vs Gestiones
# ==========================================

class IncomeVsManagedDay(BaseModel):
    """Datos de un día: ingresos vs gestiones"""
    date: date
    income: int
    managed: int


class HistoricalIncomeVsManagedResponse(BaseModel):
    """Response para histórico comparativo"""
    business_unit: str
    date_from: date
    date_to: date
    total_income: int
    total_managed: int
    data: List[IncomeVsManagedDay]


# ==========================================
# REPORTE 4: Ingresos por Hora
# ==========================================

class IncomeByHourData(BaseModel):
    """Ingresos en una hora específica"""
    hour: int
    quantity: float  # Puede ser promedio (decimal) o conteo real


class IncomeByHourResponse(BaseModel):
    """Response para ingresos por intervalo de hora"""
    date_from: date
    date_to: date
    is_average: bool = Field(
        description="True si es promedio de múltiples días, False si es conteo de un solo día"
    )
    total_income: float
    data: List[IncomeByHourData]


# ==========================================
# REPORTE 5: Ingresos y Gestiones Diario
# ==========================================

class DailyIncomeManagedData(BaseModel):
    """Datos diarios de ingresos y/o gestiones"""
    date: date
    income: Optional[int] = None
    managed: Optional[int] = None


class DailyIncomeManagedResponse(BaseModel):
    """Response para comparación diaria"""
    data_type: str
    date_from: date
    date_to: date
    data: List[DailyIncomeManagedData]


# ==========================================
# REPORTE 6: Ingresos por Concepto
# ==========================================

class IncomeByConceptData(BaseModel):
    """Ingresos por concepto en un día"""
    date: date
    concepts: Dict[str, int]  # {"ALTA": 15, "BAJA": 8}


class IncomeByConceptResponse(BaseModel):
    """Response para ingresos por concepto"""
    month: str
    concept_filter: Optional[str]
    total_income: int
    available_concepts: List[str]
    data: List[IncomeByConceptData]


# ==========================================
# REPORTE 7: Ofertas Disponibles por Concepto
# ==========================================

class IntervalData(BaseModel):
    """Datos de intervalos de tiempo"""
    interval_0_30m: int = Field(0, alias="0_30m")
    interval_31_60m: int = Field(0, alias="31_60m")
    interval_1_2h: int = Field(0, alias="1_2h")
    interval_3_5h: int = Field(0, alias="3_5h")
    interval_5_7h: int = Field(0, alias="5_7h")
    interval_7_12h: int = Field(0, alias="7_12h")
    interval_12_24h: int = Field(0, alias="12_24h")
    interval_24_48h: int = Field(0, alias="24_48h")
    interval_more_48h: int = Field(0, alias="more_48h")
    
    class Config:
        populate_by_name = True


class ConceptIntervalData(BaseModel):
    """Datos de un concepto con sus intervalos"""
    concept: str
    total: int
    intervals: IntervalData


class AvailableOffersByConceptResponse(BaseModel):
    """Response para reporte de ofertas disponibles por concepto"""
    date_field: str
    date_from: Optional[date]
    date_to: Optional[date]
    total_offers: int
    data: List[ConceptIntervalData]
    totals: ConceptIntervalData


# ==========================================
# REPORTE 9: Liquidación
# ==========================================

class LiquidationData(BaseModel):
    """Datos de liquidación de una oferta"""
    oferta: str
    usuario_login: str
    usuario_nombre: str
    concepto: Optional[str]
    producto: Optional[str]
    uen: Optional[str]
    regional: Optional[str]
    documento: Optional[str]
    pedido_id: Optional[str]
    tecnologia: Optional[str]
    garantia: Optional[str]
    departamento: Optional[str]
    tipo_scoring: Optional[str]
    tipo_trabajo: Optional[str]
    fecha_creado: Optional[str]
    descripcion: Optional[str]
    direccion: Optional[str]
    latitud: Optional[str]
    longitud: Optional[str]
    estado_direccion: Optional[str]
    estado_oferta: str
    estado_pendiente: Optional[str]
    estado_scoring: Optional[str]
    fecha_estado: Optional[str]
    fecha_pendiente: Optional[str]
    megagold: Optional[str]
    municipio: Optional[str]
    pedido_crm: Optional[str]
    usuario_pendiente: Optional[str]
    fecha_ingreso_gestor: Optional[str]
    fecha_asignacion: datetime
    fecha_gestion: datetime
    nombre_accion: Optional[str]
    nombre_subaccion: Optional[str]
    observacion: Optional[str]
    validacion_garantia: str


class LiquidationResponse(BaseModel):
    """Response para reporte de liquidación"""
    date_from: date
    date_to: date
    total_records: int
    page: int
    page_size: int
    total_pages: int
    data: List[LiquidationData]


# ==========================================
# SCHEMAS GENÉRICOS
# ==========================================

class ErrorResponse(BaseModel):
    """Response genérico de error"""
    error: bool = True
    message: str
    detail: Optional[str] = None

