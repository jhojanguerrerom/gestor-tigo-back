import logging
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer
from jose import JWTError
from app.core.jwt_manager import verify_jwt_token
from app.core.redis_cache import redis_client
from app.repositories.user_repository import UserRepository
from app.db.postgres import SessionLocalPG

security = HTTPBearer()
logger = logging.getLogger("jwt_required")

async def jwt_required(request: Request, credentials=Depends(security)):
    """
    Middleware de autenticación JWT:
    - Valida la firma y expiración del token.
    - Rechaza tokens revocados (blacklist).
    - Almacena user_id y jti en request.state.
    """
    token = credentials.credentials
    
    try:
        payload = verify_jwt_token(token, expected_type="access")

        if not payload:
            raise HTTPException(status_code=401, detail="Token inválido o expirado")

        jti = payload.get("jti")
        user_id = payload.get("sub")

        if not user_id or not jti:
            raise HTTPException(status_code=401, detail="Token sin datos de sesión")

        # 1️⃣ Revisar si el token está revocado (blacklist)
        is_blacklisted = await redis_client.exists(f"blacklist:{jti}")
        if is_blacklisted:
            logger.warning(f"Token en blacklist detectado para usuario {user_id}")
            raise HTTPException(status_code=401, detail="Token revocado o sesión finalizada")
        
        # Crear sesión temporal para consulta del usuario
        db = SessionLocalPG()
        try:
            user_repo = UserRepository(db)
            user_data = user_repo.get_by_id(user_id)
        finally:
            db.close()
        
        request.state.payload = {
            "user_login": user_data.login,
            "user_name": user_data.full_name,
            "user_dni": user_data.user_identify,
            "user_id": user_id
        }

        # 2️⃣ Guardar datos en el request para usar en endpoints
        request.state.user = {
            "id": user_id,
            "jti": jti,
            "token": token
        }

        return payload
    except JWTError as e:
        logger.error(f"Error JWT: {e}")
        raise HTTPException(status_code=401, detail="Token inválido o expirado")

    except Exception as e:
        logger.error(f"Error en jwt_required: {e}")
        raise HTTPException(status_code=401, detail="Autenticación fallida")


async def get_current_user(request: Request):
    """
    Retorna el usuario autenticado almacenado en el request.
    """
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no autenticado")
    return user