# Utils (Utilidades y Helpers)

## 📋 Descripción
Esta carpeta contiene **funciones utilitarias** y **helpers** reutilizables en toda la aplicación. Son funciones puras o de propósito específico que no pertenecen a ninguna capa en particular pero son usadas transversalmente.

## 🔗 Conexiones
- **Usado por**: Toda la aplicación (Services, Repositories, Routes, Core)
- **NO depende**: De otras capas específicas (debe ser independiente)
- **Proporciona**: Funciones auxiliares, constantes, helpers

## 🎯 Responsabilidades
1. **Funciones auxiliares** reutilizables
2. **Constantes** de la aplicación
3. **Transformaciones** de datos genéricas
4. **Validaciones** genéricas
5. **Helpers** para operaciones comunes
6. **Utilidades** de formateo, parseo, etc.

## 📂 Estructura
```
utils/
├── __init__.py
├── readme.md
├── constants.py       # Constantes de la aplicación
├── hash_utils.py      # Hashing y encriptación
├── date_utils.py      # Utilidades de fechas (opcional)
├── string_utils.py    # Utilidades de strings (opcional)
└── validators.py      # Validadores genéricos (opcional)
```

## 🔄 Flujo en la Arquitectura
```
Cualquier capa → Utils.function() → Retorna resultado
                     ↓
                (función pura, sin efectos secundarios)
```

## 📝 Ejemplos de Implementación

### 1. Constantes (constants.py)
```python
# app/utils/constants.py
"""
Constantes de la aplicación.
Valores que no cambian y se usan en múltiples lugares.
"""


class Constants:
    """Constantes generales."""
    
    # APIs Externas
    USERS_M2M = {
        "user": "unefieldste9",
        "password": "Colombia2026--++"
    }
    
    # Estados
    ESTADOS_ENLISTMENT = {
        "PENDIENTE": "pendiente",
        "EN_PROCESO": "en_proceso",
        "COMPLETADO": "completado",
        "CANCELADO": "cancelado",
        "ERROR": "error"
    }
    
    # Roles
    ROLES = {
        "ADMIN": "admin",
        "USER": "user",
        "GUEST": "guest"
    }
    
    # Límites
    MAX_PAGE_SIZE = 100
    DEFAULT_PAGE_SIZE = 20
    MAX_FILE_SIZE_MB = 10
    
    # Timeouts
    API_TIMEOUT_SECONDS = 30
    DB_TIMEOUT_SECONDS = 10
    
    # Formatos
    DATE_FORMAT = "%Y-%m-%d"
    DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
    
    # Regex Patterns
    EMAIL_PATTERN = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    PHONE_PATTERN = r'^\+?1?\d{9,15}$'
    
    # Códigos de Error Personalizados
    ERROR_CODES = {
        "INVALID_CREDENTIALS": "E001",
        "USER_NOT_FOUND": "E002",
        "UNAUTHORIZED": "E003",
        "VALIDATION_ERROR": "E004",
    }


class ProductMapper:
    """Mapeo de productos entre sistemas."""
    
    FENIX_TO_SIEBEL = {
        "Línea Telefónica": "Telefonía Fija",
        "Internet": "Internet",
        "TV": "TV",
        "Móvil": "Móvil",
        "Fija": "Telefonía Fija",
        "Datos": "Internet",
        "Video": "TV",
        "HFC": "HFC",
        "GPON": "GPON",
        "FTTH": "FTTH"
    }
    
    @classmethod
    def map_product(cls, product_name: str) -> str:
        """
        Mapea nombre de producto de Fenix a Siebel.
        
        Args:
            product_name: Nombre del producto en Fenix
        
        Returns:
            Nombre del producto en Siebel
        """
        return cls.FENIX_TO_SIEBEL.get(product_name, product_name)
```

