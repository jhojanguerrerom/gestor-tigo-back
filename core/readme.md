# Core (Configuración y Servicios Centrales)

## 📋 Descripción
Esta carpeta contiene la **configuración central** y **servicios transversales** de la aplicación. Incluye autenticación, configuración de variables de entorno, manejo de JWT, logging, caché con Redis y utilidades de seguridad.

## 🔗 Conexiones
- **Usado por**: Toda la aplicación (API, Services, Decorators, Repositories)
- **Conecta con**: 
  - LDAP (autenticación de usuarios)
  - Redis (caché y blacklist de tokens)
  - Variables de entorno (.env)

## 🎯 Responsabilidades
1. **Configuración** global de la aplicación (config.py)
2. **Autenticación LDAP** (auth_ldap.py)
3. **Gestión de JWT** (jwt_manager.py) - creación, validación, revocación
4. **Logging** centralizado (logging_config.py)
5. **Administración de caché** Redis (redis_cache.py)
6. **Seguridad** y utilidades (security.py, utils.py)

## 📂 Estructura
```
core/
├── __init__.py
├── readme.md
├── auth_ldap.py          # Autenticación con LDAP
├── config.py             # Variables de entorno y configuración
├── jwt_manager.py        # Crear, validar y revocar tokens JWT
├── logging_config.py     # Configuración de logs
├── redis_cache.py        # Cliente Redis para caché
├── security.py           # Utilidades de seguridad
└── utils.py              # Funciones utilitarias (IP, device, etc.)
```

## 🔄 Flujo en la Arquitectura
```
Startup → config.py (cargar variables de entorno)
             ↓
Login → auth_ldap.py (validar contra LDAP)
             ↓
      jwt_manager.py (crear access + refresh tokens)
             ↓
      redis_cache.py (guardar refresh token)
             ↓
Request → jwt_required (decorator) → jwt_manager.py (validar token)
                                           ↓
                                    redis_cache.py (verificar blacklist)
```

## 📝 Ejemplos de Implementación

### 1. Configuración (config.py)
```python
# app/core/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # App
    APP_NAME: str = "Gestor API"
    APP_ENV: str = "development"  # development, production
    
    # JWT
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_EXPIRE_MINUTES: int = 10080  # 7 días
    
    # Database
    POSTGRES_URL: str
    MONGO_URL: str
    ORACLE_FENIX_URL: str
    
    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    
    # LDAP (ya configurado)
    LDAP_SERVER: str = "ldap://10.100.65.10:389"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
```

### 2. Autenticación LDAP (auth_ldap.py)
```python
# Uso en services/user_service.py
from app.core.auth_ldap import authenticate_user

async def login(self, username: str, password: str):
    # Autenticar contra LDAP
    ldap_user = authenticate_user(username, password)
    
    if not ldap_user:
        raise HTTPException(401, "Credenciales inválidas")
    
    # Continuar con lógica de negocio...
```

### 3. JWT Manager (jwt_manager.py)
```python
# Uso en services/user_service.py
from app.core.jwt_manager import create_jwt_token, verify_jwt_token

# Crear tokens
access_token, access_jti, access_exp = create_jwt_token(
    subject=str(user.id),
    token_type="access"
)

refresh_token, refresh_jti, refresh_exp = create_jwt_token(
    subject=str(user.id),
    token_type="refresh"
)

# Validar token
payload = verify_jwt_token(token, expected_type="access")
if payload:
    user_id = payload["sub"]
    jti = payload["jti"]
```

### 4. Redis Cache (redis_cache.py)
```python
# Uso en services o decorators
from app.core.redis_cache import redis_client

# Guardar en caché
await redis_client.setex(
    f"refresh_token:{user_id}",
    ttl=604800,  # 7 días
    value=refresh_jti
)

# Obtener de caché
cached_value = await redis_client.get(f"refresh_token:{user_id}")

# Verificar existencia (blacklist)
is_blacklisted = await redis_client.exists(f"blacklist:{jti}")

# Eliminar de caché
await redis_client.delete(f"refresh_token:{user_id}")

# Agregar a blacklist
await redis_client.setex(
    f"blacklist:{jti}",
    ttl=remaining_time,
    value="revoked"
)
```

