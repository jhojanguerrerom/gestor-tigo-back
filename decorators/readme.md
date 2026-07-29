# Decorators (Middleware y Decoradores)

## 📋 Descripción
Esta carpeta contiene **decoradores** y **middleware** reutilizables para funcionalidades transversales como autenticación JWT y caché. Se aplican a las rutas de la API para agregar comportamiento sin modificar la lógica de negocio.

## 🔗 Conexiones
- **Usado por**: API routes
- **Usa**: 
  - Core/jwt_manager.py (validación de tokens)
  - Core/redis_cache.py (verificar blacklist, caché)
  - Repositories/user_repository.py (obtener datos de usuario)
- **Inyecta en**: Request.state (datos del usuario autenticado)

## 🎯 Responsabilidades
1. **Autenticación JWT** (auth_decorator.py)
   - Validar tokens de acceso
   - Verificar que no estén en blacklist (revocados)
   - Inyectar datos del usuario en `request.state`
   - Proteger endpoints que requieren autenticación

2. **Caché** (cache_decorator.py)
   - Cachear resultados de funciones costosas
   - Usar Redis para almacenamiento temporal
   - Reducir carga en bases de datos

## 📂 Estructura
```
decorators/
├── __init__.py
├── readme.md
├── auth_decorator.py    # jwt_required, get_current_user
└── cache_decorator.py   # @cache(ttl=60)
```

## 🔄 Flujo en la Arquitectura
```
Request → API Route → jwt_required (decorator)
                           ↓
                    Validar token (jwt_manager)
                           ↓
                    Verificar blacklist (Redis)
                           ↓
                    Obtener datos usuario (repository)
                           ↓
                    Inyectar en request.state
                           ↓
                    Ejecutar endpoint

Request → API Route → @cache decorator
                           ↓
                    Buscar en Redis cache
                           ↓
                    ¿Existe? → Retornar cached
                           ↓
                    No existe → Ejecutar función
                           ↓
                    Guardar resultado en cache
                           ↓
                    Retornar resultado
```

## 📝 Ejemplos de Implementación

### 1. Autenticación JWT (auth_decorator.py)

#### Implementación del decorador:
```python
# app/decorators/auth_decorator.py
import logging
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer
from app.core.jwt_manager import verify_jwt_token
from app.core.redis_cache import redis_client
from app.repositories.user_repository import UserRepository

security = HTTPBearer()
logger = logging.getLogger("jwt_required")

async def jwt_required(request: Request, credentials=Depends(security)):
    """
    Middleware de autenticación JWT.
    Valida el token, verifica que no esté revocado y carga datos del usuario.
    """
    token = credentials.credentials
    
    try:
        # 1️⃣ Validar token
        payload = verify_jwt_token(token, expected_type="access")
        if not payload:
            raise HTTPException(status_code=401, detail="Token inválido o expirado")
        
        jti = payload.get("jti")
        user_id = payload.get("sub")
        
        if not user_id or not jti:
            raise HTTPException(status_code=401, detail="Token sin datos de sesión")
        
        # 2️⃣ Verificar blacklist (tokens revocados)
        is_blacklisted = await redis_client.exists(f"blacklist:{jti}")
        if is_blacklisted:
            logger.warning(f"Token revocado detectado para usuario {user_id}")
            raise HTTPException(status_code=401, detail="Token revocado")
        
        # 3️⃣ Obtener datos del usuario
        user_data = UserRepository().get_by_id(user_id)
        if not user_data:
            raise HTTPException(status_code=401, detail="Usuario no encontrado")
        
        # 4️⃣ Inyectar datos en request.state
        request.state.payload = {
            "user_login": user_data.login,
            "user_name": user_data.full_name,
            "user_dni": user_data.user_identify,
            "user_id": user_id
        }
        
        request.state.user = {
            "id": user_id,
            "jti": jti
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en jwt_required: {e}")
        raise HTTPException(status_code=401, detail="Error de autenticación")

async def get_current_user(request: Request):
    """
    Extrae el usuario del request.state (debe usarse después de jwt_required).
    """
    if not hasattr(request.state, "payload"):
        raise HTTPException(status_code=401, detail="Usuario no autenticado")
    return request.state.payload
```

