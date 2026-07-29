"""
Tipos personalizados de SQLAlchemy para manejo consistente de timezone.
Todas las fechas se almacenan en UTC en la BD pero se devuelven en America/Bogota.
"""
from sqlalchemy import DateTime as SADateTime, TypeDecorator
from datetime import datetime
import pytz

# Timezone de Colombia
BOGOTA_TZ = pytz.timezone('America/Bogota')
UTC_TZ = pytz.UTC


class BogotaDateTime(TypeDecorator):
    """
    Tipo personalizado para DateTime que siempre devuelve fechas en timezone de Bogotá.
    
    Comportamiento:
    - Al GUARDAR: Acepta fechas con timezone (convierte a UTC) o sin timezone (asume UTC)
    - Al LEER: Siempre convierte de UTC a America/Bogota
    - PostgreSQL almacena internamente en UTC (comportamiento estándar de TIMESTAMP WITH TIME ZONE)
    
    Uso:
        fecha_asignacion = Column(BogotaDateTime, nullable=True)
    """
    impl = SADateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        """
        Procesa el valor antes de enviarlo a la base de datos.
        Convierte a UTC si tiene timezone, o deja como está si es naive.
        """
        if value is None:
            return None
        
        if isinstance(value, datetime):
            # Si tiene timezone, asegurar que es UTC para PostgreSQL
            if value.tzinfo is not None:
                return value.astimezone(UTC_TZ)
            # Si es naive, asumir que ya es UTC
            return value
        
        return value

    def process_result_value(self, value, dialect):
        """
        Procesa el valor al leerlo de la base de datos.
        Convierte de UTC a timezone de Bogotá.
        """
        if value is None:
            return None
        
        if isinstance(value, datetime):
            # PostgreSQL devuelve en UTC, convertir a Bogotá
            if value.tzinfo is None:
                # Si por alguna razón es naive, asumirlo UTC
                value = UTC_TZ.localize(value)
            return value.astimezone(BOGOTA_TZ)
        
        return value


def get_bogota_now():
    """
    Retorna la fecha/hora actual en timezone de Bogotá.
    Útil para asignar fechas manualmente en el código.
    """
    return datetime.now(UTC_TZ).astimezone(BOGOTA_TZ)


def to_bogota_tz(dt: datetime) -> datetime:
    """
    Convierte cualquier datetime a timezone de Bogotá.
    
    Args:
        dt: datetime con o sin timezone
        
    Returns:
        datetime en timezone de Bogotá
    """
    if dt is None:
        return None
    
    if dt.tzinfo is None:
        # Asumir UTC si es naive
        dt = UTC_TZ.localize(dt)
    
    return dt.astimezone(BOGOTA_TZ)
