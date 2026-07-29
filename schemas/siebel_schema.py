from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class SiebelBase(BaseModel):
    """Schema base para Siebel"""
    oferta: str
    estado_oferta: str
    fecha_creado: datetime
    row_id: str
    rev_num: int
    fecha_estado: datetime
    estado_estudio_legal: Optional[str] = None
    descripcion: Optional[str] = None
    concepto: str
    estado_pendiente: Optional[str] = None
    fecha_pendiente: Optional[datetime] = None
    comentario: Optional[str] = None
    disponibilidad: Optional[str] = None
    tipo_scoring: Optional[str] = None
    estado_scoring: Optional[str] = None
    usuario_pendiente: Optional[str] = None
    usuario: Optional[str] = None
    canal: Optional[str] = None
    documento: Optional[int] = None
    regional: Optional[str] = None
    departamento: Optional[str] = None
    municipio: Optional[str] = None
    direccion: Optional[str] = None
    estado_direccion: Optional[str] = None
    tipo_transaccion_internet: Optional[str] = None
    tipo_transaccion_television: Optional[str] = None
    tipo_transaccion_telefonia: Optional[str] = None