#### Uso en routes:
```python
# app/api/v1/routes_ejemplo.py
from fastapi import APIRouter, Depends, Request
from app.decorators.auth_decorator import jwt_required, get_current_user

router = APIRouter(prefix="/api/v1/ejemplo", tags=["ejemplo"])

# Opción 1: Solo proteger (datos en request.state)
@router.get("/protected", dependencies=[Depends(jwt_required)])
async def endpoint_protegido(request: Request):
    user_id = request.state.user["id"]
    user_name = request.state.payload["user_name"]
    return {"message": f"Hola {user_name}", "user_id": user_id}

# Opción 2: Obtener usuario explícitamente
@router.get("/profile")
async def get_profile(
    request: Request,
    current_user=Depends(get_current_user)
):
    # current_user tiene: user_login, user_name, user_dni, user_id
    return {"user": current_user}

# Opción 3: Combinar ambos
@router.post("/create", dependencies=[Depends(jwt_required)])
async def create_something(
    request: Request,
    payload: CreateSchema,
    current_user=Depends(get_current_user)
):
    # Acceder directamente a current_user
    created_by = current_user["user_id"]
    result = service.create(payload, created_by)
    return result
```

### 2. Caché (cache_decorator.py)

#### Implementación del decorador:
```python
# app/decorators/cache_decorator.py
from functools import wraps
import json
from app.core.redis_cache import redis_client
import asyncio
import logging

logger = logging.getLogger("cache_decorator")

def cache(ttl=60):
    """
    Decorador para cachear resultados de funciones async.
    
    Args:
        ttl: Tiempo de vida en segundos (default: 60)
    
    Uso:
        @cache(ttl=300)
        async def get_data(user_id: int):
            return await expensive_operation(user_id)
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generar key única basada en función y parámetros
            key = f"cache:{func.__name__}:{json.dumps({'args': args, 'kwargs': kwargs}, default=str)}"
            
            try:
                # Intentar obtener de cache
                cached = await redis_client.get(key)
                if cached:
                    logger.debug(f"Cache HIT: {key}")
                    return json.loads(cached)
            except Exception as e:
                logger.warning(f"Error al leer cache: {e}")
                cached = None
            
            # Cache MISS: ejecutar función
            logger.debug(f"Cache MISS: {key}")
            result = await func(*args, **kwargs)
            
            # Guardar en cache
            try:
                await redis_client.setex(
                    key,
                    ttl,
                    json.dumps(result, default=str)
                )
            except Exception as e:
                logger.warning(f"Error al guardar en cache: {e}")
            
            return result
        return wrapper
    return decorator
```

#### Uso en services o routes:
```python
# app/services/user_service.py
from app.decorators.cache_decorator import cache

class UserService:
    @cache(ttl=300)  # Cachear por 5 minutos
    async def get_user_profile(self, user_id: int):
        """
        Obtiene el perfil de usuario (cacheado).
        Primera llamada: consulta DB
        Siguientes llamadas (5 min): retorna desde cache
        """
        user = self.repository.get_by_id(user_id)
        permissions = self.repository.get_permissions(user_id)
        return {
            "user": user.to_dict(),
            "permissions": permissions
        }
    
    @cache(ttl=3600)  # Cachear por 1 hora
    async def get_menu_structure(self):
        """
        Obtiene estructura de menús (cambia poco).
        """
        menus = self.repository.get_all_menus()
        return menus

# En routes:
@router.get("/profile/{user_id}")
async def get_profile(user_id: int):
    # Primera llamada tarda (query DB)
    # Siguientes llamadas instantáneas (desde Redis)
    profile = await service.get_user_profile(user_id)
    return profile
```