### 2. Hash Utils (hash_utils.py - ya existe en el proyecto)
```python
# app/utils/hash_utils.py
import hashlib
import json
from typing import Dict, Any, List
from datetime import datetime, date
import pandas as pd


def prepare_for_json(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Prepara un diccionario para ser serializado a JSON.
    Convierte tipos no serializables a formatos compatibles.
    
    Args:
        data: Diccionario con datos potencialmente no serializables
        
    Returns:
        Diccionario con todos los valores JSON-compatibles
    """
    result = {}
    for key, value in data.items():
        if value is None or (pd.isna(value) if hasattr(pd, 'isna') else False):
            result[key] = None
        elif isinstance(value, pd.Timestamp):
            result[key] = value.isoformat()
        elif isinstance(value, (datetime, date)):
            result[key] = value.isoformat()
        elif isinstance(value, (pd.Series, pd.DataFrame)):
            result[key] = value.to_dict() if isinstance(value, pd.DataFrame) else value.tolist()
        elif isinstance(value, (int, float, bool, str)):
            if hasattr(value, 'item'):  # numpy/pandas scalar
                result[key] = value.item()
            else:
                result[key] = value
        elif isinstance(value, dict):
            result[key] = prepare_for_json(value)
        elif isinstance(value, list):
            result[key] = [prepare_for_json(item) if isinstance(item, dict) else item for item in value]
        else:
            result[key] = str(value)
    
    return result


def compute_hash(data: Dict[str, Any]) -> str:
    """
    Calcula un hash MD5 de un diccionario.
    Útil para detectar cambios en datos.
    
    Args:
        data: Diccionario a hashear
    
    Returns:
        Hash MD5 en hexadecimal
    """
    # Ordenar keys para hash consistente
    json_str = json.dumps(data, sort_keys=True, default=str)
    return hashlib.md5(json_str.encode()).hexdigest()


def hash_password(password: str) -> str:
    """
    Hashea una contraseña usando SHA256.
    
    Args:
        password: Contraseña en texto plano
    
    Returns:
        Hash de la contraseña
    
    Note:
        En producción, usar bcrypt o argon2
    """
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, hashed: str) -> bool:
    """
    Verifica una contraseña contra su hash.
    
    Args:
        password: Contraseña en texto plano
        hashed: Hash almacenado
    
    Returns:
        True si coinciden, False si no
    """
    return hash_password(password) == hashed
```

### 3. Date Utils
```python
# app/utils/date_utils.py
"""Utilidades para manejo de fechas."""
from datetime import datetime, timedelta, timezone
from typing import Optional


def now_utc() -> datetime:
    """
    Retorna datetime actual en UTC.
    
    Returns:
        Datetime actual en UTC
    """
    return datetime.now(timezone.utc)


def format_datetime(dt: datetime, format: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Formatea un datetime a string.
    
    Args:
        dt: Datetime a formatear
        format: Formato de salida
    
    Returns:
        String formateado
    """
    if not dt:
        return None
    return dt.strftime(format)


def parse_datetime(date_str: str, format: str = "%Y-%m-%d %H:%M:%S") -> Optional[datetime]:
    """
    Parsea un string a datetime.
    
    Args:
        date_str: String con fecha
        format: Formato del string
    
    Returns:
        Datetime parseado o None si falla
    """
    try:
        return datetime.strptime(date_str, format)
    except (ValueError, TypeError):
        return None


def add_days(dt: datetime, days: int) -> datetime:
    """
    Agrega días a un datetime.
    
    Args:
        dt: Datetime base
        days: Días a agregar (puede ser negativo)
    
    Returns:
        Datetime resultante
    """
    return dt + timedelta(days=days)


def days_between(start: datetime, end: datetime) -> int:
    """
    Calcula días entre dos fechas.
    
    Args:
        start: Fecha inicial
        end: Fecha final
    
    Returns:
        Número de días (puede ser negativo)
    """
    delta = end - start
    return delta.days


def is_expired(expiry_date: datetime) -> bool:
    """
    Verifica si una fecha ha expirado.
    
    Args:
        expiry_date: Fecha de expiración
    
    Returns:
        True si expiró, False si no
    """
    return now_utc() > expiry_date.replace(tzinfo=timezone.utc)


def start_of_day(dt: datetime) -> datetime:
    """
    Retorna el inicio del día (00:00:00).
    
    Args:
        dt: Datetime
    
    Returns:
        Datetime al inicio del día
    """
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


def end_of_day(dt: datetime) -> datetime:
    """
    Retorna el fin del día (23:59:59).
    
    Args:
        dt: Datetime
    
    Returns:
        Datetime al fin del día
    """
    return dt.replace(hour=23, minute=59, second=59, microsecond=999999)
```

