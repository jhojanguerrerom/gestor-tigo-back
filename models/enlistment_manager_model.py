from sqlalchemy import Column, String, DateTime, Integer, Float, Text, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from app.db.base_model import Base
from app.db.timezone_types import BogotaDateTime
import uuid
import enum


class EstadoCarga(str, enum.Enum):
    """Estados posibles para el control de carga"""
    EN_PROCESO = "EN_PROCESO"
    COMPLETADO = "COMPLETADO"
    ERROR = "ERROR"


class TipoOperacion(str, enum.Enum):
    """Tipos de operación para el histórico"""
    INSERT = "INSERT"
    UPDATE = "UPDATE"


class EnlistmentManager(Base):
    """
    Modelo para la tabla enlistment_manager.
    Almacena los datos actuales del DataFrame fusionado (Siebel + Fenix + Items).
    Utiliza JSONB para almacenar campos dinámicos sin requerir ALTER TABLE en el futuro.
    """
    __tablename__ = "enlistment_manager"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Identificadores
    ticket_carga = Column(String(100), nullable=False, index=True, comment="Identificador único de la ejecución de carga")
    oferta = Column(Text, nullable=False, unique=True, index=True, comment="Número de oferta - Clave natural única")
    
    # Hash para detección de cambios
    hash_registro = Column(String(64), nullable=False, index=True, comment="Hash SHA256 del contenido completo del registro")
    
    # Almacenamiento dinámico de todos los campos del DataFrame
    campos_dinamicos = Column(JSONB, nullable=False, comment="Todos los campos del DataFrame en formato JSONB")
    
    # Control de estado de oferta
    estado_oferta = Column(
        String(50), 
        nullable=False, 
        default='ABIERTO', 
        index=True,
        comment="Estado de la oferta: ABIERTO, EN_TRAMITE, CERRADO, CERRADO_AUTOMATICO"
    )
    contador_cargas_ausente = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Contador de cargas consecutivas donde la oferta no ha aparecido"
    )
    contador_cargas_reapertura = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Contador de cargas consecutivas donde oferta CERRADA vuelve a aparecer (para reapertura gradual)"
    )
    
    # Gestión de asignación de ofertas
    usuario_asignado_login = Column(
        Text,
        nullable=True,
        index=True,
        comment="Login del usuario que tiene asignada la oferta"
    )
    usuario_asignado_nombre = Column(
        Text,
        nullable=True,
        comment="Nombre completo del usuario asignado"
    )
    usuario_asignado_profile_id = Column(
        Integer,
        nullable=True,
        comment="Profile ID del usuario asignado"
    )
    fecha_asignacion = Column(
        BogotaDateTime,
        nullable=True,
        index=True,
        comment="Fecha y hora en que se asignó la oferta (America/Bogota)"
    )
    fecha_gestion = Column(
        BogotaDateTime,
        nullable=True,
        comment="Fecha y hora en que se gestionó/cerró la oferta (America/Bogota)"
    )
    
    # Auditoría
    created_at = Column(BogotaDateTime, server_default=func.now(), nullable=False)
    updated_at = Column(BogotaDateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<EnlistmentManager(oferta='{self.oferta}', ticket='{self.ticket_carga}')>"


class EnlistmentManagerHistory(Base):
    """
    Modelo para la tabla enlistment_manager_history.
    Almacena el histórico de cambios detectados (INSERT y UPDATE).
    Solo se registran los cambios, no todos los registros en cada carga.
    """
    __tablename__ = "enlistment_manager_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Relación con la tabla principal (sin FK física para performance)
    fk_enlistment_manager_id = Column(UUID(as_uuid=True), index=True, comment="ID del registro en enlistment_manager")
    
    # Identificadores
    ticket_carga = Column(String(100), nullable=False, index=True, comment="Ticket de la carga que generó este cambio")
    create_date_automation = Column(BogotaDateTime, nullable=False, index=True, comment="Fecha de la carga automática (America/Bogota)")
    oferta = Column(Text, nullable=False, index=True, comment="Número de oferta")
    
    # Hash y tipo de operación
    hash_registro = Column(String(64), nullable=False, comment="Hash del registro en el momento del cambio")
    tipo_operacion = Column(SQLEnum(TipoOperacion, native_enum=False), nullable=False, index=True, comment="Tipo de operación: INSERT o UPDATE")
    
    # Datos
    campos_dinamicos = Column(JSONB, nullable=False, comment="Snapshot completo de los campos en el momento del cambio")
    campos_modificados = Column(JSONB, nullable=True, comment="Solo los campos que cambiaron (para UPDATE)")
    
    # Estado de la oferta en el momento del cambio
    estado_oferta = Column(
        String(50), 
        nullable=False,
        index=True,
        comment="Estado de la oferta en el momento del cambio"
    )
    
    # Auditoría
    created_at = Column(BogotaDateTime, server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<EnlistmentManagerHistory(oferta='{self.oferta}', tipo='{self.tipo_operacion}', ticket='{self.ticket_carga}')>"


class EnlistmentManagerControl(Base):
    """
    Modelo para la tabla enlistment_manager_control.
    Almacena información de control de cada ejecución de carga.
    Permite monitorear performance, errores y estadísticas.
    """
    __tablename__ = "enlistment_manager_control"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Identificador único de la carga
    ticket_carga = Column(String(100), nullable=False, unique=True, index=True, comment="Identificador único de esta ejecución")
    create_date_automation = Column(BogotaDateTime, nullable=False, index=True, comment="Fecha y hora de inicio de la carga (America/Bogota)")
    
    # Estadísticas de procesamiento
    total_registros_procesados = Column(Integer, nullable=False, default=0, comment="Total de registros recibidos")
    total_registros_nuevos = Column(Integer, nullable=False, default=0, comment="Registros insertados (nuevos)")
    total_registros_actualizados = Column(Integer, nullable=False, default=0, comment="Registros actualizados (modificados)")
    total_registros_sin_cambios = Column(Integer, nullable=False, default=0, comment="Registros sin cambios")
    
    # Performance
    tiempo_ejecucion_segundos = Column(Float, nullable=True, comment="Tiempo total de ejecución en segundos")
    
    # Estado y errores
    estado = Column(SQLEnum(EstadoCarga, native_enum=False), nullable=False, default=EstadoCarga.EN_PROCESO, index=True, comment="Estado de la ejecución")
    mensaje_error = Column(Text, nullable=True, comment="Mensaje de error si el estado es ERROR")
    
    # Metadata
    columnas_detectadas = Column(JSONB, nullable=True, comment="Lista de columnas detectadas en el DataFrame")
    
    # Auditoría
    created_at = Column(BogotaDateTime, server_default=func.now(), nullable=False)
    updated_at = Column(BogotaDateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<EnlistmentManagerControl(ticket='{self.ticket_carga}', estado='{self.estado}', procesados={self.total_registros_procesados})>"
