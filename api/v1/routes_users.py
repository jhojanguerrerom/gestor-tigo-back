import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session

from app.decorators.auth_decorator import jwt_required
from app.decorators.role_decorator import require_profile
from app.services.user_service import UserService
from app.repositories.user_repository import UserRepository
from app.dependencies import get_db_pg
from app.schemas.user_schema import (
    UserCreateRequest,
    UserUpdateRequest,
    UserDetailResponse,
    UserListResponse
)

router = APIRouter(prefix="/v1/users", tags=["users"])
logger = logging.getLogger("users_routes")


# ==========================================
# UTILIDADES
# ==========================================

def get_requesting_user_data(request: Request, db: Session) -> dict:
    """Obtiene los datos del usuario que realiza la petición"""
    payload = getattr(request.state, "payload", None)
    if not payload:
        raise HTTPException(status_code=401, detail="Usuario no autenticado")
    
    user_id = payload.get("user_id")
    user_repository = UserRepository(db)
    user = user_repository.get_by_id(user_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    return {
        'user_id': str(user.id),
        'login': user.login,
        'profile_id': user.profile_id
    }


# ==========================================
# ENDPOINTS CRUD - SOLO SUPERUSUARIO
# ==========================================

@router.get(
    "/",
    response_model=UserListResponse,
    dependencies=[Depends(jwt_required), Depends(require_profile([1]))],
    summary="Listar usuarios (paginado)",
    description="Obtiene un listado paginado de usuarios con opción de búsqueda. **Solo SuperUsuario (perfil 1)**"
)
async def get_users(
    request: Request,
    db: Session = Depends(get_db_pg),
    page: int = Query(1, ge=1, description="Número de página"),
    page_size: int = Query(10, ge=1, le=100, description="Tamaño de página"),
    search: Optional[str] = Query(None, description="Buscar por nombre, email o login")
):
    """
    Lista todos los usuarios del sistema con paginación.
    
    **Permisos requeridos**: SuperUsuario (profile_id = 1)
    
    **Parámetros de búsqueda**:
    - `page`: Número de página (inicia en 1)
    - `page_size`: Cantidad de registros por página (máximo 100)
    - `search`: Texto para filtrar por nombre completo, email o login
    
    **Retorna**:
    - Lista de usuarios con información detallada
    - Total de usuarios
    - Información de paginación
    """
    service = UserService(db)
    try:
        # Calcular offset para paginación
        skip = (page - 1) * page_size
        
        # Obtener usuarios
        result = service.get_users(skip=skip, limit=page_size, search=search)
        
        logger.info(f"Usuarios listados por {get_requesting_user_data(request, db)['login']}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error al listar usuarios: {e}")
        raise


@router.get(
    "/{user_id}",
    response_model=UserDetailResponse,
    dependencies=[Depends(jwt_required), Depends(require_profile([1]))],
    summary="Obtener usuario por ID",
    description="Obtiene la información detallada de un usuario específico. **Solo SuperUsuario (perfil 1)**"
)
async def get_user(
    request: Request,
    user_id: UUID,
    db: Session = Depends(get_db_pg)
):
    """
    Obtiene información detallada de un usuario por su ID.
    
    **Permisos requeridos**: SuperUsuario (profile_id = 1)
    
    **Parámetros**:
    - `user_id`: UUID del usuario
    
    **Retorna**:
    - Información completa del usuario incluyendo:
      - Datos personales
      - Estado de la cuenta
      - Fecha de creación y último acceso
      - Usuario que lo creó
    """
    service = UserService(db)
    try:
        user = service.get_user_by_id(str(user_id))
        
        logger.info(f"Usuario {user_id} consultado por {get_requesting_user_data(request, db)['login']}")
        
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al obtener usuario {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener usuario"
        )


@router.post(
    "/",
    response_model=UserDetailResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(jwt_required), Depends(require_profile([1]))],
    summary="Crear nuevo usuario",
    description="Crea un nuevo usuario en el sistema. **Solo SuperUsuario (perfil 1)**"
)
async def create_user(
    request: Request,
    user_data: UserCreateRequest,
    db: Session = Depends(get_db_pg)
):
    """
    Crea un nuevo usuario en el sistema.
    
    **Permisos requeridos**: SuperUsuario (profile_id = 1)
    
    **Campos requeridos**:
    - `login`: Login único del usuario (3-50 caracteres)
    - `user_identify`: Número de identificación
    - `full_name`: Nombre completo (3-200 caracteres)
    - `profile_id`: ID del perfil (1-5)
    
    **Campos opcionales**:
    - `email`: Correo electrónico
    - `user_state`: Estado del usuario (activo/inactivo, default: true)
    
    **Perfiles disponibles**:
    - 1: SuperUser
    - 2: M2M
    - 3: Supervisor
    - 4: Regular
    - 5: Viewer
    
    **Validaciones**:
    - El login debe ser único en el sistema
    - El email debe tener formato válido
    """
    service = UserService(db)
    try:
        requesting_user = get_requesting_user_data(request, db)
        
        # Convertir Pydantic model a dict
        user_dict = user_data.model_dump()
        
        # Crear usuario
        new_user = service.create_user(user_dict, created_by=requesting_user['login'])
        
        logger.info(
            f"Usuario creado: {new_user.login} (ID: {new_user.id}) "
            f"por {requesting_user['login']}"
        )
        
        return new_user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al crear usuario: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al crear usuario"
        )


