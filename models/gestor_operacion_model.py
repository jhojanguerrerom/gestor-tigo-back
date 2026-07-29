from sqlalchemy import Column, String, DateTime, Integer, Boolean, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID
from app.db.base_model import Base
import uuid


class GestorOperacion(Base):
    """
    Modelo para la tabla gestor_operacion en PostgreSQL.
    Almacena información de pedidos provenientes de Fenix y Siebel.
    """
    __tablename__ = "gestor_operacion"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Identificadores del pedido
    pedido = Column(Text)
    pedido_id = Column(Text)
    pedido_fenix = Column(Text)
    subpedido_id = Column(Text)
    solicitud_id = Column(Text)
    
    # IDs de claves foráneas (referencias a tablas de catálogo - UUID)
    fk_tipo_elemento_id = Column(UUID(as_uuid=True))
    fk_tipo_trabajo = Column(UUID(as_uuid=True))
    fk_desc_tipo_trabajo = Column(UUID(as_uuid=True))
    fk_producto = Column(UUID(as_uuid=True))
    fk_producto_id = Column(UUID(as_uuid=True))
    fk_uen_calculada = Column(UUID(as_uuid=True))
    fk_concepto_id = Column(UUID(as_uuid=True))
    fk_concepto_anterior = Column(UUID(as_uuid=True))
    fk_municipio_id = Column(UUID(as_uuid=True))
    fk_zona = Column(UUID(as_uuid=True))
    fk_departamento = Column(UUID(as_uuid=True))
    fk_microzona = Column(UUID(as_uuid=True))
    fk_barrio = Column(UUID(as_uuid=True))
    fk_fuente = Column(UUID(as_uuid=True))
    fk_actividad = Column(UUID(as_uuid=True))
    fk_grupo = Column(UUID(as_uuid=True))
    fk_tecnologia_id = Column(UUID(as_uuid=True))
    fk_concepto_id_anterior_nov = Column(UUID(as_uuid=True))
    fk_aprovisionador = Column(UUID(as_uuid=True))
    fk_status_pedido = Column(UUID(as_uuid=True))
    
    # Campos de texto
    estado_bloqueo = Column(Text)
    # usuario_bloqueo_fenix = Column(Text)
    estrato = Column(Text)
    direccion_servicio = Column(Text)
    pagina_servicio = Column(Text)
    identificador_id = Column(Text)
    vel_iden = Column(Text)
    vel_soli = Column(Text)
    cliente_id = Column(Text)
    pedido_crm = Column(Text)
    
    # Campos adicionales del SQL
    estado_gis = Column(Text)
    concepto_anterior_oculto = Column(Text)
    id_gis = Column(Text)
    canal = Column(Text)
    asesor = Column(Text)
    programacion = Column(Text)
    cantidad_equ = Column(Integer)
    nombre_cliente = Column(Text)
    celular_avisar = Column(Text)
    telefono_avisar = Column(Text)
    up2date = Column(Text)
    robot = Column(Boolean)
    observaciones = Column(Text)
    views = Column(Integer)
    latitude = Column(Numeric(10, 8))
    longitude = Column(Numeric(10, 8))
    
    # Fechas
    fecha_ingreso = Column(DateTime)
    fecha_estado = Column(DateTime)
    fecha_cita = Column(Text)  # En el SQL es text
    hora_cita = Column(Text)
    fecha_carga = Column(DateTime)
    fecha_visto_asesor = Column(DateTime)
    fecha_final = Column(DateTime)

    def __repr__(self):
        return f"<GestorOperacion(id={self.id}, pedido={self.pedido})>"
