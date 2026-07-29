import logging
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from app.core.jwt_manager import get_token_header
from app.core.utils import get_client_device, get_client_ip
from app.decorators.auth_decorator import get_current_user, jwt_required
from app.schemas.auth_schema import LoginRequest
from app.schemas.user_schema import UserRespWithTokenAndMenu
from app.services.user_service import UserService
from app.repositories.user_repository import UserRepository
from app.dependencies import get_db_pg

router = APIRouter(prefix="", tags=["auth"])
logger = logging.getLogger("auth")

# ============================
# LOGIN
# ============================
@router.post("/login", response_model=UserRespWithTokenAndMenu)
async def login(request: Request, payload: LoginRequest, db: Session = Depends(get_db_pg)):
    """
    Inicia sesión y retorna Access + Refresh Tokens.
    🔐 SINGLE SESSION: Invalida automáticamente cualquier sesión activa previa.
    """
    service = UserService(db)
    try:
        logger.info("Start Login")
        
        ip = get_client_ip(request)
        device = get_client_device(request)

        auth = await service.login(
            username=payload.username,
            password=payload.password,
            ip=ip,
            device=device
        )

        # auth debe retornar:
        # {
        #   "user": user_data,
        #   "access_token": "...",
        #   "refresh_token": "...",
        #   "token_type": "Bearer"
        # }
        return auth
    except HTTPException as e:
        logger.error(f"Login error: {e}")
        raise e
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error en autenticación")
    finally:
        logger.info("End Login")


# ============================
# LOGOUT
# ============================
@router.post("/logout", dependencies=[Depends(jwt_required)])
async def logout(request: Request, db: Session = Depends(get_db_pg)):
    """
    Cierra la sesión actual eliminando el refresh token y bloqueando el access token.
    """
    service = UserService(db)
    try:
        logger.info("Start Logout")
        token = get_token_header(request)
        res = await service.logout(token=token)
        return res
    except HTTPException as e:
        logger.error(f"Logout error: {e}")
        raise e
    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al cerrar sesión")
    finally:
        logger.info("End Logout")


# ============================
# REFRESH TOKEN
# ============================
@router.post("/refresh-token")
async def refresh_token(request: Request, db: Session = Depends(get_db_pg)):
    """
    Refresca el Access Token usando un Refresh Token válido.
    - Genera nuevos tokens.
    - Invalida el Refresh Token anterior.
    """
    service = UserService(db)
    try:
        logger.info("Start Refresh Token")
        ip = get_client_ip(request)
        device = get_client_device(request)
        refresh_token = get_token_header(request)  # Se envía como Bearer token
        res = await service.refresh_token(
            old_refresh_token=refresh_token,
            ip=ip,
            device=device
        )
        # Retorna nuevo par de tokens
        return res
    except HTTPException as e:
        logger.error(f"Refresh token error: {e}")
        raise e
    except Exception as e:
        logger.error(f"Refresh token error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al refrescar token")
    finally:
        logger.info("End Refresh Token")

# ============================
# SESSIONS (nuevo)
# ============================
@router.get("/sessions", dependencies=[Depends(jwt_required)])
async def get_sessions(request: Request, db: Session = Depends(get_db_pg)):
    """
    Retorna las sesiones activas del usuario autenticado (por dispositivo e IP).
    """
    service = UserService(db)
    try:
        logger.info("Start Get Sessions")
        current_user = await get_current_user(request)
        sessions = await service.get_active_sessions(current_user["id"])
        return {
            "user_id": current_user["id"],
            "count": len(sessions),
            "active_sessions": sessions
        }
    except HTTPException as e:
        logger.error(f"Get sessions error: {e}")
        raise e
    except Exception as e:
        logger.error(f"Get sessions error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al obtener sesiones activas")
    finally:
        logger.info("End Get Sessions")

# ============================
# SESSIONS REVOCAR POR JTI
# ============================
@router.delete("/sessions/{jti}", dependencies=[Depends(jwt_required)])
async def terminate_session(jti: str, request: Request, db: Session = Depends(get_db_pg)):
    """
    Revoca (cierra) una sesión específica del usuario.
    Esto elimina el refresh token de Redis y evita que se renueve el access token.
    """
    service = UserService(db)
    try:
        logger.info("Start Terminate Session")

        user = request.state.user
        
        res = await service.revoke_session(user_id=user.get('id'), jti=jti)

        if not res:
            raise HTTPException(status_code=404, detail="Sesión no encontrada o ya cerrada")

        return {"detail": "Sesión cerrada exitosamente", "jti": jti}

    except HTTPException as e:
        logger.error(f"Terminate session error: {e}")
        raise e
    except Exception as e:
        logger.error(f"Terminate session error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        logger.info("End Terminate Session")

# ============================
# CHECK ACTIVE SESSION (opcional - para UX)
# ============================
@router.post("/check-session")
async def check_active_session(payload: LoginRequest, db: Session = Depends(get_db_pg)):
    """
    🔐 SINGLE SESSION: Verifica si el usuario tiene una sesión activa.
    Útil para mostrar advertencia en el frontend antes del login.
    """
    service = UserService(db)
    user_repo = UserRepository(db)
    try:
        logger.info("Start Check Active Session")
        
        # Buscar usuario por username
        user = user_repo.get_by_username(payload.username)
        
        if not user:
            # No revelamos si el usuario existe o no por seguridad
            return {
                "has_active_session": False,
                "message": "No hay sesiones activas"
            }
        
        # Verificar sesiones activas
        sessions = await service.get_active_sessions(str(user.id))
        
        if sessions:
            # Obtener info de la sesión más reciente
            latest_session = max(sessions, key=lambda s: s.get('created_at', ''))
            return {
                "has_active_session": True,
                "message": "Ya existe una sesión activa. Al iniciar sesión, se cerrará automáticamente.",
                "current_session": {
                    "device": latest_session.get("device"),
                    "ip": latest_session.get("ip"),
                    "created_at": latest_session.get("created_at")
                }
            }
        
        return {
            "has_active_session": False,
            "message": "No hay sesiones activas"
        }
        
    except Exception as e:
        logger.error(f"Check session error: {e}")
        # No revelamos errores por seguridad
        return {
            "has_active_session": False,
            "message": "No hay sesiones activas"
        }
    finally:
        logger.info("End Check Active Session")