### 5. Logging (logging_config.py)
```python
# Ya configurado en main.py, usar en cualquier módulo:
import logging

logger = logging.getLogger("mi_modulo")

logger.info("Operación exitosa")
logger.warning("Advertencia")
logger.error("Error al procesar")
logger.debug("Información de depuración")
```

### 6. Utilidades (utils.py)
```python
# Uso en routes o services
from app.core.utils import get_client_ip, get_client_device

@router.post("/login")
async def login(request: Request, payload: LoginRequest):
    ip = get_client_ip(request)
    device = get_client_device(request)
    
    logger.info(f"Login desde IP: {ip}, Dispositivo: {device}")
```

## ✅ Buenas Prácticas

### 1. **Configuración**
- ✅ Usar variables de entorno para valores sensibles y configurables
- ✅ Nunca hardcodear credenciales o URLs
- ✅ Definir valores por defecto razonables
- ✅ Usar Pydantic Settings para validación automática
- ❌ No commitear archivos .env al repositorio

### 2. **JWT**
- ✅ Usar tokens de corta duración (access) y larga duración (refresh)
- ✅ Incluir `jti` (JWT ID) para rastrear y revocar tokens
- ✅ Validar `type` del token (access vs refresh)
- ✅ Implementar blacklist para logout efectivo
- ❌ No exponer JWT_SECRET en logs o respuestas

### 3. **Redis**
- ✅ Usar TTL (Time To Live) para limpieza automática
- ✅ Usar prefijos descriptivos en las keys (`refresh_token:`, `blacklist:`, `cache:`)
- ✅ Manejar errores de conexión gracefully
- ✅ Cerrar conexiones apropiadamente

### 4. **Logging**
- ✅ Usar niveles apropiados (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- ✅ Incluir contexto relevante en los mensajes
- ✅ No loggear información sensible (passwords, tokens completos)
- ✅ Usar formato estructurado (JSON) en producción

### 5. **Autenticación LDAP**
- ✅ Validar credenciales antes de crear tokens
- ✅ Manejar timeouts y errores de conexión
- ✅ Loggear intentos fallidos (para seguridad)
- ❌ No guardar contraseñas en ningún lado

### 6. **Seguridad**
- ✅ Validar y sanitizar todas las entradas
- ✅ Usar algoritmos criptográficos fuertes (HS256, RS256)
- ✅ Rotar secretos regularmente
- ✅ Implementar rate limiting si es necesario

## 🚫 Anti-patrones (Evitar)

```python
# ❌ MAL: Hardcodear configuración
JWT_SECRET = "mi_secreto_123"  # ❌ Nunca!

# ✅ BIEN: Usar variables de entorno
from app.core.config import settings
jwt_secret = settings.JWT_SECRET


# ❌ MAL: No validar tipo de token
payload = verify_jwt_token(token)  # ¿Es access o refresh?

# ✅ BIEN: Validar tipo esperado
payload = verify_jwt_token(token, expected_type="access")


# ❌ MAL: No manejar errores de Redis
cached = await redis_client.get(key)  # ¿Y si falla?

# ✅ BIEN: Manejar errores
try:
    cached = await redis_client.get(key)
except Exception as e:
    logger.error(f"Error Redis: {e}")
    cached = None


# ❌ MAL: Loggear información sensible
logger.info(f"Login exitoso: {username}/{password}")  # ❌ Nunca!

# ✅ BIEN: Loggear sin información sensible
logger.info(f"Login exitoso para usuario: {username}")
```

## 🔧 Configuración Inicial

### 1. Crear archivo .env
```bash
# .env
APP_ENV=development

JWT_SECRET=tu_secreto_muy_seguro_aqui_cambiar_en_produccion
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=60
JWT_REFRESH_EXPIRE_MINUTES=10080

POSTGRES_URL=postgresql://user:pass@localhost:5432/gestor
MONGO_URL=mongodb://localhost:27017/

REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
```

### 2. Instalar dependencias
```bash
pip install python-dotenv pydantic-settings python-jose[cryptography] ldap3 redis
```

## 📚 Recursos Adicionales
- [JWT Best Practices](https://auth0.com/blog/a-look-at-the-latest-draft-for-jwt-bcp/)
- [LDAP3 Documentation](https://ldap3.readthedocs.io/)
- [Redis Python Client](https://redis-py.readthedocs.io/)
- [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
