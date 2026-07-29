# Services (Lógica de Negocio)

## 📋 Descripción
Esta carpeta contiene los **servicios** que implementan la **lógica de negocio** de la aplicación. Orquestan llamadas a múltiples repositories, aplican reglas de negocio, transforman datos y coordinan flujos complejos. Son el corazón de la aplicación.

## 🔗 Conexiones
- **Usado por**: API Routes (endpoints)
- **Usa**: 
  - Repositories (acceso a datos)
  - Core (JWT, Redis, logging)
  - Models (para transformaciones)
  - Schemas (para validación interna)
- **NO accede**: Directamente a bases de datos (usa repositories)

## 🎯 Responsabilidades
1. **Lógica de negocio** (reglas, validaciones, flujos)
2. **Orquestación** de múltiples repositories
3. **Transformación de datos** entre capas
4. **Validaciones complejas** de negocio
5. **Manejo de transacciones** complejas
6. **Integración** entre diferentes sistemas
7. **Caché** y optimización (usando decoradores)

## 📂 Estructura
```
services/
├── __init__.py
├── readme.md
├── user_service.py          # Lógica de usuarios (login, CRUD)
├── automation_service.py    # Automatización de Fenix/Siebel
├── enlistment_service.py    # Gestión de enlistments
└── log_service.py           # Servicios de logging
```

## 🔄 Flujo en la Arquitectura
```
API Route → Service.method()
                ↓
           Validar reglas de negocio
                ↓
           Repository 1 (query)
                ↓
           Repository 2 (query)
                ↓
           Aplicar lógica de negocio
                ↓
           Transformar datos
                ↓
           Retornar resultado
                ↓
API Route ← Serializar con Schema
```

## 📝 Ejemplos de Implementación