### 4. String Utils
```python
# app/utils/string_utils.py
"""Utilidades para manejo de strings."""
import re
from typing import Optional


def to_snake_case(text: str) -> str:
    """
    Convierte texto a snake_case.
    
    Args:
        text: Texto a convertir
    
    Returns:
        Texto en snake_case
    """
    text = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', text)
    text = re.sub('([a-z0-9])([A-Z])', r'\1_\2', text)
    return text.lower()


def to_camel_case(text: str) -> str:
    """
    Convierte texto a camelCase.
    
    Args:
        text: Texto a convertir (snake_case o normal)
    
    Returns:
        Texto en camelCase
    """
    components = text.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


def to_pascal_case(text: str) -> str:
    """
    Convierte texto a PascalCase.
    
    Args:
        text: Texto a convertir
    
    Returns:
        Texto en PascalCase
    """
    return ''.join(x.title() for x in text.split('_'))


def truncate(text: str, length: int, suffix: str = "...") -> str:
    """
    Trunca un texto a una longitud máxima.
    
    Args:
        text: Texto a truncar
        length: Longitud máxima
        suffix: Sufijo a agregar si se trunca
    
    Returns:
        Texto truncado
    """
    if len(text) <= length:
        return text
    return text[:length - len(suffix)] + suffix


def sanitize_filename(filename: str) -> str:
    """
    Sanitiza un nombre de archivo eliminando caracteres no válidos.
    
    Args:
        filename: Nombre de archivo
    
    Returns:
        Nombre de archivo sanitizado
    """
    # Eliminar caracteres no válidos
    sanitized = re.sub(r'[<>:"/\\|?*]', '', filename)
    # Reemplazar espacios
    sanitized = sanitized.replace(' ', '_')
    return sanitized


def mask_sensitive_data(text: str, visible_chars: int = 4) -> str:
    """
    Enmascara datos sensibles mostrando solo los últimos caracteres.
    
    Args:
        text: Texto a enmascarar
        visible_chars: Caracteres visibles al final
    
    Returns:
        Texto enmascarado
    """
    if not text or len(text) <= visible_chars:
        return '*' * len(text) if text else ''
    
    masked_length = len(text) - visible_chars
    return '*' * masked_length + text[-visible_chars:]


def is_valid_email(email: str) -> bool:
    """
    Valida formato de email.
    
    Args:
        email: Email a validar
    
    Returns:
        True si es válido, False si no
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))
```

### 5. Validators
```python
# app/utils/validators.py
"""Validadores genéricos."""
import re
from typing import Any, Optional


def validate_phone(phone: str) -> bool:
    """
    Valida formato de teléfono.
    
    Args:
        phone: Número de teléfono
    
    Returns:
        True si es válido, False si no
    """
    pattern = r'^\+?1?\d{9,15}$'
    return bool(re.match(pattern, phone))


def validate_dni(dni: str, country: str = "CO") -> bool:
    """
    Valida DNI/Cédula según el país.
    
    Args:
        dni: Documento de identidad
        country: Código de país (CO, MX, etc)
    
    Returns:
        True si es válido, False si no
    """
    if country == "CO":
        # Colombia: 6-10 dígitos
        return bool(re.match(r'^\d{6,10}$', dni))
    # Agregar otros países según necesidad
    return True


def validate_range(value: Any, min_val: Any, max_val: Any) -> bool:
    """
    Valida que un valor esté en un rango.
    
    Args:
        value: Valor a validar
        min_val: Valor mínimo
        max_val: Valor máximo
    
    Returns:
        True si está en rango, False si no
    """
    try:
        return min_val <= value <= max_val
    except TypeError:
        return False


def validate_length(text: str, min_length: int = 0, max_length: Optional[int] = None) -> bool:
    """
    Valida longitud de un texto.
    
    Args:
        text: Texto a validar
        min_length: Longitud mínima
        max_length: Longitud máxima (None = sin límite)
    
    Returns:
        True si cumple, False si no
    """
    length = len(text)
    
    if length < min_length:
        return False
    
    if max_length is not None and length > max_length:
        return False
    
    return True


def is_numeric(value: str) -> bool:
    """
    Verifica si un string es numérico.
    
    Args:
        value: String a verificar
    
    Returns:
        True si es numérico, False si no
    """
    try:
        float(value)
        return True
    except (ValueError, TypeError):
        return False
```

