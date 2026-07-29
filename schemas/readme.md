# Schemas (Validación y Serialización)

## 📋 Descripción
Esta carpeta contiene los **schemas de Pydantic** que definen la estructura de datos para entrada (request) y salida (response) en la API. Validan automáticamente los datos, documentan la API y proveen serialización/deserialización.

## 🔗 Conexiones
- **Usado por**: API Routes (validación de request/response)
- **NO accede**: Directamente a DB o Services
- **Documenta**: Automáticamente en OpenAPI/Swagger

## 🎯 Responsabilidades
1. **Validar datos de entrada** (request body, query params)
2. **Definir estructura de respuestas** (response models)
3. **Documentar API** automáticamente (OpenAPI)
4. **Serializar/Deserializar** datos a/desde JSON
5. **Convertir modelos ORM** a schemas (usando `from_orm`)
6. **Validaciones personalizadas** (tipos, rangos, formatos)

## 📂 Estructura
```
schemas/
├── __init__.py
├── readme.md
├── auth_schema.py         # Login, tokens, refresh
├── user_schema.py         # Usuarios (CRUD)
├── automation_schema.py   # Automatización
├── enlistment_schema.py   # Enlistment manager
└── siebel_schema.py       # Datos de Siebel
```

## 🔄 Flujo en la Arquitectura
```
Cliente → Request JSON
              ↓
         Request Schema (valida)
              ↓
         API Route (datos validados)
              ↓
         Service (lógica)
              ↓
         Response Schema (serializa)
              ↓
         Cliente ← Response JSON
```

## 📝 Ejemplos de Implementación

### 1. Schema Básico (Request y Response)
```python
# app/schemas/user_schema.py
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    """Schema base con campos comunes."""
    login: str = Field(..., min_length=3, max_length=50, description="Login del usuario")
    full_name: str = Field(..., min_length=3, max_length=100, description="Nombre completo")
    email: EmailStr = Field(..., description="Email válido")
    user_identify: str = Field(..., min_length=5, max_length=20, description="DNI/Cédula")


class UserCreate(UserBase):
    """
    Schema para crear usuario (Request).
    Incluye campos adicionales requeridos para creación.
    """
    password: str = Field(..., min_length=8, description="Contraseña (min 8 caracteres)")
    
    @validator('password')
    def validate_password(cls, v):
        """Validación personalizada de contraseña."""
        if not any(char.isdigit() for char in v):
            raise ValueError("La contraseña debe contener al menos un número")
        if not any(char.isupper() for char in v):
            raise ValueError("La contraseña debe contener al menos una mayúscula")
        return v


class UserUpdate(BaseModel):
    """
    Schema para actualizar usuario (Request).
    Todos los campos son opcionales.
    """
    full_name: Optional[str] = Field(None, min_length=3, max_length=100)
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    """
    Schema para respuesta de usuario (Response).
    Incluye campos adicionales que vienen de la BD.
    """
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        # Permite crear schema desde modelos ORM
        from_attributes = True  # Pydantic v2 (antes: orm_mode = True)


class UserListResponse(BaseModel):
    """Schema para lista de usuarios con paginación."""
    users: list[UserResponse]
    total: int
    page: int
    page_size: int
```

### 2. Schema para Autenticación
```python
# app/schemas/auth_schema.py
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Schema para login."""
    username: str = Field(..., min_length=3, description="Nombre de usuario")
    password: str = Field(..., min_length=1, description="Contraseña")


class TokenResponse(BaseModel):
    """Schema para respuesta de tokens."""
    access_token: str = Field(..., description="Access token JWT")
    refresh_token: str = Field(..., description="Refresh token JWT")
    token_type: str = Field(default="Bearer", description="Tipo de token")
    expires_in: int = Field(..., description="Segundos hasta expiración")


class RefreshTokenRequest(BaseModel):
    """Schema para refresh token."""
    refresh_token: str = Field(..., description="Refresh token JWT")


class LogoutRequest(BaseModel):
    """Schema para logout (opcional si se usa desde header)."""
    pass  # El token viene en el header Authorization
```

### 3. Schema con Relaciones
```python
# app/schemas/producto_schema.py
from pydantic import BaseModel, Field, condecimal
from typing import Optional
from decimal import Decimal


class CategoriaBase(BaseModel):
    """Schema base de categoría."""
    nombre: str = Field(..., max_length=100)
    descripcion: Optional[str] = None


class CategoriaResponse(CategoriaBase):
    """Schema de respuesta de categoría."""
    id: int
    
    class Config:
        from_attributes = True


class ProductoCreate(BaseModel):
    """Schema para crear producto."""
    nombre: str = Field(..., min_length=3, max_length=200)
    precio: condecimal(max_digits=10, decimal_places=2) = Field(..., gt=0)
    categoria_id: int = Field(..., gt=0)


class ProductoResponse(BaseModel):
    """Schema de respuesta de producto (con categoría incluida)."""
    id: int
    nombre: str
    precio: Decimal
    categoria_id: int
    categoria: Optional[CategoriaResponse] = None  # Nested schema
    
    class Config:
        from_attributes = True


class ProductoListResponse(BaseModel):
    """Schema para lista de productos."""
    productos: list[ProductoResponse]
    total: int
```