### 1. Service Básico (CRUD con Validaciones)
```python
# app/services/user_service.py
import logging
from typing import List, Optional
from fastapi import HTTPException, status
from app.repositories.user_repository import UserRepository
from app.repositories.log_repository import LogRepository
from app.schemas.user_schema import UserCreate, UserUpdate
from app.core.auth_ldap import authenticate_user
from app.core.jwt_manager import create_jwt_token
from app.core.redis_cache import redis_client

logger = logging.getLogger("user_service")


class UserService:
    """
    Servicio para lógica de negocio de usuarios.
    """
    
    def __init__(self):
        """Inicializa repositories necesarios."""
        self.user_repo = UserRepository()
        self.log_repo = LogRepository()
    
    async def login(
        self,
        username: str,
        password: str,
        ip: str,
        device: str
    ) -> dict:
        """
        Procesa el login de un usuario.
        
        Flujo:
        1. Autenticar contra LDAP
        2. Buscar/crear usuario en BD
        3. Invalidar sesiones previas (single session)
        4. Crear nuevos tokens
        5. Guardar refresh token en Redis
        6. Loggear el evento
        
        Args:
            username: Nombre de usuario
            password: Contraseña
            ip: IP del cliente
            device: Dispositivo del cliente
        
        Returns:
            Dict con usuario, tokens y tipo
        
        Raises:
            HTTPException: Si credenciales son inválidas
        """
        try:
            # 1️⃣ Autenticar contra LDAP
            ldap_user = authenticate_user(username, password)
            if not ldap_user:
                logger.warning(f"Login fallido: {username} desde {ip}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Credenciales inválidas"
                )
            
            # 2️⃣ Buscar o crear usuario en BD
            user = self.user_repo.get_by_login(username)
            if not user:
                # Crear usuario automáticamente desde LDAP
                user_data = {
                    "login": username,
                    "full_name": ldap_user.get("display_name", username),
                    "email": ldap_user.get("email"),
                    "user_identify": ldap_user.get("username"),
                    "is_active": True
                }
                user = self.user_repo.create(user_data)
                logger.info(f"Nuevo usuario creado desde LDAP: {user.id}")
            
            # Validar que el usuario esté activo
            if not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Usuario inactivo"
                )
            
            # 3️⃣ Invalidar sesiones previas (single session)
            await self._invalidate_previous_sessions(user.id)
            
            # 4️⃣ Crear nuevos tokens
            access_token, access_jti, access_exp = create_jwt_token(
                subject=str(user.id),
                token_type="access"
            )
            
            refresh_token, refresh_jti, refresh_exp = create_jwt_token(
                subject=str(user.id),
                token_type="refresh"
            )
            
            # 5️⃣ Guardar refresh token en Redis
            await redis_client.setex(
                f"refresh_token:{user.id}",
                ttl=604800,  # 7 días
                value=refresh_jti
            )
            
            # 6️⃣ Loggear evento
            await self.log_repo.insert_log(
                level="INFO",
                message=f"Login exitoso: {username}",
                user_id=user.id,
                extra_data={"ip": ip, "device": device}
            )
            
            logger.info(f"Login exitoso: {username} (ID: {user.id}) desde {ip}")
            
            # 7️⃣ Retornar respuesta
            return {
                "user": user.to_dict(),
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "Bearer",
                "expires_in": access_exp
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error en login: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al procesar login"
            )
    
    async def _invalidate_previous_sessions(self, user_id: int):
        """
        Invalida sesiones previas del usuario (single session).
        
        Args:
            user_id: ID del usuario
        """
        try:
            # Obtener refresh token anterior
            old_refresh_jti = await redis_client.get(f"refresh_token:{user_id}")
            
            if old_refresh_jti:
                # Agregar a blacklist (si aún no expiró)
                await redis_client.setex(
                    f"blacklist:{old_refresh_jti}",
                    ttl=3600,  # 1 hora de blacklist
                    value="revoked"
                )
                
                # Eliminar refresh token anterior
                await redis_client.delete(f"refresh_token:{user_id}")
                
                logger.info(f"Sesión previa invalidada para usuario {user_id}")
        
        except Exception as e:
            logger.warning(f"Error al invalidar sesión previa: {e}")
            # No es crítico, continuar
    
    async def logout(self, token: str) -> dict:
        """
        Cierra sesión invalidando tokens.
        
        Args:
            token: Access token JWT
        
        Returns:
            Mensaje de confirmación
        """
        from app.core.jwt_manager import verify_jwt_token
        
        try:
            # Validar y extraer datos del token
            payload = verify_jwt_token(token, expected_type="access")
            if not payload:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token inválido"
                )
            
            user_id = payload.get("sub")
            access_jti = payload.get("jti")
            
            # Obtener refresh token
            refresh_jti = await redis_client.get(f"refresh_token:{user_id}")
            
            # Agregar ambos tokens a blacklist
            remaining_time = payload.get("exp") - int(datetime.utcnow().timestamp())
            
            await redis_client.setex(
                f"blacklist:{access_jti}",
                ttl=max(remaining_time, 60),
                value="revoked"
            )
            
            if refresh_jti:
                await redis_client.setex(
                    f"blacklist:{refresh_jti}",
                    ttl=604800,
                    value="revoked"
                )
                await redis_client.delete(f"refresh_token:{user_id}")
            
            logger.info(f"Logout exitoso: usuario {user_id}")
            
            return {
                "type": "success",
                "message": "Sesión cerrada exitosamente"
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error en logout: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al cerrar sesión"
            )
    
    def get_all_users(self, skip: int = 0, limit: int = 100) -> dict:
        """
        Obtiene todos los usuarios con paginación.
        
        Args:
            skip: Registros a saltar
            limit: Máximo de registros
        
        Returns:
            Dict con usuarios y metadata de paginación
        """
        users = self.user_repo.get_all(skip, limit)
        total = len(users)  # En producción, hacer query count
        
        return {
            "users": [user.to_dict() for user in users],
            "total": total,
            "page": (skip // limit) + 1,
            "page_size": limit
        }
    
    def create_user(self, user_data: UserCreate, created_by: int) -> dict:
        """
        Crea un nuevo usuario.
        
        Validaciones de negocio:
        - Login único
        - Email único
        - DNI único
        
        Args:
            user_data: Datos del usuario (UserCreate schema)
            created_by: ID del usuario que crea
        
        Returns:
            Usuario creado
        
        Raises:
            HTTPException: Si validaciones fallan
        """
        # 1️⃣ Validar login único
        existing_login = self.user_repo.get_by_login(user_data.login)
        if existing_login:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Login '{user_data.login}' ya está en uso"
            )
        
        # 2️⃣ Validar email único
        existing_email = self.user_repo.get_by_email(user_data.email)
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Email '{user_data.email}' ya está registrado"
            )
        
        # 3️⃣ Crear usuario
        user_dict = user_data.model_dump()  # Pydantic v2
        # user_dict = user_data.dict()  # Pydantic v1
        
        # Hash password (ejemplo)
        from app.utils.hash_utils import hash_password
        user_dict["password"] = hash_password(user_dict["password"])
        
        user = self.user_repo.create(user_dict)
        
        # 4️⃣ Loggear creación
        self.log_repo.insert_log(
            level="INFO",
            message=f"Usuario creado: {user.login}",
            user_id=created_by,
            extra_data={"new_user_id": user.id}
        )
        
        logger.info(f"Usuario creado: {user.id} por {created_by}")
        
        return user.to_dict()
```