## ✅ Buenas Prácticas

### 1. **Funciones Puras**
- ✅ Sin efectos secundarios
- ✅ Mismo input → mismo output
- ✅ No modificar argumentos mutables

### 2. **Nomenclatura**
- ✅ Nombres descriptivos (verb_noun)
- ✅ snake_case para funciones
- ✅ SCREAMING_SNAKE_CASE para constantes

### 3. **Documentación**
- ✅ Docstrings con Args y Returns
- ✅ Ejemplos de uso si es complejo
- ✅ Notas sobre edge cases

### 4. **Testing**
- ✅ Funciones utils son fáciles de testear
- ✅ Testear edge cases
- ✅ Testear con diferentes tipos de input

### 5. **Independencia**
- ✅ No depender de otras capas
- ✅ No hacer I/O (DB, APIs, archivos)
- ✅ Mantener utils genéricos y reutilizables

### 6. **Performance**
- ✅ Optimizar funciones frecuentemente usadas
- ✅ Evitar imports costosos en utils
- ✅ Cachear resultados si es apropiado

## 🚫 Anti-patrones (Evitar)

```python
# ❌ MAL: Función con efectos secundarios
def format_user(user):
    user.name = user.name.upper()  # ❌ Modifica el argumento
    return user

# ✅ BIEN: Función pura
def format_user_name(name: str) -> str:
    return name.upper()


# ❌ MAL: Lógica de negocio en utils
def validate_user_can_purchase(user_id: int) -> bool:
    # ❌ Acceso a BD en utils
    user = db.query(User).filter(User.id == user_id).first()
    return user.balance > 100

# ✅ BIEN: Solo validaciones genéricas
def is_positive(value: float) -> bool:
    return value > 0


# ❌ MAL: Utils dependientes de otras capas
from app.repositories.user_repository import UserRepository  # ❌

def get_user_name(user_id):
    repo = UserRepository()
    user = repo.get_by_id(user_id)
    return user.name

# ✅ BIEN: Utils independientes
def format_full_name(first_name: str, last_name: str) -> str:
    return f"{first_name} {last_name}".strip().title()


# ❌ MAL: No documentar
def x(a, b):  # ❌ Nombres no descriptivos, sin documentación
    return a + b

# ✅ BIEN: Documentación clara
def add_numbers(a: float, b: float) -> float:
    """
    Suma dos números.
    
    Args:
        a: Primer número
        b: Segundo número
    
    Returns:
        Suma de a y b
    """
    return a + b
```

## 🧪 Testing de Utils

```python
# tests/test_string_utils.py
from app.utils.string_utils import to_snake_case, mask_sensitive_data, is_valid_email


def test_to_snake_case():
    assert to_snake_case("HelloWorld") == "hello_world"
    assert to_snake_case("helloWorld") == "hello_world"
    assert to_snake_case("hello_world") == "hello_world"


def test_mask_sensitive_data():
    assert mask_sensitive_data("1234567890", 4) == "******7890"
    assert mask_sensitive_data("123", 4) == "***"
    assert mask_sensitive_data("", 4) == ""


def test_is_valid_email():
    assert is_valid_email("test@example.com") == True
    assert is_valid_email("invalid-email") == False
    assert is_valid_email("test@") == False
```

## 📚 Recursos Adicionales
- [Python Utilities Best Practices](https://realpython.com/python-refactoring/)
- [Pure Functions](https://realpython.com/defining-your-own-python-function/#pure-functions)
- [Python String Methods](https://docs.python.org/3/library/stdtypes.html#string-methods)