### 3. Invalidación de Caché
```python
# Opción 1: Invalidar manualmente
from app.core.redis_cache import redis_client

async def update_user(user_id: int, data: dict):
    # Actualizar usuario
    updated_user = repository.update(user_id, data)
    
    # Invalidar cache para ese usuario
    cache_key = f"cache:get_user_profile:{json.dumps({'args': (user_id,), 'kwargs': {}}, default=str)}"
    await redis_client.delete(cache_key)
    
    return updated_user

# Opción 2: Patrón de keys para invalidar todos los caches de un tipo
await redis_client.delete_pattern("cache:get_user_*")
```

## ✅ Buenas Prácticas

### 1. **Autenticación**
- ✅ Verificar siempre la blacklist de tokens revocados
- ✅ Inyectar datos del usuario en `request.state` para fácil acceso
- ✅ Loggear intentos de acceso con tokens inválidos (seguridad)
- ✅ Usar `dependencies=[Depends(jwt_required)]` para proteger rutas
- ❌ No validar tokens manualmente en cada ruta

### 2. **Caché**
- ✅ Usar TTL apropiados (datos estáticos: largo, datos dinámicos: corto)
- ✅ Cachear solo operaciones costosas (queries complejos, APIs externas)
- ✅ Generar keys únicas e informativas
- ✅ Invalidar cache cuando los datos cambien
- ❌ No cachear datos sensibles o en constante cambio

### 3. **Manejo de Errores**
- ✅ Manejar errores de Redis gracefully (no debe romper la app)
- ✅ Loggear errores para debugging
- ✅ Retornar respuestas HTTP apropiadas (401, 403)

### 4. **Performance**
- ✅ Cache keys deben ser cortas pero descriptivas
- ✅ Usar TTL para limpieza automática
- ✅ Monitorear hit rate del cache

## 🚫 Anti-patrones (Evitar)

```python
# ❌ MAL: No usar el decorador, validar manualmente
@router.get("/data")
async def get_data(request: Request):
    token = request.headers.get("Authorization")
    if not token:
        raise HTTPException(401)
    # Validación manual... ❌

# ✅ BIEN: Usar el decorador
@router.get("/data", dependencies=[Depends(jwt_required)])
async def get_data(request: Request):
    user_id = request.state.user["id"]
    # ...


# ❌ MAL: Cachear sin TTL o con TTL muy largo
@cache(ttl=86400*365)  # 1 año! ❌
async def get_user_data(user_id):
    # Datos pueden quedar obsoletos
    ...

# ✅ BIEN: TTL razonable según naturaleza de los datos
@cache(ttl=300)  # 5 minutos
async def get_user_data(user_id):
    ...


# ❌ MAL: No manejar errores de cache
@cache(ttl=60)
async def expensive_function():
    # Si Redis falla, la app se rompe ❌
    ...

# ✅ BIEN: Manejar errores (ya implementado en el decorador)
# El decorador maneja errores y continúa sin cache si falla Redis


# ❌ MAL: No invalidar cache al actualizar
async def update_user(user_id, data):
    repository.update(user_id, data)
    return "OK"  # ❌ Cache queda desactualizado

# ✅ BIEN: Invalidar cache después de actualizar
async def update_user(user_id, data):
    repository.update(user_id, data)
    cache_key = f"cache:get_user:{user_id}"
    await redis_client.delete(cache_key)
    return "OK"
```

## 🔧 Testing

### Test de autenticación:
```python
# test_auth_decorator.py
from fastapi.testclient import TestClient

def test_protected_endpoint_without_token():
    response = client.get("/api/v1/protected")
    assert response.status_code == 401

def test_protected_endpoint_with_valid_token():
    token = get_valid_token()
    response = client.get(
        "/api/v1/protected",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200

def test_protected_endpoint_with_revoked_token():
    token = get_revoked_token()
    response = client.get(
        "/api/v1/protected",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 401
```

## 📚 Recursos Adicionales
- [FastAPI Dependencies](https://fastapi.tiangolo.com/tutorial/dependencies/)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [Python Decorators](https://realpython.com/primer-on-python-decorators/)
- [Caching Strategies](https://aws.amazon.com/caching/best-practices/)