### 2. Service con Orquestación Compleja
```python
# app/services/automation_service.py
import logging
from typing import Dict, Any, List
from datetime import datetime
import pandas as pd
from app.repositories.automation_repository import AutomationRepository
from app.repositories.enlistment_repository import EnlistmentRepository
from app.services.enlistment_service import EnlistmentService

logger = logging.getLogger("automation_service")


class AutomationService:
    """
    Servicio para automatización de carga de datos desde Fenix y Siebel.
    Orquesta múltiples repositories y servicios.
    """
    
    def __init__(self):
        self.automation_repo = AutomationRepository()
        self.enlistment_service = EnlistmentService()
    
    async def process_fenix_data(self, pedidos: List[str]) -> Dict[str, Any]:
        """
        Procesa datos de Fenix y los carga en enlistment.
        
        Flujo complejo:
        1. Obtener datos de Fenix (Oracle)
        2. Transformar y limpiar datos
        3. Mapear productos
        4. Validar datos
        5. Insertar/actualizar en enlistment
        6. Generar reporte de resultados
        
        Args:
            pedidos: Lista de números de pedido
        
        Returns:
            Reporte de procesamiento
        """
        try:
            logger.info(f"Iniciando procesamiento Fenix: {len(pedidos)} pedidos")
            
            # 1️⃣ Obtener datos de Fenix
            fenix_data = self.automation_repo.get_data_fenix(pedidos)
            if not fenix_data:
                return {
                    "type": "warning",
                    "message": "No se encontraron datos en Fenix",
                    "processed": 0
                }
            
            # 2️⃣ Convertir a DataFrame para transformación
            df = pd.DataFrame(fenix_data)
            
            # 3️⃣ Transformar y limpiar datos
            df = self._transform_fenix_data(df)
            
            # 4️⃣ Validar datos
            valid_records, invalid_records = self._validate_records(df)
            
            # 5️⃣ Procesar registros válidos
            processed = 0
            errors = []
            
            for record in valid_records:
                try:
                    # Insertar o actualizar en enlistment
                    await self.enlistment_service.upsert_enlistment(record)
                    processed += 1
                except Exception as e:
                    logger.error(f"Error procesando pedido {record.get('pedido_crm')}: {e}")
                    errors.append({
                        "pedido": record.get("pedido_crm"),
                        "error": str(e)
                    })
            
            # 6️⃣ Generar reporte
            report = {
                "type": "success",
                "message": f"Procesamiento completado",
                "total_records": len(fenix_data),
                "valid_records": len(valid_records),
                "invalid_records": len(invalid_records),
                "processed": processed,
                "errors": errors,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            logger.info(f"Procesamiento Fenix completado: {processed}/{len(fenix_data)}")
            
            return report
            
        except Exception as e:
            logger.error(f"Error en procesamiento Fenix: {e}")
            raise
    
    def _transform_fenix_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Transforma y limpia datos de Fenix.
        
        Args:
            df: DataFrame con datos raw
        
        Returns:
            DataFrame transformado
        """
        # Ejemplo de transformaciones
        df = df.copy()
        
        # Limpiar espacios
        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].str.strip()
        
        # Mapear productos
        df['producto_mapped'] = df['producto'].map(self.PRODUCTO_MAPPER)
        
        # Agregar timestamps
        df['processed_at'] = datetime.utcnow()
        
        return df
    
    def _validate_records(self, df: pd.DataFrame) -> tuple:
        """
        Valida registros según reglas de negocio.
        
        Args:
            df: DataFrame a validar
        
        Returns:
            Tupla con (registros_validos, registros_invalidos)
        """
        valid = df[df['pedido_crm'].notna() & (df['pedido_crm'] != '')]
        invalid = df[~df.index.isin(valid.index)]
        
        valid_records = valid.to_dict('records')
        invalid_records = invalid.to_dict('records')
        
        return valid_records, invalid_records
```

