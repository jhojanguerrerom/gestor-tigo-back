from sqlalchemy import Column, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID
from app.db.base_model import Base
import uuid


# Tablas de catálogo genéricas
class Actividad(Base):
    """Tabla de catálogo: actividad"""
    __tablename__ = "actividad"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actividad = Column(Text, nullable=False)
    is_state = Column(Boolean, default=True, nullable=False)


class Aprovisionador(Base):
    """Tabla de catálogo: aprovisionador"""
    __tablename__ = "aprovisionador"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    aprovisionador = Column(Text, nullable=False)
    is_state = Column(Boolean, default=True, nullable=False)


class Barrio(Base):
    """Tabla de catálogo: barrio"""
    __tablename__ = "barrio"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    barrio = Column(Text, nullable=False)
    is_state = Column(Boolean, default=True, nullable=False)


class ConceptoAnterior(Base):
    """Tabla de catálogo: concepto_anterior"""
    __tablename__ = "concepto_anterior"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    concepto_anterior = Column(Text, nullable=False)
    is_state = Column(Boolean, default=True, nullable=False)


class ConceptoId(Base):
    """Tabla de catálogo: concepto_id"""
    __tablename__ = "concepto_id"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    concepto_id = Column(Text, nullable=False)
    is_state = Column(Boolean, default=True, nullable=False)


class ConceptoIdAnteriorNov(Base):
    """Tabla de catálogo: concepto_id_anterior_nov"""
    __tablename__ = "concepto_id_anterior_nov"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    concepto_id_anterior_nov = Column(Text, nullable=False)
    is_state = Column(Boolean, default=True, nullable=False)


class Departamento(Base):
    """Tabla de catálogo: departamento"""
    __tablename__ = "departamento"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    departamento = Column(Text, nullable=False)
    is_state = Column(Boolean, default=True, nullable=False)


class DescTipoTrabajo(Base):
    """Tabla de catálogo: desc_tipo_trabajo"""
    __tablename__ = "desc_tipo_trabajo"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    desc_tipo_trabajo = Column(Text, nullable=False)
    is_state = Column(Boolean, default=True, nullable=False)


class Fuente(Base):
    """Tabla de catálogo: fuente"""
    __tablename__ = "fuente"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fuente = Column(Text, nullable=False)
    is_state = Column(Boolean, default=True, nullable=False)


class Grupo(Base):
    """Tabla de catálogo: grupo"""
    __tablename__ = "grupo"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    grupo = Column(Text, nullable=False)
    is_state = Column(Boolean, default=True, nullable=False)


class Microzona(Base):
    """Tabla de catálogo: microzona"""
    __tablename__ = "microzona"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    microzona = Column(Text, nullable=False)
    is_state = Column(Boolean, default=True, nullable=False)


class MunicipioId(Base):
    """Tabla de catálogo: municipio_id"""
    __tablename__ = "municipio_id"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    municipio_id = Column(Text, nullable=False)
    is_state = Column(Boolean, default=True, nullable=False)


class Producto(Base):
    """Tabla de catálogo: producto"""
    __tablename__ = "producto"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    producto = Column(Text, nullable=False)
    is_state = Column(Boolean, default=True, nullable=False)


class ProductoId(Base):
    """Tabla de catálogo: producto_id"""
    __tablename__ = "producto_id"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    producto_id = Column(Text, nullable=False)
    is_state = Column(Boolean, default=True, nullable=False)


class StatusPedido(Base):
    """Tabla de catálogo: status_pedido"""
    __tablename__ = "status_pedido"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status_pedido = Column(Text, nullable=False)
    is_state = Column(Boolean, default=True, nullable=False)


class TecnologiaId(Base):
    """Tabla de catálogo: tecnologia_id"""
    __tablename__ = "tecnologia_id"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tecnologia_id = Column(Text, nullable=False)
    is_state = Column(Boolean, default=True, nullable=False)


class TipoElemento(Base):
    """Tabla de catálogo: tipo_elemento"""
    __tablename__ = "tipo_elemento"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tipo_elemento = Column(Text, nullable=False)
    is_state = Column(Boolean, default=True, nullable=False)


class TipoTrabajo(Base):
    """Tabla de catálogo: tipo_trabajo"""
    __tablename__ = "tipo_trabajo"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tipo_trabajo = Column(Text, nullable=False)
    is_state = Column(Boolean, default=True, nullable=False)


class UenCalculada(Base):
    """Tabla de catálogo: uen_calculada"""
    __tablename__ = "uen_calculada"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    uen_calculada = Column(Text, nullable=False)
    is_state = Column(Boolean, default=True, nullable=False)


class Zona(Base):
    """Tabla de catálogo: zona"""
    __tablename__ = "zona"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    zona = Column(Text, nullable=False)
    is_state = Column(Boolean, default=True, nullable=False)
