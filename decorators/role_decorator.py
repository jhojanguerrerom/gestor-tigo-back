import logging
from fastapi import Request, HTTPException, Depends
from typing import List
from functools import wraps
from app.decorators.auth_decorator import jwt_required
from app.repositories.user_repository import UserRepository
from app.db.postgres import SessionLocalPG

logger = logging.getLogger("role_decorator")

# Definición de perfiles del sistema TODO: Implemntar desde base de datos
PERFILES = {
    1: "SuperUser",
    2: "M2M",
    3: "Supervisor",
    4: "Regular",
    5: "Viewer"
}


def require_profile(allowed_profiles: List[int]):
    """
    Decorador para validar que el usuario tenga uno de los perfiles permitidos.
    
    **IMPORTANTE**: El perfil SuperUser (ID: 1) tiene acceso total a TODA la plataforma,
    sin importar qué perfiles estén especificados en allowed_profiles.
    
    Args:
        allowed_profiles: Lista de profile_ids permitidos (ej: [1, 3] para SuperUser y Supervisor)
    
    Comportamiento:
        - SuperUser (profile_id = 1): Acceso automático a CUALQUIER endpoint
        - Otros perfiles: Deben estar en la lista allowed_profiles
    
    Ejemplo de uso:
        @router.post("/ofertas/descongelar", dependencies=[Depends(jwt_required), Depends(require_profile([1, 3]))])
        async def descongelar_oferta(...):
            # SuperUser (1) y Supervisor (3) pueden acceder
            # SuperUser siempre tiene acceso, incluso si solo se especifica [3]
            ...
    """
    async def profile_checker(request: Request):
        """Verifica que el usuario tenga el perfil requerido"""
        try:
            # Obtener el user_id del request (almacenado por jwt_required)
            user_data = getattr(request.state, "user", None)
            if not user_data:
                raise HTTPException(
                    status_code=401, 
                    detail="Usuario no autenticado"
                )
            
            user_id = user_data.get("id")
            if not user_id:
                raise HTTPException(
                    status_code=401, 
                    detail="No se pudo obtener el ID del usuario"
                )
            
            # Obtener el perfil del usuario desde la base de datos
            # Crear sesión temporal para la consulta
            db = SessionLocalPG()
            try:
                user_repo = UserRepository(db)
                user = user_repo.get_by_id(user_id)
            finally:
                db.close()
            
            if not user:
                logger.error(f"Usuario {user_id} no encontrado en la base de datos")
                raise HTTPException(
                    status_code=404, 
                    detail="Usuario no encontrado"
                )
            
            profile_id = user.profile_id
            
            # ⭐ SuperUser (perfil 1) tiene acceso total a TODA la plataforma
            if profile_id == 1:
                # Agregar el profile_id al request para uso posterior si es necesario
                request.state.profile_id = profile_id
                
                logger.info(
                    f"Acceso autorizado (SuperUser): Usuario {user.login} con acceso total a la plataforma"
                )
                
                return True
            
            # Validar que el perfil esté en la lista de perfiles permitidos
            if profile_id not in allowed_profiles:
                profile_name = PERFILES.get(profile_id, "Desconocido")
                allowed_names = [PERFILES.get(p, str(p)) for p in allowed_profiles]
                
                logger.warning(
                    f"Acceso denegado: Usuario {user.login} (perfil: {profile_name}) "
                    f"intentó acceder a un recurso que requiere perfil: {allowed_names}"
                )
                
                raise HTTPException(
                    status_code=403,
                    detail=f"Acceso denegado. Se requiere perfil: {', '.join(allowed_names)}"
                )
            
            # Agregar el profile_id al request para uso posterior si es necesario
            request.state.profile_id = profile_id
            
            logger.info(
                f"Acceso autorizado: Usuario {user.login} con perfil {PERFILES.get(profile_id)}"
            )
            
            return True
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error en validación de perfil: {e}")
            raise HTTPException(
                status_code=500, 
                detail="Error al validar permisos del usuario"
            )
    
    return profile_checker


def get_user_profile(request: Request) -> int:
    """
    Función helper para obtener el profile_id del usuario autenticado.
    
    Args:
        request: FastAPI Request object
        
    Returns:
        profile_id del usuario
        
    Raises:
        HTTPException si no se puede obtener el perfil
    """
    try:
        user_data = getattr(request.state, "user", None)
        if not user_data:
            raise HTTPException(status_code=401, detail="Usuario no autenticado")
        
        user_id = user_data.get("id")
        
        # Crear sesión temporal para la consulta
        db = SessionLocalPG()
        try:
            user_repo = UserRepository(db)
            user = user_repo.get_by_id(user_id)
        finally:
            db.close()
        
        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
        return user.profile_id
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al obtener perfil del usuario: {e}")
        raise HTTPException(status_code=500, detail="Error al obtener perfil del usuario")


def is_supervisor_or_admin(profile_id: int) -> bool:
    """
    Verifica si un perfil es Supervisor o SuperUser.
    
    Args:
        profile_id: ID del perfil a verificar
        
    Returns:
        True si es Supervisor (3) o SuperUser (1)
    """
    return profile_id in [1, 3]


def is_regular_user(profile_id: int) -> bool:
    """
    Verifica si un perfil es Usuario Regular.
    
    Args:
        profile_id: ID del perfil a verificar
        
    Returns:
        True si es Regular (4)
    """
    return profile_id == 4


def get_profile_name(profile_id: int) -> str:
    """
    Obtiene el nombre legible de un perfil.
    
    Args:
        profile_id: ID del perfil
        
    Returns:
        Nombre del perfil
    """
    return PERFILES.get(profile_id, f"Desconocido ({profile_id})")