### 4. Schema con Validaciones Personalizadas
```python
# app/schemas/enlistment_schema.py
from pydantic import BaseModel, Field, validator, root_validator
from typing import Optional, Dict, Any
from datetime import datetime


class EnlistmentCreate(BaseModel):
    """Schema para crear enlistment."""
    pedido_crm: str = Field(..., min_length=5, max_length=50, description="Número de pedido")
    estado: str = Field(..., description="Estado del enlistment")
    campos_dinamicos: Dict[str, Any] = Field(default={}, description="Campos personalizados")
    
    @validator('pedido_crm')
    def validate_pedido_format(cls, v):
        """Valida formato del número de pedido."""
        if not v.startswith('PED-'):
            raise ValueError("El pedido debe iniciar con 'PED-'")
        return v.upper()
    
    @validator('estado')
    def validate_estado(cls, v):
        """Valida que el estado sea uno de los permitidos."""
        estados_validos = ['PENDIENTE', 'EN_PROCESO', 'COMPLETADO', 'CANCELADO']
        if v.upper() not in estados_validos:
            raise ValueError(f"Estado debe ser uno de: {', '.join(estados_validos)}")
        return v.upper()
    
    @root_validator
    def validate_campos_dinamicos(cls, values):
        """Validación que requiere múltiples campos."""
        estado = values.get('estado')
        campos = values.get('campos_dinamicos', {})
        
        if estado == 'COMPLETADO' and 'fecha_completado' not in campos:
            raise ValueError("Estado COMPLETADO requiere campo 'fecha_completado'")
        
        return values


class EnlistmentUpdate(BaseModel):
    """Schema para actualizar enlistment."""
    estado: Optional[str] = None
    campos_dinamicos: Optional[Dict[str, Any]] = None


class EnlistmentResponse(BaseModel):
    """Schema de respuesta de enlistment."""
    id: int
    pedido_crm: str
    estado: str
    campos_dinamicos: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
```

### 5. Schema con Tipos Genéricos
```python
# app/schemas/common_schema.py
from pydantic import BaseModel
from typing import Generic, TypeVar, List, Optional

T = TypeVar('T')


class PaginatedResponse(BaseModel, Generic[T]):
    """Schema genérico para respuestas paginadas."""
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int


class ApiResponse(BaseModel, Generic[T]):
    """Schema genérico para respuestas de API."""
    type: str = "success"  # success, error, warning
    message: str
    data: Optional[T] = None


# Uso:
# response: ApiResponse[UserResponse] = ApiResponse(
#     type="success",
#     message="Usuario creado",
#     data=user_response
# )
```

### 6. Schema para Filtros y Búsqueda
```python
# app/schemas/filter_schema.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class UserFilter(BaseModel):
    """Schema para filtros de búsqueda de usuarios."""
    search: Optional[str] = Field(None, description="Buscar en nombre o email")
    is_active: Optional[bool] = Field(None, description="Filtrar por activos")
    created_after: Optional[datetime] = Field(None, description="Creados después de")
    created_before: Optional[datetime] = Field(None, description="Creados antes de")
    
    # Paginación
    page: int = Field(default=1, ge=1, description="Número de página")
    page_size: int = Field(default=20, ge=1, le=100, description="Tamaño de página")
    
    # Ordenamiento
    sort_by: Optional[str] = Field(default="created_at", description="Campo para ordenar")
    sort_order: Optional[str] = Field(default="desc", regex="^(asc|desc)$")
```

## ✅ Buenas Prácticas

### 1. **Nomenclatura**
- ✅ Sufijos descriptivos: `*Create`, `*Update`, `*Response`, `*Filter`
- ✅ Usar `Base` para campos comunes compartidos
- ✅ PascalCase para nombres de schemas

### 2. **Validación**
- ✅ Usar Field() con constraints (min_length, max_length, ge, le)
- ✅ Validaciones simples en Field(), complejas en @validator
- ✅ EmailStr para emails (requiere `pip install pydantic[email]`)
- ✅ Mensajes de error descriptivos en validadores

### 3. **Documentación**
- ✅ Agregar docstrings a cada schema
- ✅ Usar `description` en Field() para documentar API
- ✅ Ejemplos en docstrings para claridad

