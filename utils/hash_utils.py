import hashlib
import json
from typing import Dict, Any, List
from datetime import datetime, date
import pandas as pd


def prepare_for_json(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Prepara un diccionario para ser serializado a JSON.
    Convierte pandas Timestamp y otros tipos no serializables a formatos compatibles.
    
    Args:
        data: Diccionario con datos que pueden contener tipos no serializables
        
    Returns:
        Diccionario con todos los valores convertidos a tipos JSON compatibles
    """
    result = {}
    for key, value in data.items():
        if value is None or (pd.isna(value) if hasattr(pd, 'isna') else False):
            # Manejar None y pandas NaT/NaN
            result[key] = None
        elif isinstance(value, pd.Timestamp):
            # Convertir pandas Timestamp a string ISO format
            result[key] = value.isoformat()
        elif isinstance(value, (datetime, date)):
            # Convertir datetime/date a string ISO format
            result[key] = value.isoformat()
        elif isinstance(value, (pd.Series, pd.DataFrame)):
            # Convertir pandas Series/DataFrame a dict/list
            result[key] = value.to_dict() if isinstance(value, pd.DataFrame) else value.tolist()
        elif isinstance(value, (int, float, bool, str)):
            # Tipos nativos de Python ya son JSON serializables
            # Convertir numpy/pandas int64, float64 a int/float de Python
            if hasattr(value, 'item'):  # numpy/pandas scalar
                result[key] = value.item()
            else:
                result[key] = value
        elif isinstance(value, dict):
            # Recursión para diccionarios anidados
            result[key] = prepare_for_json(value)
        elif isinstance(value, list):
            # Procesar cada elemento de la lista
            result[key] = [prepare_for_json(item) if isinstance(item, dict) else item for item in value]
        else:
            # Para cualquier otro tipo, convertir a string como fallback
            result[key] = str(value)
    
    return result


def normalize_value(value: Any) -> str:
    """
    Normaliza un valor para el cálculo de hash.
    Convierte diferentes tipos de datos a string de forma consistente.
    
    Args:
        value: Valor a normalizar
        
    Returns:
        String normalizado
    """
    if value is None:
        return "NULL"
    
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    
    if isinstance(value, (int, float)):
        return str(value)
    
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    
    if isinstance(value, (list, dict)):
        return json.dumps(value, sort_keys=True, default=str)
    
    return str(value).strip()


def generate_record_hash(record: Dict[str, Any], exclude_fields: List[str] = None) -> str:
    """
    Genera un hash SHA256 de un registro de manera determinística.
    Los campos se ordenan alfabéticamente para garantizar consistencia.
    
    Args:
        record: Diccionario con los datos del registro
        exclude_fields: Lista de campos a excluir del hash (ej: timestamps de auditoría)
        
    Returns:
        Hash SHA256 en formato hexadecimal (64 caracteres)
        
    Example:
        >>> record = {"oferta": "1-123", "estado": "Activo", "responsable": "Juan"}
        >>> hash_value = generate_record_hash(record)
        >>> len(hash_value)
        64
    """
    if exclude_fields is None:
        exclude_fields = ['created_at', 'updated_at', 'ticket_carga', 'hash_registro']
    
    # Filtrar campos excluidos
    filtered_record = {k: v for k, v in record.items() if k not in exclude_fields}
    
    # Ordenar campos alfabéticamente
    sorted_keys = sorted(filtered_record.keys())
    
    # Construir string con formato: campo1:valor1|campo2:valor2|...
    hash_parts = []
    for key in sorted_keys:
        normalized_value = normalize_value(filtered_record[key])
        hash_parts.append(f"{key}:{normalized_value}")
    
    hash_string = "|".join(hash_parts)
    
    # Generar hash SHA256
    hash_object = hashlib.sha256(hash_string.encode('utf-8'))
    return hash_object.hexdigest()


def compare_records(old_record: Dict[str, Any], new_record: Dict[str, Any], 
                   exclude_fields: List[str] = None) -> Dict[str, Any]:
    """
    Compara dos registros y retorna los campos que cambiaron.
    
    Args:
        old_record: Registro anterior
        new_record: Registro nuevo
        exclude_fields: Campos a excluir de la comparación
        
    Returns:
        Dict con los campos modificados y sus valores (antes y después)
        
    Example:
        >>> old = {"oferta": "1-123", "estado": "Activo", "responsable": "Juan"}
        >>> new = {"oferta": "1-123", "estado": "Modificado", "responsable": "Juan"}
        >>> changes = compare_records(old, new)
        >>> changes
        {
            "estado": {
                "old": "Activo",
                "new": "Modificado"
            }
        }
    """
    if exclude_fields is None:
        exclude_fields = ['created_at', 'updated_at', 'ticket_carga', 'hash_registro']
    
    changes = {}
    
    # Obtener todas las claves únicas de ambos registros
    all_keys = set(old_record.keys()) | set(new_record.keys())
    
    for key in all_keys:
        if key in exclude_fields:
            continue
        
        old_value = old_record.get(key)
        new_value = new_record.get(key)
        
        # Normalizar valores para comparación
        old_normalized = normalize_value(old_value)
        new_normalized = normalize_value(new_value)
        
        if old_normalized != new_normalized:
            changes[key] = {
                "old": old_value,
                "new": new_value
            }
    
    return changes


def generate_ticket_carga(prefix: str = "LOAD") -> str:
    """
    Genera un ticket único para identificar una carga.
    Formato: PREFIX_YYYY-MM-DD_HH:MM:SS_UUID
    
    Args:
        prefix: Prefijo del ticket (default: "LOAD")
        
    Returns:
        Ticket único como string
        
    Example:
        >>> ticket = generate_ticket_carga()
        >>> ticket.startswith("LOAD_")
        True
    """
    import uuid
    from datetime import datetime
    
    timestamp = datetime.now().astimezone().strftime("%Y-%m-%d_%H:%M:%S")
    unique_id = str(uuid.uuid4())[:8]
    
    return f"{prefix}_{timestamp}_{unique_id}"
