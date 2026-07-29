from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID


class GestorOperacionBase(BaseModel):
    """Schema base para GestorOperacion"""
    pedido: str
    pedido_id: Optional[str] = None
    pedido_fenix: Optional[str] = None
    subpedido_id: Optional[str] = None
    solicitud_id: Optional[str] = None

    # IDs de claves foráneas (UUID)
    fk_tipo_elemento_id: Optional[UUID] = None
    fk_tipo_trabajo: Optional[UUID] = None
    fk_desc_tipo_trabajo: Optional[UUID] = None
    fk_producto: Optional[UUID] = None
    fk_producto_id: Optional[UUID] = None
    fk_uen_calculada: Optional[UUID] = None
    fk_concepto_id: Optional[UUID] = None
    fk_concepto_anterior: Optional[UUID] = None
    fk_municipio_id: Optional[UUID] = None
    fk_zona: Optional[UUID] = None
    fk_departamento: Optional[UUID] = None
    fk_microzona: Optional[UUID] = None
    fk_barrio: Optional[UUID] = None
    fk_fuente: Optional[UUID] = None
    fk_actividad: Optional[UUID] = None
    fk_grupo: Optional[UUID] = None
    fk_tecnologia_id: Optional[UUID] = None
    fk_concepto_id_anterior_nov: Optional[UUID] = None
    fk_aprovisionador: Optional[UUID] = None
    fk_status_pedido: Optional[UUID] = None

    # Campos de texto
    estado_bloqueo: Optional[str] = None
    usuario_bloqueo_fenix: Optional[str] = None
    estrato: Optional[str] = None
    direccion_servicio: Optional[str] = None
    pagina_servicio: Optional[str] = None
    identificador_id: Optional[str] = None
    vel_iden: Optional[str] = None
    vel_soli: Optional[str] = None
    cliente_id: Optional[str] = None
    pedido_crm: Optional[str] = None

    # Campos adicionales
    estado_gis: Optional[str] = None
    concepto_anterior_oculto: Optional[str] = None
    id_gis: Optional[str] = None
    canal: Optional[str] = None
    asesor: Optional[str] = None
    programacion: Optional[str] = None
    cantidad_equ: Optional[int] = None
    nombre_cliente: Optional[str] = None
    celular_avisar: Optional[str] = None
    telefono_avisar: Optional[str] = None
    up2date: Optional[str] = None
    robot: Optional[bool] = None
    observaciones: Optional[str] = None
    views: Optional[int] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    # Fechas
    fecha_ingreso: Optional[datetime] = None
    fecha_estado: Optional[datetime] = None
    fecha_cita: Optional[str] = None
    hora_cita: Optional[str] = None
    fecha_carga: Optional[datetime] = None
    fecha_visto_asesor: Optional[datetime] = None
    fecha_final: Optional[datetime] = None


class GestorOperacionCreate(GestorOperacionBase):
    """Schema para crear un registro de GestorOperacion"""
    pass


class GestorOperacionUpdate(BaseModel):
    """Schema para actualizar un registro de GestorOperacion"""
    # Todos los campos opcionales para permitir actualizaciones parciales
    fk_tipo_elemento_id: Optional[UUID] = None
    fk_tipo_trabajo: Optional[UUID] = None
    fk_desc_tipo_trabajo: Optional[UUID] = None
    fk_producto: Optional[UUID] = None
    fk_producto_id: Optional[UUID] = None
    fk_uen_calculada: Optional[UUID] = None
    fk_concepto_id: Optional[UUID] = None
    fk_concepto_anterior: Optional[UUID] = None
    fk_municipio_id: Optional[UUID] = None
    fk_zona: Optional[UUID] = None
    fk_departamento: Optional[UUID] = None
    fk_microzona: Optional[UUID] = None
    fk_barrio: Optional[UUID] = None
    fk_fuente: Optional[UUID] = None
    fk_actividad: Optional[UUID] = None
    fk_grupo: Optional[UUID] = None
    fk_tecnologia_id: Optional[UUID] = None
    fk_concepto_id_anterior_nov: Optional[UUID] = None
    fk_aprovisionador: Optional[UUID] = None
    fk_status_pedido: Optional[UUID] = None
    estado_bloqueo: Optional[str] = None
    usuario_bloqueo_fenix: Optional[str] = None
    estrato: Optional[str] = None
    direccion_servicio: Optional[str] = None
    pagina_servicio: Optional[str] = None
    identificador_id: Optional[str] = None
    vel_iden: Optional[str] = None
    vel_soli: Optional[str] = None
    cliente_id: Optional[str] = None
    pedido_crm: Optional[str] = None
    fecha_ingreso: Optional[datetime] = None
    fecha_estado: Optional[datetime] = None
    fecha_cita: Optional[str] = None


class GestorOperacionResponse(GestorOperacionBase):
    """Schema para respuesta de GestorOperacion"""
    id: UUID

    class Config:
        from_attributes = True


class AutomationResponse(BaseModel):
    """Schema genérico para respuestas de automation"""
    type: str
    msg: str


class DataFenixResponse(BaseModel):
    """Schema para respuesta de datos de Fenix"""
    type: str
    msg: list

    class Config:
        from_attributes = True


class DataSiebelResponse(BaseModel):
    """Schema para respuesta de datos de Siebel"""
    type: str
    msg: list

    class Config:
        from_attributes = True


class DataProcessResponse(BaseModel):
    """Schema para respuesta de datos de process"""
    type: str
    msg: str

    class Config:
        from_attributes = True
