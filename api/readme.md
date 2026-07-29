# API (Routes)

## 📋 Descripción
Esta carpeta contiene todos los **endpoints REST** de la aplicación. Se encarga de recibir las peticiones HTTP, validar datos de entrada usando schemas, delegar la lógica a los servicios y retornar respuestas al cliente.

## 🔗 Conexiones
- **Consume**: Services (lógica de negocio)
- **Usa**: Schemas (validación de entrada/salida)
- **Protege con**: Decorators (autenticación JWT, caché)
- **Registra en**: main.py (inclusión de routers en la app FastAPI)

## 🎯 Responsabilidades
1. **Definir endpoints** HTTP (GET, POST, PUT, DELETE)
2. **Validar datos de entrada** usando Pydantic schemas
3. **Aplicar middleware** de autenticación (JWT)
4. **Delegar lógica** a la capa de servicios
5. **Retornar respuestas** estructuradas al cliente
6. **Manejo de errores** HTTP con códigos de estado apropiados
7. **Documentación automática** con OpenAPI/Swagger

## 📂 Estructura
```
api/
├── __init__.py
├── readme.md
└── v1/                    # Versionado de API
    ├── __init__.py
    ├── routes_auth.py     # Endpoints de autenticación
    ├── routes_automation.py  # Endpoints de automatización
    └── routes_enlistment.py  # Endpoints de enlistment manager
```

## 🔄 Flujo en la Arquitectura
```
Cliente HTTP → API (Routes) → Services → Repositories → DB/APIs Externas
                   ↓
              Schemas (validación)
                   ↓
              Decorators (auth/cache)
```

## 📝 Ejemplo de Implementación

### 1. Crear nuevo archivo de rutas
```python
# app/api/v1/routes_ejemplo.py
import logging
from fastapi import APIRouter, Depends, HTTPException, Request, status
from app.decorators.auth_decorator import jwt_required
from app.schemas.ejemplo_schema import EjemploRequest, EjemploResponse
from app.services.ejemplo_service import EjemploService

router = APIRouter(prefix="/api/v1/ejemplo", tags=["ejemplo"])
service = EjemploService()
logger = logging.getLogger("routes_ejemplo")

@router.get("/", response_model=list[EjemploResponse])
async def listar_ejemplos(request: Request, dependencies=[Depends(jwt_required)]):
    """
    Lista todos los ejemplos.
    🔒 Requiere autenticación JWT.
    """
    try:
        logger.info("Listando ejemplos")
        user_id = request.state.user["id"]  # Obtener user del token
        ejemplos = await service.listar_ejemplos(user_id)
        return ejemplos
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error al listar ejemplos: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al listar ejemplos"
        )

@router.post("/", response_model=EjemploResponse, status_code=status.HTTP_201_CREATED)
async def crear_ejemplo(
    request: Request,
    payload: EjemploRequest,
    dependencies=[Depends(jwt_required)]
):
    """
    Crea un nuevo ejemplo.
    🔒 Requiere autenticación JWT.
    """
    try:
        logger.info(f"Creando ejemplo: {payload.nombre}")
        user_id = request.state.user["id"]
        ejemplo = await service.crear_ejemplo(payload, user_id)
        return ejemplo
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error al crear ejemplo: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al crear ejemplo"
        )

@router.get("/{ejemplo_id}", response_model=EjemploResponse)
async def obtener_ejemplo(
    ejemplo_id: int,
    request: Request,
    dependencies=[Depends(jwt_required)]
):
    """Obtiene un ejemplo por ID."""
    try:
        ejemplo = await service.obtener_ejemplo(ejemplo_id)
        if not ejemplo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ejemplo no encontrado"
            )
        return ejemplo
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error al obtener ejemplo: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener ejemplo"
        )

@router.put("/{ejemplo_id}", response_model=EjemploResponse)
async def actualizar_ejemplo(
    ejemplo_id: int,
    payload: EjemploRequest,
    request: Request,
    dependencies=[Depends(jwt_required)]
):
    """Actualiza un ejemplo existente."""
    try:
        ejemplo = await service.actualizar_ejemplo(ejemplo_id, payload)
        return ejemplo
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error al actualizar ejemplo: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al actualizar ejemplo"
        )

@router.delete("/{ejemplo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_ejemplo(
    ejemplo_id: int,
    request: Request,
    dependencies=[Depends(jwt_required)]
):
    """Elimina un ejemplo."""
    try:
        await service.eliminar_ejemplo(ejemplo_id)
        return None
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error al eliminar ejemplo: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al eliminar ejemplo"
        )
```

### 2. Registrar el router en main.py
```python
# app/main.py
from app.api.v1 import routes_ejemplo

app.include_router(routes_ejemplo.router)
```

## ✅ Buenas Prácticas

### 1. **Organización**
- ✅ Un archivo por recurso/dominio (routes_users.py, routes_products.py)
- ✅ Usar prefijos descriptivos (`/api/v1/users`)
- ✅ Agrupar con tags para documentación automática

### 2. **Autenticación**
- ✅ Usar `dependencies=[Depends(jwt_required)]` para rutas protegidas
- ✅ Acceder al usuario desde `request.state.user`
- ❌ No validar tokens manualmente en las rutas

### 3. **Validación**
- ✅ Usar Pydantic schemas para request/response
- ✅ Definir `response_model` en el decorador
- ✅ Usar status codes apropiados (201 para crear, 204 para delete sin contenido)

### 4. **Manejo de Errores**
- ✅ Capturar HTTPException y re-lanzarlas
- ✅ Loggear errores antes de lanzar excepciones
- ✅ Retornar mensajes de error claros y seguros (sin exponer detalles internos)
- ✅ Usar códigos HTTP estándar (404, 400, 401, 403, 500)

### 5. **Logging**
- ✅ Loggear inicio y fin de operaciones importantes
- ✅ Usar niveles apropiados (INFO, WARNING, ERROR)
- ✅ Incluir contexto relevante en los logs

### 6. **Documentación**
- ✅ Agregar docstrings descriptivos a cada endpoint
- ✅ Documentar parámetros, respuestas y errores posibles
- ✅ Usar emojis para indicar características (🔒 = requiere auth)

### 7. **Delegación**
- ✅ **NO** poner lógica de negocio en las rutas
- ✅ Delegar todo a los servicios
- ✅ Las rutas solo deben orquestar y retornar

## 🚫 Anti-patrones (Evitar)

```python
# ❌ MAL: Lógica de negocio en la ruta
@router.post("/users")
async def crear_usuario(payload: UserRequest):
    # ❌ NO hacer queries directos aquí
    user = db.query(User).filter(User.email == payload.email).first()
    if user:
        raise HTTPException(400, "Usuario ya existe")
    # ❌ NO tener lógica de validación compleja aquí
    if len(payload.password) < 8:
        raise HTTPException(400, "Contraseña muy corta")
    # Esto debe estar en el servicio!
    

# ✅ BIEN: Delegar al servicio
@router.post("/users")
async def crear_usuario(payload: UserRequest):
    return await service.crear_usuario(payload)
```

## 📚 Recursos Adicionales
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [REST API Best Practices](https://restfulapi.net/)
- [HTTP Status Codes](https://developer.mozilla.org/en-US/docs/Web/HTTP/Status)
