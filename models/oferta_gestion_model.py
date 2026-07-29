from sqlalchemy import Column, String, DateTime, Integer, Boolean, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.db.base_model import Base
from app.db.timezone_types import BogotaDateTime
import uuid


class OfertaAccionCatalogo(Base):
    """
    Catálogo de acciones disponibles para gestión de ofertas.
    Ejemplo: Asignado, Cancelado, Reconfigurar.
    """
    __tablename__ = "oferta_accion_catalogo"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nombre_accion = Column(String(100), nullable=False, unique=True, index=True, comment="Nombre de la acción")
    descripcion = Column(Text, nullable=True, comment="Descripción opcional de la acción")
    is_active = Column(Boolean, nullable=False, default=True, index=True, comment="Estado activo/inactivo")
    orden = Column(Integer, nullable=False, default=0, comment="Orden de visualización")
    created_at = Column(BogotaDateTime, server_default=func.now(), nullable=False)
    updated_at = Column(BogotaDateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<OfertaAccionCatalogo(nombre='{self.nombre_accion}', active={self.is_active})>"


class OfertaSubaccionCatalogo(Base):
    """
    Catálogo de subacciones asociadas a cada acción.
    Ejemplo: Para 'Asignado' -> 'Se busca elemento con red libre'.
    """
    __tablename__ = "oferta_subaccion_catalogo"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    accion_id = Column(UUID(as_uuid=True), ForeignKey('oferta_accion_catalogo.id'), nullable=False, index=True, comment="Referencia a la acción padre")
    nombre_subaccion = Column(Text, nullable=False, comment="Nombre de la subacción")
    is_active = Column(Boolean, nullable=False, default=True, index=True, comment="Estado activo/inactivo")
    orden = Column(Integer, nullable=False, default=0, comment="Orden de visualización")
    created_at = Column(BogotaDateTime, server_default=func.now(), nullable=False)
    updated_at = Column(BogotaDateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<OfertaSubaccionCatalogo(nombre='{self.nombre_subaccion}', accion_id='{self.accion_id}')>"


class OfertaGestionDetalle(Base):
    """
    Almacena el detalle de la gestión realizada por el asesor al cerrar una oferta.
    Incluye: acción, subacción y observación.
    """
    __tablename__ = "oferta_gestion_detalle"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    oferta = Column(Text, nullable=False, index=True, comment="Número de oferta gestionada")
    accion_id = Column(UUID(as_uuid=True), ForeignKey('oferta_accion_catalogo.id'), nullable=False, index=True, comment="Acción seleccionada")
    subaccion_id = Column(UUID(as_uuid=True), ForeignKey('oferta_subaccion_catalogo.id'), nullable=False, index=True, comment="Subacción seleccionada")
    observacion = Column(Text, nullable=True, comment="Observaciones del asesor")
    usuario_login = Column(Text, nullable=False, index=True, comment="Login del usuario que gestionó")
    usuario_nombre = Column(Text, nullable=False, comment="Nombre completo del usuario")
    usuario_profile_id = Column(Integer, nullable=False, comment="Profile ID del usuario")
    fecha_gestion = Column(BogotaDateTime, nullable=False, server_default=func.now(), index=True, comment="Fecha y hora de la gestión (America/Bogota)")
    created_at = Column(BogotaDateTime, server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<OfertaGestionDetalle(oferta='{self.oferta}', usuario='{self.usuario_login}')>"


class OfertaHistoricoEstados(Base):
    """
    Almacena el histórico completo de cambios de estado de ofertas.
    Registra: CONGELAR, DESCONGELAR, REASIGNAR, GESTIONAR.
    """
    __tablename__ = "oferta_historico_estados"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    oferta = Column(Text, nullable=False, index=True, comment="Número de oferta")
    accion_sistema = Column(String(50), nullable=False, index=True, comment="CONGELAR, DESCONGELAR, REASIGNAR, GESTIONAR")
    estado_anterior = Column(String(50), nullable=False, comment="Estado previo de la oferta")
    estado_nuevo = Column(String(50), nullable=False, comment="Estado nuevo de la oferta")
    usuario_login = Column(Text, nullable=False, index=True, comment="Usuario que ejecutó la acción")
    usuario_nombre = Column(Text, nullable=False, comment="Nombre completo del usuario")
    usuario_profile_id = Column(Integer, nullable=False, comment="Profile ID del usuario")
    asesor_asignado_login = Column(Text, nullable=True, comment="Login del asesor asignado (para reasignaciones)")
    asesor_asignado_nombre = Column(Text, nullable=True, comment="Nombre del asesor asignado")
    motivo = Column(Text, nullable=True, comment="Motivo de la acción (opcional)")
    ip_address = Column(String(50), nullable=True, comment="Dirección IP del usuario")
    fecha_accion = Column(BogotaDateTime, nullable=False, server_default=func.now(), index=True, comment="Fecha y hora de la acción (America/Bogota)")
    created_at = Column(BogotaDateTime, server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<OfertaHistoricoEstados(oferta='{self.oferta}', accion='{self.accion_sistema}')>"


class OfertaConfiguracion(Base):
    """
    Configuración de orden de búsqueda de ofertas por perfil de usuario.
    ASC = más antigua primero, DESC = más reciente primero.
    """
    __tablename__ = "oferta_configuracion"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id = Column(Integer, nullable=False, unique=True, index=True, comment="ID del perfil de usuario")
    orden_busqueda = Column(String(4), nullable=False, default='ASC', comment="ASC o DESC")
    descripcion = Column(Text, nullable=True, comment="Descripción del perfil")
    is_active = Column(Boolean, nullable=False, default=True, comment="Estado de la configuración")
    updated_by = Column(Text, nullable=True, comment="Usuario que actualizó la configuración")
    created_at = Column(BogotaDateTime, server_default=func.now(), nullable=False)
    updated_at = Column(BogotaDateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<OfertaConfiguracion(profile_id={self.profile_id}, orden='{self.orden_busqueda}')>"


class OfertaConfiguracionPausada(Base):
    """
    Configuración global para el manejo de ofertas pausadas.
    Define el tiempo mínimo antes de pausar y la cantidad máxima de ofertas pausadas por asesor.
    """
    __tablename__ = "oferta_configuracion_pausada"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tiempo_minimo_pausa_minutos = Column(Integer, nullable=False, default=7, comment="Tiempo mínimo en minutos antes de poder pausar una oferta")
    max_ofertas_pausadas_por_asesor = Column(Integer, nullable=False, default=3, comment="Cantidad máxima de ofertas que un asesor puede tener pausadas simultáneamente")
    is_active = Column(Boolean, nullable=False, default=True, index=True, comment="Estado activo/inactivo")
    updated_by = Column(String(100), nullable=True, comment="Usuario que realizó la última actualización")
    created_at = Column(BogotaDateTime, server_default=func.now(), nullable=False)
    updated_at = Column(BogotaDateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<OfertaConfiguracionPausada(tiempo_min={self.tiempo_minimo_pausa_minutos}, max_ofertas={self.max_ofertas_pausadas_por_asesor})>"


class OfertaPausadaTracking(Base):
    """
    Registro histórico de ofertas pausadas.
    Registra cuándo se pausa una oferta, quién la pausó, cuándo se reanudó y quién la reanudó.
    Permite trazabilidad completa de las pausas de ofertas.
    """
    __tablename__ = "oferta_pausada_tracking"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    oferta = Column(Text, nullable=False, index=True, comment="Número de oferta pausada")
    usuario_login = Column(Text, nullable=False, index=True, comment="Login del usuario que tiene la oferta pausada")
    concepto_anterior = Column(String(255), nullable=True, comment="Concepto que tenía la oferta antes de ser pausada")
    fecha_pausa = Column(BogotaDateTime, nullable=False, index=True, comment="Fecha y hora en que se pausó la oferta")
    fecha_reanudacion = Column(BogotaDateTime, nullable=True, comment="Fecha y hora en que se reanudó la oferta")
    pausada_por = Column(String(100), nullable=True, comment="Tipo de usuario que pausó: asesor")
    reanudada_por = Column(String(100), nullable=True, comment="Login del usuario que reanudó la oferta")
    tipo_reanudacion = Column(String(50), nullable=True, comment="Tipo de reanudación: manual_asesor, liberada_supervisor, liberada_superuser")
    motivo_liberacion = Column(Text, nullable=True, comment="Motivo de liberación por parte de supervisor/superuser")
    created_at = Column(BogotaDateTime, server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<OfertaPausadaTracking(oferta='{self.oferta}', usuario='{self.usuario_login}', pausada={self.fecha_pausa})>"


class OfertaConfiguracionAvanzada(Base):
    """
    Configuración GLOBAL de búsqueda y filtrado de ofertas.
    Un único registro activo que aplica a TODOS los usuarios/perfiles.
    """
    __tablename__ = "oferta_configuracion_avanzada"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Ordenamiento
    campo_orden = Column(String(50), nullable=False, default='created_at',
                        comment="Campo para ordenar: created_at | fecha_creado")
    direccion_orden = Column(String(4), nullable=False, default='ASC',
                            comment="Dirección: ASC | DESC")
    
    # Filtro conceptos
    filtro_conceptos_tipo = Column(String(20), nullable=False, default='TODOS',
                                   comment="Tipo filtro: TODOS | ESPECIFICOS")
    conceptos_seleccionados = Column(Text, default='[]',
                                     comment="JSON Array de conceptos permitidos")
    
    # Filtro tipo trabajo
    filtro_tipo_trabajo = Column(String(20), nullable=False, default='TODOS',
                                 comment="Filtro: TODOS | NUEVO | CAMBIO")
    
    # Filtro regional
    filtro_regional_tipo = Column(String(20), nullable=False, default='TODOS',
                                  comment="Tipo filtro: TODOS | ESPECIFICAS")
    regionales_seleccionadas = Column(Text, default='[]',
                                      comment="JSON Array de regionales permitidas")
    
    # Metadata
    nombre_config = Column(String(100), default='Configuración Global')
    descripcion = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    updated_by = Column(String(100), nullable=True)
    created_at = Column(BogotaDateTime, server_default=func.now(), nullable=False)
    updated_at = Column(BogotaDateTime, server_default=func.now(), 
                       onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<OfertaConfiguracionAvanzada(nombre='{self.nombre_config}', activo={self.is_active})>"


class OfertaConfiguracionAvanzadaHistory(Base):
    """Historial de cambios en configuración GLOBAL de ofertas"""
    __tablename__ = "oferta_configuracion_avanzada_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    configuracion_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Snapshot de configuración
    nombre_config = Column(String(100))
    campo_orden = Column(String(50), nullable=False)
    direccion_orden = Column(String(4), nullable=False)
    filtro_conceptos_tipo = Column(String(20), nullable=False)
    conceptos_seleccionados = Column(Text)
    filtro_tipo_trabajo = Column(String(20), nullable=False)
    filtro_regional_tipo = Column(String(20), nullable=False)
    regionales_seleccionadas = Column(Text)
    descripcion = Column(Text)
    
    # Auditoría
    accion = Column(String(20), nullable=False)  # CREATE, UPDATE, ACTIVATE, DEACTIVATE
    changed_by = Column(String(100), nullable=True)
    changed_at = Column(BogotaDateTime, server_default=func.now(), 
                       nullable=False, index=True)
    cambios_detalle = Column(Text, nullable=True, 
                            comment="JSON con detalle de campos modificados")
    ip_address = Column(String(45), nullable=True)

    def __repr__(self):
        return f"<ConfigHistory(accion={self.accion}, changed_at={self.changed_at})>"