@router.put(
    "/{user_id}",
    response_model=UserDetailResponse,
    dependencies=[Depends(jwt_required), Depends(require_profile([1]))],
    summary="Actualizar usuario",
    description="Actualiza la información de un usuario existente. **Solo SuperUsuario (perfil 1)**"
)
async def update_user(
    request: Request,
    user_id: UUID,
    user_data: UserUpdateRequest,
    db: Session = Depends(get_db_pg)
):
    """
    Actualiza la información de un usuario existente.
    
    **Permisos requeridos**: SuperUsuario (profile_id = 1)
    
    **Parámetros**:
    - `user_id`: UUID del usuario a actualizar
    
    **Campos actualizables** (todos opcionales):
    - `user_identify`: Número de identificación
    - `full_name`: Nombre completo (3-200 caracteres)
    - `profile_id`: ID del perfil (1-5)
    - `email`: Correo electrónico
    - `user_state`: Estado del usuario (activo/inactivo)
    
    **Nota**: Solo se actualizan los campos enviados en la petición.
    Los campos omitidos o con valor `null` mantienen su valor actual.
    """
    service = UserService(db)
    try:
        requesting_user = get_requesting_user_data(request, db)
        
        # Convertir Pydantic model a dict
        user_dict = user_data.model_dump(exclude_none=True)
        
        # Actualizar usuario
        updated_user = service.update_user(str(user_id), user_dict)
        
        logger.info(
            f"Usuario actualizado: {updated_user.login} (ID: {user_id}) "
            f"por {requesting_user['login']}"
        )
        
        return updated_user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al actualizar usuario {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al actualizar usuario"
        )


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(jwt_required), Depends(require_profile([1]))],
    summary="Eliminar usuario",
    description="Desactiva un usuario del sistema (soft delete). **Solo SuperUsuario (perfil 1)**"
)
async def delete_user(
    request: Request,
    user_id: UUID,
    db: Session = Depends(get_db_pg)
):
    """
    Elimina (desactiva) un usuario del sistema.
    
    **Permisos requeridos**: SuperUsuario (profile_id = 1)
    
    **Parámetros**:
    - `user_id`: UUID del usuario a eliminar
    
    **Importante**:
    - Esta es una eliminación lógica (soft delete)
    - El usuario se marca como inactivo (`user_state = false`)
    - Los datos del usuario se conservan en la base de datos
    - No puede eliminarse a sí mismo
    
    **Validaciones**:
    - El usuario debe existir
    - No puede eliminar su propia cuenta
    """
    service = UserService(db)
    try:
        requesting_user = get_requesting_user_data(request, db)
        
        # Eliminar usuario (soft delete)
        success = service.delete_user(str(user_id), requesting_user['user_id'])
        
        if success:
            logger.info(
                f"Usuario {user_id} eliminado (soft delete) "
                f"por {requesting_user['login']}"
            )
            return {
                "detail": "Usuario eliminado correctamente",
                "user_id": str(user_id)
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al eliminar usuario"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al eliminar usuario {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al eliminar usuario"
        )
