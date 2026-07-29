# Arquitectura del Proyecto Gestor v2

## 📋 Tabla de Contenido
- [Visión General](#-visión-general)
- [Arquitectura de Capas](#-arquitectura-de-capas)
- [Flujo de Datos](#-flujo-de-datos)
- [Estructura de Carpetas](#-estructura-de-carpetas)
- [Tecnologías Utilizadas](#-tecnologías-utilizadas)
- [Guía de Desarrollo](#-guía-de-desarrollo)
- [Convenciones y Estándares](#-convenciones-y-estándares)
- [Diagramas](#-diagramas)

---

## 🎯 Visión General

**Gestor v2** es una aplicación backend construida con **FastAPI** que implementa una arquitectura en capas limpia y escalable. El proyecto gestiona operaciones de automatización, enlistment y administración de usuarios, conectándose a múltiples bases de datos (PostgreSQL, MongoDB, Oracle).

### Principios de Diseño
- **Separación de Responsabilidades**: Cada capa tiene una única responsabilidad
- **Independencia de Capas**: Las capas no dependen de implementaciones concretas
- **Testabilidad**: Código fácilmente testeable con inyección de dependencias
- **Escalabilidad**: Estructura que permite crecer sin refactorización masiva
- **Mantenibilidad**: Código limpio, documentado y con patrones consistentes

---

## 🏗️ Arquitectura de Capas

El proyecto sigue una arquitectura de **4 capas principales**:

```
┌─────────────────────────────────────────────────────────────┐
│                      API LAYER (Routes)                      │
│  • Endpoints HTTP                                            │
│  • Validación de entrada (Schemas)                          │
│  • Autenticación (Decorators)                               │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                    SERVICE LAYER                             │
│  • Lógica de negocio                                        │
│  • Orquestación de repositories                             │
│  • Validaciones de negocio                                  │
│  • Transformación de datos                                  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                   REPOSITORY LAYER                           │
│  • Acceso a bases de datos (ORM)                           │
│  • Queries SQL raw                                          │
│  • Llamadas a APIs externas                                │
│  • Transformación DB ↔ Objects                             │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                      DATA LAYER                              │
│  • PostgreSQL (BD principal)                                │
│  • MongoDB (logs)                                           │
│  • Oracle Fenix/MSS/Siebel (datos externos)                │
└─────────────────────────────────────────────────────────────┘
```

### Capas Transversales

```
┌─────────────────────────────────────────────────────────────┐
│                 TRANSVERSAL LAYERS                           │
│                                                              │
│  CORE: Configuración, JWT, LDAP, Logging, Redis            │
│  MODELS: Definiciones ORM de tablas                         │
│  SCHEMAS: Validación Pydantic (Request/Response)            │
│  DECORATORS: Middleware (Auth, Cache)                       │
│  UTILS: Funciones auxiliares reutilizables                  │
│  MIGRATIONS: Scripts de migración de BD                     │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔄 Flujo de Datos

### Flujo Completo de una Request

```
1. Cliente → HTTP Request
                ↓
2. API Route → Valida con Schema (Pydantic)
                ↓
3. Decorator → jwt_required (valida token)
                ↓
4. Service → Lógica de negocio
                ↓
5. Repository → Query a BD
                ↓
6. Database → Retorna datos
                ↓
7. Repository → Transforma a objetos
                ↓
8. Service → Aplica reglas de negocio
                ↓
9. API Route → Serializa con Schema
                ↓
10. Cliente ← HTTP Response (JSON)
```

### Ejemplo Concreto: Login de Usuario

```python
# 1. REQUEST
POST /login
{
  "username": "john_doe",
  "password": "secret"
}

# 2. API ROUTE (routes_auth.py)
@router.post("/login")
async def login(payload: LoginRequest):  # ← Schema valida
    return await user_service.login(
        username=payload.username,
        password=payload.password
    )

# 3. SERVICE (user_service.py)
async def login(username, password):
    # 3.1 Autenticar con LDAP
    ldap_user = authenticate_user(username, password)
    
    # 3.2 Buscar usuario en BD
    user = user_repo.get_by_login(username)
    
    # 3.3 Crear tokens JWT
    access_token, jti, exp = create_jwt_token(user.id)
    
    # 3.4 Guardar en Redis
    await redis_client.setex(f"refresh:{user.id}", ...)
    
    # 3.5 Retornar
    return {
        "user": user.to_dict(),
        "access_token": access_token,
        "token_type": "Bearer"
    }

# 4. REPOSITORY (user_repository.py)
def get_by_login(self, login: str):
    return self.db.query(User).filter(User.login == login).first()

# 5. RESPONSE
{
  "user": {
    "id": 1,
    "login": "john_doe",
    "email": "john@example.com"
  },
  "access_token": "eyJ0eXAiOiJKV1...",
  "token_type": "Bearer"
}
```

---

## 📂 Estructura de Carpetas

```
app/
├── __init__.py
├── main.py                    # ⭐ Entry point, FastAPI app
├── ARCHITECTURE.md            # 📖 Este documento
│
├── api/                       # 🌐 Endpoints HTTP
│   ├── readme.md
│   └── v1/
│       ├── routes_auth.py
│       ├── routes_automation.py
│       └── routes_enlistment.py
│
├── core/                      # ⚙️ Configuración y servicios centrales
│   ├── readme.md
│   ├── config.py              # Variables de entorno
│   ├── auth_ldap.py           # Autenticación LDAP
│   ├── jwt_manager.py         # Gestión de JWT
│   ├── logging_config.py      # Configuración de logs
│   ├── redis_cache.py         # Cliente Redis
│   ├── security.py            # Utilidades de seguridad
│   └── utils.py               # Utilidades (IP, device)
│
├── db/                        # 💾 Conexiones a bases de datos
│   ├── readme.md
│   ├── base_model.py          # Base para modelos ORM
│   ├── postgres.py            # PostgreSQL
│   ├── mongodb_client.py      # MongoDB
│   ├── oracle_fenix_session.py
│   ├── oracle_mss_session.py
│   └── oracle_siebel_session.py
│
├── decorators/                # 🎨 Middleware y decoradores
│   ├── readme.md
│   ├── auth_decorator.py      # jwt_required
│   └── cache_decorator.py     # @cache
│
├── migrations/                # 🔄 Migraciones de BD
│   ├── readme.md
│   └── create_*_tables.py
│
├── models/                    # 📊 Modelos ORM (SQLAlchemy)
│   ├── readme.md
│   ├── user_model.py
│   ├── menu_model.py
│   ├── enlistment_manager_model.py
│   └── ...
│
├── repositories/              # 🗄️ Acceso a datos
│   ├── readme.md
│   ├── user_repository.py
│   ├── automation_repository.py
│   ├── enlistment_repository.py
│   └── log_repository.py
│
├── schemas/                   # ✅ Validación Pydantic
│   ├── readme.md
│   ├── auth_schema.py
│   ├── user_schema.py
│   ├── automation_schema.py
│   └── enlistment_schema.py
│
├── services/                  # 🧠 Lógica de negocio
│   ├── readme.md
│   ├── user_service.py
│   ├── automation_service.py
│   └── enlistment_service.py
│
└── utils/                     # 🔧 Utilidades y helpers
    ├── readme.md
    ├── constants.py
    └── hash_utils.py
```

---

## 🛠️ Tecnologías Utilizadas

### Backend Framework
- **FastAPI** 0.100+: Framework web moderno y rápido
- **Uvicorn**: ASGI server para FastAPI
- **Python** 3.11+: Lenguaje de programación

### Bases de Datos
- **PostgreSQL**: Base de datos principal (usuarios, configuración)
- **MongoDB**: Logs y datos no estructurados
- **Oracle**: Datos de Fenix, MSS y Siebel (Standby)

### ORM y Validación
- **SQLAlchemy** 2.0+: ORM para bases de datos relacionales
- **Pydantic** 2.0+: Validación de datos y serialización

### Autenticación y Seguridad
- **LDAP3**: Autenticación contra Active Directory
- **python-jose**: Manejo de JWT
- **Redis**: Caché y gestión de sesiones

### Herramientas de Desarrollo
- **Docker**: Containerización
- **pytest**: Testing
- **pylint/black**: Linting y formateo

---

## 👨‍💻 Guía de Desarrollo

### 1. Agregar un Nuevo Endpoint

#### Paso 1: Crear Schema
```python
# app/schemas/producto_schema.py
from pydantic import BaseModel, Field

class ProductoCreate(BaseModel):
    nombre: str = Field(..., min_length=3)
    precio: float = Field(..., gt=0)
```

#### Paso 2: Crear/Actualizar Model
```python
# app/models/producto_model.py
from sqlalchemy import Column, Integer, String, Numeric
from app.db.base_model import Base

class Producto(Base):
    __tablename__ = "productos"
    
    id = Column(Integer, primary_key=True)
    nombre = Column(String(200), nullable=False)
    precio = Column(Numeric(10, 2), nullable=False)
```

#### Paso 3: Crear Repository
```python
# app/repositories/producto_repository.py
from app.db.postgres import SessionLocalPG
from app.models.producto_model import Producto

class ProductoRepository:
    def __init__(self):
        self.db = SessionLocalPG()
    
    def create(self, producto_data: dict):
        producto = Producto(**producto_data)
        self.db.add(producto)
        self.db.commit()
        self.db.refresh(producto)
        return producto
```

#### Paso 4: Crear Service
```python
# app/services/producto_service.py
from app.repositories.producto_repository import ProductoRepository

class ProductoService:
    def __init__(self):
        self.repo = ProductoRepository()
    
    def crear_producto(self, producto_data):
        # Lógica de negocio aquí
        return self.repo.create(producto_data)
```

#### Paso 5: Crear Route
```python
# app/api/v1/routes_producto.py
from fastapi import APIRouter, Depends
from app.decorators.auth_decorator import jwt_required
from app.schemas.producto_schema import ProductoCreate
from app.services.producto_service import ProductoService

router = APIRouter(prefix="/api/v1/productos", tags=["productos"])
service = ProductoService()

@router.post("/", dependencies=[Depends(jwt_required)])
async def crear_producto(payload: ProductoCreate):
    return service.crear_producto(payload.dict())
```

#### Paso 6: Registrar Route en main.py
```python
# app/main.py
from app.api.v1 import routes_producto

app.include_router(routes_producto.router)
```

### 2. Ejecutar Migraciones

```bash
# Crear migración
python -m app.migrations.create_producto_tables

# Verificar tablas creadas
# Conectarse a PostgreSQL y verificar
```

### 3. Testing

```python
# tests/test_producto_service.py
import pytest
from app.services.producto_service import ProductoService

def test_crear_producto():
    service = ProductoService()
    producto_data = {
        "nombre": "Producto Test",
        "precio": 100.50
    }
    
    producto = service.crear_producto(producto_data)
    
    assert producto.nombre == "Producto Test"
    assert producto.precio == 100.50
```

---

## 📐 Convenciones y Estándares

### Nomenclatura

#### Archivos
- **snake_case**: `user_service.py`, `routes_auth.py`
- **Sufijos descriptivos**: `*_model.py`, `*_repository.py`, `*_service.py`

#### Clases
- **PascalCase**: `UserService`, `ProductoRepository`
- **Sufijos descriptivos**: `*Service`, `*Repository`, `*Schema`

#### Funciones y Variables
- **snake_case**: `get_user_by_id()`, `user_data`
- **Verbos para funciones**: `create_`, `get_`, `update_`, `delete_`

#### Constantes
- **SCREAMING_SNAKE_CASE**: `MAX_PAGE_SIZE`, `API_TIMEOUT`

### Estructura de Código

#### Services
```python
class ExampleService:
    """Docstring describiendo el servicio."""
    
    def __init__(self):
        """Inicializar repositories necesarios."""
        self.repo = ExampleRepository()
    
    def public_method(self, param: str) -> dict:
        """
        Método público (caso de uso).
        
        Args:
            param: Descripción
        
        Returns:
            Descripción del retorno
        """
        # 1️⃣ Validaciones
        # 2️⃣ Lógica de negocio
        # 3️⃣ Llamadas a repositories
        # 4️⃣ Transformaciones
        # 5️⃣ Retorno
        pass
    
    def _private_helper(self):
        """Método privado (helper)."""
        pass
```

#### Repositories
```python
class ExampleRepository:
    """Docstring describiendo el repository."""
    
    def __init__(self):
        """Inicializar conexión a BD."""
        self.db = SessionLocal()
    
    def __del__(self):
        """Cerrar conexión al destruir."""
        if hasattr(self, 'db'):
            self.db.close()
    
    def get_by_id(self, id: int):
        """Query específico."""
        return self.db.query(Model).filter(Model.id == id).first()
```

### Manejo de Errores

```python
# En Services
try:
    # Lógica
    result = self.repo.do_something()
    return result
except HTTPException:
    # Re-lanzar HTTPException
    raise
except Exception as e:
    # Loggear y lanzar HTTPException
    logger.error(f"Error: {e}")
    raise HTTPException(500, "Error interno")

# En Repositories
try:
    # Query
    self.db.commit()
except Exception as e:
    self.db.rollback()
    logger.error(f"Error: {e}")
    raise
```

### Logging

```python
import logging

logger = logging.getLogger("module_name")

# Niveles
logger.debug("Información de debug")
logger.info("Operación normal")
logger.warning("Advertencia")
logger.error("Error recuperable")
logger.critical("Error crítico")
```

---

## 📊 Diagramas

### Diagrama de Arquitectura General

```
┌─────────────────────────────────────────────────────────┐
│                      CLIENTE                            │
│                   (Frontend/API Client)                  │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP/HTTPS
                       ↓
┌─────────────────────────────────────────────────────────┐
│                   FASTAPI APP                           │
│  ┌───────────────────────────────────────────────────┐ │
│  │            API ROUTES (v1/)                       │ │
│  │  • routes_auth.py    • routes_automation.py      │ │
│  │  • routes_enlistment.py                          │ │
│  └─────────────┬─────────────────────────────────────┘ │
│                ↓                                         │
│  ┌───────────────────────────────────────────────────┐ │
│  │         DECORATORS (Middleware)                   │ │
│  │  • jwt_required  • @cache                        │ │
│  └─────────────┬─────────────────────────────────────┘ │
│                ↓                                         │
│  ┌───────────────────────────────────────────────────┐ │
│  │              SERVICES                             │ │
│  │  • UserService  • AutomationService              │ │
│  │  • EnlistmentService                             │ │
│  └─────────────┬─────────────────────────────────────┘ │
│                ↓                                         │
│  ┌───────────────────────────────────────────────────┐ │
│  │            REPOSITORIES                           │ │
│  │  • UserRepository  • AutomationRepository        │ │
│  │  • EnlistmentRepository  • LogRepository         │ │
│  └─────────────┬─────────────────────────────────────┘ │
└────────────────┼─────────────────────────────────────────┘
                 │
     ┌───────────┼───────────┐
     ↓           ↓           ↓
┌─────────┐ ┌─────────┐ ┌─────────┐
│PostgreSQL │ │ MongoDB │ │  Oracle │
│ (Main DB) │ │ (Logs)  │ │ (Fenix/ │
│           │ │         │ │MSS/Siebel)│
└─────────┘ └─────────┘ └─────────┘

     ┌───────────┐
     │   Redis   │
     │  (Cache)  │
     └───────────┘

     ┌───────────┐
     │   LDAP    │
     │  (Auth)   │
     └───────────┘
```

### Diagrama de Flujo: Autenticación

```
┌──────────┐
│  Cliente │
└────┬─────┘
     │ POST /login
     ↓
┌─────────────────────┐
│   routes_auth.py    │ ← Valida LoginRequest schema
└────┬────────────────┘
     │ user_service.login()
     ↓
┌─────────────────────┐
│   UserService       │ 
└────┬────────────────┘
     │ 1. authenticate_user()
     ↓
┌─────────────────────┐
│    auth_ldap.py     │ ← Valida contra LDAP
└────┬────────────────┘
     │ ✅ Credenciales válidas
     ↓
┌─────────────────────┐
│   UserService       │
└────┬────────────────┘
     │ 2. user_repo.get_by_login()
     ↓
┌─────────────────────┐
│  UserRepository     │ ← Query a PostgreSQL
└────┬────────────────┘
     │ User object
     ↓
┌─────────────────────┐
│   UserService       │
└────┬────────────────┘
     │ 3. create_jwt_token()
     ↓
┌─────────────────────┐
│   jwt_manager.py    │ ← Genera access + refresh tokens
└────┬────────────────┘
     │ tokens
     ↓
┌─────────────────────┐
│   UserService       │
└────┬────────────────┘
     │ 4. redis_client.setex()
     ↓
┌─────────────────────┐
│   Redis             │ ← Guarda refresh token
└────┬────────────────┘
     │ OK
     ↓
┌─────────────────────┐
│   routes_auth.py    │
└────┬────────────────┘
     │ UserRespWithTokenAndMenu schema
     ↓
┌──────────┐
│  Cliente │ ← { user, access_token, refresh_token }
└──────────┘
```

---

## 🔐 Seguridad

### Autenticación
- **LDAP**: Autenticación central contra Active Directory
- **JWT**: Tokens de acceso (corta duración) y refresh (larga duración)
- **Single Session**: Solo una sesión activa por usuario

### Autorización
- **jwt_required decorator**: Protege endpoints
- **Roles y permisos**: Basado en perfiles de usuario

### Datos Sensibles
- **No loggear**: Contraseñas, tokens completos
- **Variables de entorno**: Para credenciales y secrets
- **Blacklist**: Tokens revocados en Redis

---

## 📚 Recursos y Referencias

### Documentación de Carpetas
Cada carpeta tiene su propio `readme.md` con documentación detallada:
- [API](./api/readme.md) - Endpoints HTTP
- [Core](./core/readme.md) - Configuración central
- [DB](./db/readme.md) - Conexiones a BD
- [Decorators](./decorators/readme.md) - Middleware
- [Migrations](./migrations/readme.md) - Migraciones
- [Models](./models/readme.md) - Modelos ORM
- [Repositories](./repositories/readme.md) - Acceso a datos
- [Schemas](./schemas/readme.md) - Validación
- [Services](./services/readme.md) - Lógica de negocio
- [Utils](./utils/readme.md) - Utilidades

### Enlaces Externos
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy ORM](https://docs.sqlalchemy.org/)
- [Pydantic](https://docs.pydantic.dev/)
- [Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)

---

## 🤝 Contribuyendo

### Antes de Contribuir
1. Leer este documento completo
2. Revisar documentación específica de la carpeta donde trabajarás
3. Seguir convenciones de nomenclatura y estructura
4. Agregar tests para código nuevo
5. Documentar funciones y clases con docstrings

### Pull Request Checklist
- [ ] Código sigue convenciones del proyecto
- [ ] Tests agregados y pasando
- [ ] Documentación actualizada
- [ ] Sin errores de linting
- [ ] Logs apropiados agregados
- [ ] Manejo de errores implementado

---

## 📞 Contacto y Soporte

Para dudas sobre la arquitectura o contribuciones:
- Revisar primero la documentación en cada carpeta
- Consultar con el equipo de desarrollo
- Seguir las buenas prácticas documentadas

---

**Última actualización**: 2026-02-17  
**Versión**: 2.0.0