### 3. Service con Caché
```python
# app/services/menu_service.py
import logging
from typing import List, Dict
from app.repositories.menu_repository import MenuRepository
from app.decorators.cache_decorator import cache

logger = logging.getLogger("menu_service")


class MenuService:
    """
    Servicio para gestión de menús.
    Usa caché para mejorar performance.
    """
    
    def __init__(self):
        self.menu_repo = MenuRepository()
    
    @cache(ttl=3600)  # Cachear por 1 hora
    async def get_menu_structure(self) -> List[Dict]:
        """
        Obtiene estructura completa de menús.
        Resultado es cacheado por 1 hora.
        
        Returns:
            Lista de menús con submenús
        """
        logger.info("Obteniendo estructura de menús (sin cache)")
        
        menus = self.menu_repo.get_all_with_submenus()
        
        # Transformar a estructura jerárquica
        menu_structure = []
        for menu in menus:
            menu_dict = menu.to_dict()
            menu_dict['submenus'] = [
                submenu.to_dict() for submenu in menu.submenus
            ]
            menu_structure.append(menu_dict)
        
        return menu_structure
    
    @cache(ttl=300)  # Cachear por 5 minutos
    async def get_user_menu(self, user_id: int) -> List[Dict]:
        """
        Obtiene menús permitidos para un usuario.
        Cacheado por 5 minutos.
        
        Args:
            user_id: ID del usuario
        
        Returns:
            Menús con permisos del usuario
        """
        logger.info(f"Obteniendo menús para usuario {user_id}")
        
        user_menus = self.menu_repo.get_menus_by_user(user_id)
        
        return [menu.to_dict() for menu in user_menus]
```

## ✅ Buenas Prácticas

### 1. **Responsabilidades**
- ✅ Lógica de negocio en services, NO en routes ni repositories
- ✅ Un service por dominio/entidad
- ✅ Métodos públicos para casos de uso, privados para helpers

### 2. **Orquestación**
- ✅ Llamar a múltiples repositories según sea necesario
- ✅ Coordinar transacciones complejas
- ✅ Manejar rollbacks  cuando sea necesario

### 3. **Validaciones**
- ✅ Validaciones de negocio en services
- ✅ Lanzar HTTPException con mensajes claros
- ✅ Usar status codes apropiados

### 4. **Logging**
- ✅ Loggear inicio y fin de operaciones importantes
- ✅ Loggear errores con contexto completo
- ✅ Niveles apropiados (INFO, WARNING, ERROR)

### 5. **Performance**
- ✅ Usar decorador @cache para operaciones costosas
- ✅ Evitar N+1 queries (coordinar con repositories)
- ✅ Procesar en lotes cuando sea posible

### 6. **Testing**
- ✅ Services son fácilmente testables (inyección de dependencies)
- ✅ Mockear repositories en tests
- ✅ Testear reglas de negocio extensivamente

## 🚫 Anti-patrones (Evitar)

```python
# ❌ MAL: Acceso directo a BD en service
class UserService:
    def get_user(self, user_id):
        db = SessionLocal()  # ❌ No acceder directamente
        return db.query(User).filter(User.id == user_id).first()

# ✅ BIEN: Usar repository
class UserService:
    def __init__(self):
        self.user_repo = UserRepository()
    
    def get_user(self, user_id):
        return self.user_repo.get_by_id(user_id)


# ❌ MAL: No validar reglas de negocio
def create_user(self, user_data):
    return self.user_repo.create(user_data)  # ❌ Sin validaciones

# ✅ BIEN: Validar antes de crear
def create_user(self, user_data):
    # Validar unicidad
    if self.user_repo.get_by_email(user_data.email):
        raise HTTPException(400, "Email ya existe")
    
    return self.user_repo.create(user_data)


# ❌ MAL: Lógica de presentación en service
def get_user_profile(self, user_id):
    user = self.user_repo.get_by_id(user_id)
    # ❌ Formatear para UI aquí
    return {
        "nombre_completo": f"{user.first_name} {user.last_name}",
        "edad_texto": f"{user.age} años"
    }

# ✅ BIEN: Retornar datos, dejar presentación a la UI
def get_user_profile(self, user_id):
    user = self.user_repo.get_by_id(user_id)
    return user.to_dict()
```

## 📚 Recursos Adicionales
- [Domain-Driven Design](https://martinfowler.com/bliki/DomainDrivenDesign.html)
- [Service Layer Pattern](https://martinfowler.com/eaaCatalog/serviceLayer.html)
- [Business Logic in Services](https://stackoverflow.com/questions/11064316/where-to-put-business-logic-in-web-applications)