### 4. **Reutilización**
- ✅ Crear schemas Base para compartir campos
- ✅ Usar herencia para especializar schemas
- ✅ Schemas genéricos para respuestas comunes

### 5. **Configuración**
- ✅ `from_attributes = True` para convertir desde ORM (Pydantic v2)
- ✅ `orm_mode = True` si usas Pydantic v1
- ✅ Personalizar serialización en Config si es necesario

### 6. **Tipos de Datos**
- ✅ Usar tipos built-in cuando sea posible (str, int, bool)
- ✅ EmailStr para emails
- ✅ condecimal() para valores monetarios
- ✅ Optional[] para campos opcionales
- ✅ List[], Dict[] para colecciones

## 🚫 Anti-patrones (Evitar)

```python
# ❌ MAL: No usar Field() para validaciones
class UserCreate(BaseModel):
    email: str  # ❌ Sin validación

# ✅ BIEN: Usar Field() y tipos especializados
class UserCreate(BaseModel):
    email: EmailStr = Field(..., description="Email válido")


# ❌ MAL: Duplicar campos en múltiples schemas
class UserCreate(BaseModel):
    login: str
    email: str
    full_name: str

class UserUpdate(BaseModel):
    login: str  # ❌ Duplicado
    email: str  # ❌ Duplicado
    full_name: str  # ❌ Duplicado

# ✅ BIEN: Usar herencia
class UserBase(BaseModel):
    login: str
    email: EmailStr
    full_name: str

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):  # Solo campos opcionales
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None


# ❌ MAL: Lógica de negocio en validators
@validator('price')
def validate_price(cls, v):
    # ❌ No hacer queries a DB aquí
    existing = db.query(Product).filter(Product.price == v).first()
    if existing:
        raise ValueError("Precio ya existe")
    return v

# ✅ BIEN: Solo validaciones de formato/tipo
@validator('price')
def validate_price(cls, v):
    if v <= 0:
        raise ValueError("Precio debe ser mayor a 0")
    return v


# ❌ MAL: No documentar campos
nombre: str  # ❌ Sin descripción

# ✅ BIEN: Documentar con Field()
nombre: str = Field(..., description="Nombre del producto", max_length=200)


# ❌ MAL: No usar from_attributes
class UserResponse(BaseModel):
    id: int
    email: str
    # ❌ No se puede crear desde modelo ORM

# ✅ BIEN: Configurar from_attributes
class UserResponse(BaseModel):
    id: int
    email: str
    
    class Config:
        from_attributes = True  # Pydantic v2
        # orm_mode = True  # Pydantic v1
```

## 💡 Conversión entre Model y Schema

```python
# Model ORM → Schema
user = user_repository.get_by_id(1)  # Retorna User (Model)
user_response = UserResponse.from_orm(user)  # Pydantic v1
user_response = UserResponse.model_validate(user)  # Pydantic v2

# Schema → dict
user_dict = user_response.dict()  # Pydantic v1
user_dict = user_response.model_dump()  # Pydantic v2

# dict → Schema
data = {"login": "john", "email": "john@example.com"}
user_create = UserCreate(**data)

# Schema → JSON
json_str = user_response.json()  # Pydantic v1
json_str = user_response.model_dump_json()  # Pydantic v2
```

## 🧪 Testing de Schemas

```python
# tests/test_schemas.py
import pytest
from pydantic import ValidationError
from app.schemas.user_schema import UserCreate


def test_user_create_valid():
    """Test con datos válidos."""
    data = {
        "login": "john_doe",
        "full_name": "John Doe",
        "email": "john@example.com",
        "user_identify": "12345678",
        "password": "Password123"
    }
    user = UserCreate(**data)
    assert user.login == "john_doe"


def test_user_create_invalid_email():
    """Test con email inválido."""
    data = {
        "login": "john_doe",
        "full_name": "John Doe",
        "email": "invalid-email",  # ❌ Email inválido
        "user_identify": "12345678",
        "password": "Password123"
    }
    with pytest.raises(ValidationError) as exc_info:
        UserCreate(**data)
    
    assert "email" in str(exc_info.value)


def test_user_create_password_too_short():
    """Test con contraseña muy corta."""
    data = {
        "login": "john_doe",
        "full_name": "John Doe",
        "email": "john@example.com",
        "user_identify": "12345678",
        "password": "123"  # ❌ Muy corta
    }
    with pytest.raises(ValidationError):
        UserCreate(**data)
```

## 📚 Recursos Adicionales
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [FastAPI Pydantic Models](https://fastapi.tiangolo.com/tutorial/body/)
- [Pydantic Validators](https://docs.pydantic.dev/latest/concepts/validators/)
- [Pydantic Field Types](https://docs.pydantic.dev/latest/api/fields/)