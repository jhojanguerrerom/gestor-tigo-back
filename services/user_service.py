import logging
import json
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.utils.constants import Constants
from fastapi import HTTPException, status
from typing import Dict

from app.core.auth_ldap import authenticate_user
from app.repositories.user_repository import UserRepository
from app.repositories.menu_repository import MenuRepository
from app.models.user_model import UserModel
from app.core.config import settings
from app.core.jwt_manager import create_jwt_token, verify_jwt_token
from app.core.redis_cache import redis_client  # se asume cliente async (aioredis or alike)

logger = logging.getLogger("auth")

INVALID_CREDENTIALS = "invalid credentials"

class UserService:
    """
    Servicio de usuario que implementa autenticación JWT con estrategia híbrida de rotación.
    
    🔐 ESTRATEGIA DE TOKENS (ROTACIÓN HÍBRIDA CON LÍMITE TEMPORAL):
    
    **Access Token** (15 min):
      - Token de corta duración para acceder a recursos protegidos
      - Se valida en cada request mediante middleware
      - Cuando expira: usar refresh token para obtener uno nuevo
    
    **Refresh Token** (7 días por rotación, máximo 30 días absolutos):
      - Token de larga duración para obtener nuevos access tokens
      - Se ROTA en cada uso (genera nuevo refresh + access)
      - Límite temporal ABSOLUTO: MAX_SESSION_DAYS desde login original
      - Cuando expira o alcanza límite: re-login obligatorio
    
    **Características de Seguridad:**
      ✅ Rotación de tokens: cada refresh genera nuevos tokens (previene reutilización)
      ✅ Límite temporal absoluto: fuerza re-login después de MAX_SESSION_DAYS
      ✅ Single session mode: invalida sesiones previas en nuevo login (opcional)
      ✅ Blacklist de access tokens: revocación inmediata en logout
      ✅ Auditoría completa: logs detallados de todas las operaciones
    
    **Métodos principales:**
      - login: genera access + refresh tokens (guarda original_login_at)
      - logout: invalida tokens y marca en blacklist
      - refresh_token: rota tokens verificando límite temporal absoluto
    """

    def __init__(self, db: Session):
        """Inicializa el service con la sesión de base de datos.
        
        Args:
            db: Sesión de SQLAlchemy inyectada por dependency
        """
        self.db = db
        self.repo = UserRepository(db)
        self.repo_menu = MenuRepository(db)

    async def login(self, username: str, password: str, device: str = "unknown", ip: str = "unknown") -> Dict:
        logger.info(f"Function login: {username}")
        try:
            logger.info(f"Validacion campos vacios: {username}")
            if not username or not password:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=INVALID_CREDENTIALS)
            
            # Buscar si el usuario es M2M en la lista
            logger.info(f"Validacion usuario M2M: {username}")
            m2m_user = next((user for user in Constants.USERS_M2M if user.get('user') == username), None)
            
            if m2m_user:
                # Es usuario M2M - validar contraseña
                logger.info(f"Validacion autenticacion M2M: {username}")
                if password != m2m_user.get('password'):
                    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=INVALID_CREDENTIALS)
            else:
                # No es usuario M2M - autenticar con LDAP
                auth_ldap = authenticate_user(username=username, password=password)
                logger.info(f"USER_LDAP: {auth_ldap}")
                if not auth_ldap:
                    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=INVALID_CREDENTIALS)

            # Local DB user
            logger.info(f"Validacion usuario Base de datos: {username}")
            user = self.repo.get_by_username(username)
            logger.info(f"Respuesta usuario Base de datos: {user}")
            if not user or not user.user_state:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=INVALID_CREDENTIALS)

            # 🔐 SINGLE SESSION: Invalidar todas las sesiones previas del usuario
            logger.info(f"Validacion single mode: {user}")
            if settings.SINGLE_SESSION_MODE:
                await self._revoke_all_user_sessions(str(user.id))
                logger.info(f"Sesiones previas invalidadas para usuario {user.id}")

            # Crear access + refresh
            logger.info("Generación de token JWT")
            access_token, access_jti, access_exp = create_jwt_token(str(user.id), token_type="access")
            refresh_token, refresh_jti, refresh_exp = create_jwt_token(str(user.id), token_type="refresh")

            # 🔐 HYBRID ROTATION: Guardar timestamp original del login
            original_login_at = datetime.now(timezone.utc).isoformat()

            # Persistir refresh token en Redis (clave: refresh:{refresh_jti})
            session_value = {
                "user_id": str(user.id),
                "refresh_jti": refresh_jti,
                "access_jti": access_jti,  # 🔐 Guardar access_jti para blacklist
                "device": device,
                "ip": ip,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "original_login_at": original_login_at,  # 🔐 HYBRID: timestamp del login original
                "expires_at": refresh_exp,
                "access_expires_at": access_exp  # 🔐 Guardar expiración del access token
            }
            # TTL en segundos desde ahora hasta refresh_exp
            ttl = max(0, refresh_exp - int(datetime.now(timezone.utc).timestamp()))
            await redis_client.setex(f"refresh:{refresh_jti}", ttl, json.dumps(session_value))

            # Registrar en set por usuario para manejo (refreshs:{user_id})
            await redis_client.sadd(f"refreshs:{user.id}", refresh_jti)
            # Establecer TTL para el set (opcional): igual que el refresh token
            await redis_client.expire(f"refreshs:{user.id}", ttl)

            # Construir menú
            logger.info("Construccion del menu")
            menus_db = self.repo_menu.get_menu_by_profile(profile=user.profile_id)
            menus = []
            for menu in menus_db:
                submenus = self.repo_menu.get_submenu_by_menu_id(menu_id=menu.id, profile=user.profile_id)
                menu_dict = {
                    "label": menu.menu_name,
                    "subItems": [{"label": s.submenu_name, "path": s.url} for s in submenus]
                }
                menus.append(menu_dict)

            # Respuesta: incluir tokens
            logger.info("Incluir token en la respeusta del user")
            user.menu = menus
            user.auth = {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "Bearer",
                "access_expires_at": access_exp,
                "refresh_expires_at": refresh_exp
            }

            return user

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Login error: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al autenticar")

    async def logout(self, token: str) -> Dict:
        """
        Invalida sesión:
         - Si se recibe un access token: lo marca en blacklist y elimina todos los refresh tokens del usuario.
         - Si se recibe un refresh token: elimina ese refresh token.
        """
        try:
            payload = verify_jwt_token(token)
            if not payload:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")

            token_type = payload.get("type")
            user_id = payload.get("sub")
            jti = payload.get("jti")
            now_ts = int(datetime.now(timezone.utc).timestamp())

            # Blacklist key for access tokens
            if token_type == "access":
                # Guardar blacklist:{access_jti} con TTL hasta exp
                exp = payload.get("exp", now_ts)
                ttl = max(0, int(exp) - now_ts)
                await redis_client.setex(f"blacklist:{jti}", ttl, "revoked")
                # Además, eliminar todos los refresh tokens del usuario
                refresh_set_key = f"refreshs:{user_id}"
                refreshs = await redis_client.smembers(refresh_set_key) or []
                for rjti in refreshs:
                    await redis_client.delete(f"refresh:{rjti}")
                await redis_client.delete(refresh_set_key)
                return {"detail": "Sesión cerrada: access token invalidado y refresh tokens eliminados"}

            elif token_type == "refresh":
                refresh_jti = jti
                # Eliminar refresh token and remove from set
                await redis_client.delete(f"refresh:{refresh_jti}")
                # remove from user set if possible: need user id
                # payload contains sub
                refresh_set_key = f"refreshs:{user_id}"
                await redis_client.srem(refresh_set_key, refresh_jti)
                return {"detail": "Refresh token eliminado"}

            else:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tipo de token no reconocido")

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Logout error: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al cerrar sesión")

    async def refresh_token(self, old_refresh_token: str, device: str = "unknown", ip: str = "unknown") -> Dict:
        """
        🔐 ROTACIÓN HÍBRIDA CON LÍMITE TEMPORAL:
         - Verifica el refresh token y su registro en Redis.
         - Valida que no se haya excedido el límite absoluto de sesión (MAX_SESSION_DAYS).
         - Si es válido, ROTA ambos tokens (access + refresh) por seguridad.
         - Mantiene el timestamp original del login para enforcement del límite temporal.
         
        Flujo:
         1. Verifica validez del refresh token (firma JWT + existencia en Redis)
         2. Verifica límite temporal absoluto desde el login original
         3. Revoca el refresh token anterior (previene reutilización)
         4. Genera NUEVOS access + refresh tokens
         5. Preserva el original_login_at para mantener límite temporal
        """
        try:
            payload = verify_jwt_token(old_refresh_token, expected_type="refresh")
            if not payload:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token inválido o expirado")

            refresh_jti = payload.get("jti")
            user_id = payload.get("sub")

            # Verificar existencia en Redis
            stored = await redis_client.get(f"refresh:{refresh_jti}")
            if not stored:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token no válido o ya revocado")

            # Parse session data
            session_data = json.loads(stored)
            original_login_at_str = session_data.get("original_login_at")
            
            # 🔐 VALIDACIÓN DE LÍMITE TEMPORAL ABSOLUTO
            if original_login_at_str:
                original_login_dt = datetime.fromisoformat(original_login_at_str)
                now = datetime.now(timezone.utc)
                max_session_delta = timedelta(days=settings.MAX_SESSION_DAYS)
                
                if now - original_login_dt > max_session_delta:
                    # Sesión expirada por límite temporal - revocar y forzar re-login
                    await redis_client.delete(f"refresh:{refresh_jti}")
                    await redis_client.srem(f"refreshs:{user_id}", refresh_jti)
                    
                    logger.warning(
                        f"AUDIT: Session expired by time limit | "
                        f"user_id={user_id} | "
                        f"original_login={original_login_at_str} | "
                        f"max_days={settings.MAX_SESSION_DAYS} | "
                        f"age_days={(now - original_login_dt).days}"
                    )
                    
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail=f"Sesión expirada: han pasado {settings.MAX_SESSION_DAYS} días desde el login. Por favor, inicie sesión nuevamente."
                    )

            # Revoke old refresh
            await redis_client.delete(f"refresh:{refresh_jti}")
            await redis_client.srem(f"refreshs:{user_id}", refresh_jti)

            # 🔐 ROTACIÓN: Crear nuevos tokens (ambos por seguridad)
            access_token, access_jti, access_exp = create_jwt_token(str(user_id), token_type="access")
            refresh_token, refresh_jti_new, refresh_exp = create_jwt_token(str(user_id), token_type="refresh")

            # 🔐 PRESERVAR original_login_at para mantener límite temporal
            session_value = {
                "user_id": str(user_id),
                "refresh_jti": refresh_jti_new,
                "access_jti": access_jti,
                "device": device,
                "ip": ip,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "original_login_at": original_login_at_str,  # 🔐 CLAVE: Mantener login original
                "expires_at": refresh_exp,
                "access_expires_at": access_exp
            }
            ttl = max(0, refresh_exp - int(datetime.now(timezone.utc).timestamp()))
            await redis_client.setex(f"refresh:{refresh_jti_new}", ttl, json.dumps(session_value))
            await redis_client.sadd(f"refreshs:{user_id}", refresh_jti_new)
            await redis_client.expire(f"refreshs:{user_id}", ttl)

            logger.info(f"Token rotado para usuario {user_id} (original login: {original_login_at_str})")
            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "Bearer",
                "access_expires_at": access_exp,
                "refresh_expires_at": refresh_exp
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error al refrescar token: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al refrescar token")
        
    async def get_active_sessions(self, user_id: str):
        """
        Retorna las sesiones activas del usuario desde Redis (refresh tokens válidos).
        """
        session_keys = await redis_client.smembers(f"refreshs:{user_id}")
        sessions = []

        for jti_bytes in session_keys:
            jti = jti_bytes if isinstance(jti_bytes, str) else jti_bytes.decode()
            data = await redis_client.get(f"refresh:{jti}")
            if data:
                session = json.loads(data)
                sessions.append({
                    "device": session.get("device"),
                    "ip": session.get("ip"),
                    "created_at": session.get("created_at"),
                    "jti": jti
                })

        return sessions
    
    async def revoke_session(self, user_id: str, jti: str):
        """
        Elimina una sesión específica (refresh token) de Redis.
        """
        try:
            # Verificar si la sesión existe
            session_data = await redis_client.get(f"refresh:{jti}")
            if not session_data:
                return False

            # Eliminar el token individual
            await redis_client.delete(f"refresh:{jti}")

            # Eliminar la referencia del set de sesiones del usuario
            await redis_client.srem(f"refreshs:{user_id}", jti)

            return True

        except Exception as e:
            logger.error(f"Error revocando sesión {jti} para user {user_id}: {e}")
            return False

    async def _revoke_all_user_sessions(self, user_id: str):
        """
        🔐 SINGLE SESSION: Invalida todas las sesiones activas de un usuario.
        - Elimina todos los refresh tokens del usuario de Redis.
        - Agrega access tokens a blacklist para invalidación inmediata.
        - Genera logs de auditoría detallados.
        """
        try:
            refresh_set_key = f"refreshs:{user_id}"
            refreshs = await redis_client.smembers(refresh_set_key) or []
            now_ts = int(datetime.now(timezone.utc).timestamp())
            
            sessions_revoked = 0
            
            # Eliminar cada refresh token y agregar access token a blacklist
            for rjti_bytes in refreshs:
                rjti = rjti_bytes if isinstance(rjti_bytes, str) else rjti_bytes.decode()
                
                # Obtener session data para extraer access_jti
                session_data = await redis_client.get(f"refresh:{rjti}")
                if session_data:
                    session = json.loads(session_data)
                    access_jti = session.get("access_jti")
                    device = session.get("device", "unknown")
                    ip = session.get("ip", "unknown")
                    created_at = session.get("created_at", "unknown")
                    
                    # 🔐 MEJORA 1: Agregar access token a blacklist
                    if access_jti:
                        access_exp = session.get("access_expires_at", now_ts + 900)  # 15 min default
                        ttl = max(0, int(access_exp) - now_ts)
                        if ttl > 0:  # Solo blacklistear si aún no expiró
                            await redis_client.setex(f"blacklist:{access_jti}", ttl, "revoked")
                            logger.debug(f"Access token {access_jti} agregado a blacklist (TTL: {ttl}s)")
                    
                    # 🔐 MEJORA 4: Log de auditoría detallado
                    logger.warning(
                        f"AUDIT: Session revoked | "
                        f"user_id={user_id} | "
                        f"device={device} | "
                        f"ip={ip} | "
                        f"created_at={created_at} | "
                        f"refresh_jti={rjti} | "
                        f"access_jti={access_jti} | "
                        f"reason=new_login"
                    )
                    
                    sessions_revoked += 1
                
                # Eliminar refresh token
                await redis_client.delete(f"refresh:{rjti}")
                logger.debug(f"Refresh token {rjti} eliminado para usuario {user_id}")
            
            # Eliminar el set de referencias
            await redis_client.delete(refresh_set_key)
            
            # 🔐 MEJORA 4: Log consolidado de auditoría
            if sessions_revoked > 0:
                logger.warning(
                    f"AUDIT: All sessions revoked | "
                    f"user_id={user_id} | "
                    f"total_sessions={sessions_revoked} | "
                    f"timestamp={datetime.now(timezone.utc).isoformat()}"
                )
            
            logger.info(f"Todas las sesiones ({sessions_revoked}) revocadas para usuario {user_id}")
            
        except Exception as e:
            logger.error(f"Error revocando todas las sesiones para usuario {user_id}: {e}")

    # ==========================================
    # MÉTODOS CRUD (Solo SuperUsuario)
    # ==========================================
    
    def get_users(self, skip: int = 0, limit: int = 100, search: str = None) -> Dict:
        """
        Lista usuarios con paginación y búsqueda.
        
        Args:
            skip: Número de registros a saltar (paginación)
            limit: Número máximo de registros a retornar
            search: Texto de búsqueda opcional
        
        Returns:
            Diccionario con total, página, tamaño de página y lista de usuarios
        """
        try:
            # Obtener total de usuarios (para paginación)
            total = self.repo.count_all(active_only=False, search=search)
            
            # Construir query
            query = self.repo.db.query(UserModel)
            
            # Aplicar filtro de búsqueda si existe
            if search:
                search_pattern = f"%{search}%"
                query = query.filter(
                    (UserModel.full_name.ilike(search_pattern)) |
                    (UserModel.email.ilike(search_pattern)) |
                    (UserModel.login.ilike(search_pattern))
                )
            
            # Aplicar paginación y obtener usuarios
            users = query.offset(skip).limit(limit).all()
            
            # Calcular número de página
            page = (skip // limit) + 1 if limit > 0 else 1
            
            return {
                "total": total,
                "page": page,
                "page_size": limit,
                "users": users
            }
        except Exception as e:
            logger.error(f"Error al obtener usuarios: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al obtener usuarios"
            )
    
    def get_user_by_id(self, user_id: str) -> UserModel:
        """
        Obtiene un usuario por ID.
        
        Args:
            user_id: UUID del usuario
        
        Returns:
            Usuario encontrado
        
        Raises:
            HTTPException: Si el usuario no existe
        """
        try:
            user = self.repo.get_by_id(user_id)
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Usuario con ID {user_id} no encontrado"
                )
            
            return user
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error al obtener usuario {user_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al obtener usuario"
            )
    
    def create_user(self, user_data: dict, created_by: str) -> UserModel:
        """
        Crea un nuevo usuario.
        
        Args:
            user_data: Diccionario con datos del usuario
            created_by: Login del usuario que crea el registro
        
        Returns:
            Usuario creado
        
        Raises:
            HTTPException: Si el login ya existe o hay error en la creación
        """
        try:
            # Validar que el login no exista
            existing_user = self.repo.get_by_username(user_data.get("login"))
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"El usuario con login '{user_data.get('login')}' ya existe"
                )
            
            # Agregar información de auditoría
            user_data["create_user_login"] = created_by
            user_data["create_at"] = datetime.now(timezone.utc)
            
            # Crear usuario
            user = self.repo.create(user_data)
            
            logger.info(f"Usuario creado: {user.login} (ID: {user.id}) por {created_by}")
            
            return user
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error al crear usuario: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al crear usuario"
            )
    
    def update_user(self, user_id: str, user_data: dict) -> UserModel:
        """
        Actualiza un usuario existente.
        
        Args:
            user_id: UUID del usuario
            user_data: Diccionario con datos a actualizar
        
        Returns:
            Usuario actualizado
        
        Raises:
            HTTPException: Si el usuario no existe o hay error en la actualización
        """
        try:
            # Verificar que el usuario exista
            user = self.repo.get_by_id(user_id)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Usuario con ID {user_id} no encontrado"
                )
            
            # Filtrar solo los campos que se enviaron (no None)
            update_data = {k: v for k, v in user_data.items() if v is not None}
            
            if not update_data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No se proporcionaron datos para actualizar"
                )
            
            # Actualizar usuario
            updated_user = self.repo.update(user_id, update_data)
            
            logger.info(f"Usuario actualizado: {updated_user.login} (ID: {user_id})")
            
            return updated_user
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error al actualizar usuario {user_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al actualizar usuario"
            )
    
    def delete_user(self, user_id: str, requesting_user_id: str) -> bool:
        """
        Elimina un usuario (soft delete - marca como inactivo).
        
        Args:
            user_id: UUID del usuario a eliminar
            requesting_user_id: UUID del usuario que solicita la eliminación
        
        Returns:
            True si se eliminó correctamente
        
        Raises:
            HTTPException: Si el usuario no existe, intenta auto-eliminarse, o hay error
        """
        try:
            # Validar que no sea auto-eliminación
            if str(user_id) == str(requesting_user_id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No puede eliminar su propia cuenta"
                )
            
            # Verificar que el usuario exista
            user = self.repo.get_by_id(user_id)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Usuario con ID {user_id} no encontrado"
                )
            
            # Eliminar (soft delete)
            success = self.repo.delete(user_id)
            
            if success:
                logger.info(f"Usuario eliminado (soft delete): {user.login} (ID: {user_id})")
                return True
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
            # No lanzamos excepción para no bloquear el login