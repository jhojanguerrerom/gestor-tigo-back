# Repositories (Capa de Acceso a Datos)

## 📋 Descripción
Esta carpeta contiene los **repositories**, que son la capa de acceso a datos. Se encargan de todas las interacciones directas con bases de datos (ORM, SQL raw), APIs externas y otros sistemas. Implementan el patrón Repository para abstraer el acceso a datos.

## 🔗 Conexiones
- **Usado por**: Services (lógica de negocio)
- **Usa**: 
  - DB (sessions y engines)
  - Models (ORM)
  - APIs externas (requests HTTP)
- **NO accede**: Directamente desde Routes

## 🎯 Responsabilidades
1. **Queries a bases de datos** (SELECT, INSERT, UPDATE, DELETE)
2. **Uso de ORM** (SQLAlchemy) para operaciones con modelos
3. **SQL raw** cuando ORM no es suficiente o es ineficiente
4. **Llamadas a APIs externas** (requests, manejo de respuestas)
5. **Transformación de datos** entre formatos de BD y aplicación
6. **Manejo de transacciones** y sesiones de BD
7. **Optimización** de queries y performance

## 📂 Estructura
```
repositories/
├── __init__.py
├── readme.md
├── user_repository.py           # CRUD de usuarios
├── menu_repository.py           # Queries de menús
├── enlistment_repository.py     # Gestión de enlistments
├── automation_repository.py     # Queries a Oracle (Fenix, Siebel, MSS)
└── log_repository.py            # Logs en MongoDB
```

## 🔄 Flujo en la Arquitectura
```
Service → Repository.method()
              ↓
         Obtener session (SessionLocal)
              ↓
         Ejecutar query (ORM o raw SQL)
              ↓
         Transformar resultados
              ↓
         Cerrar session
              ↓
         Retornar datos
              ↓
Service ← Procesa datos
```

## 📝 Ejemplos de Implementación

### 1. Repository Básico (CRUD con ORM)
```python
# app/repositories/user_repository.py
import logging
from typing import List, Optional
from sqlalchemy.orm import Session
from app.db.postgres import SessionLocalPG
from app.models.user_model import User

logger = logging.getLogger("user_repository")


class UserRepository:
    """
    Repository para operaciones CRUD de usuarios.
    """
    
    def __init__(self):
        """Inicializa la conexión a la base de datos."""
        self.db: Session = SessionLocalPG()
    
    def __del__(self):
        """Cierra la sesión al destruir el repository."""
        if hasattr(self, 'db'):
            self.db.close()
    
    def get_all(self, skip: int = 0, limit: int = 100) -> List[User]:
        """
        Obtiene todos los usuarios con paginación.
        
        Args:
            skip: Número de registros a saltar
            limit: Número máximo de registros a retornar
        
        Returns:
            Lista de usuarios
        """
        return self.db.query(User).offset(skip).limit(limit).all()
    
    def get_by_id(self, user_id: int) -> Optional[User]:
        """
        Obtiene un usuario por ID.
        
        Args:
            user_id: ID del usuario
        
        Returns:
            Usuario o None si no existe
        """
        return self.db.query(User).filter(User.id == user_id).first()
    
    def get_by_login(self, login: str) -> Optional[User]:
        """
        Busca un usuario por login.
        
        Args:
            login: Login del usuario
        
        Returns:
            Usuario o None si no existe
        """
        return self.db.query(User).filter(User.login == login).first()
    
    def create(self, user_data: dict) -> User:
        """
        Crea un nuevo usuario.
        
        Args:
            user_data: Diccionario con datos del usuario
        
        Returns:
            Usuario creado
        """
        try:
            user = User(**user_data)
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
            logger.info(f"Usuario creado: {user.id}")
            return user
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error al crear usuario: {e}")
            raise
    
    def update(self, user_id: int, user_data: dict) -> Optional[User]:
        """
        Actualiza un usuario existente.
        
        Args:
            user_id: ID del usuario
            user_data: Diccionario con datos a actualizar
        
        Returns:
            Usuario actualizado o None si no existe
        """
        try:
            user = self.get_by_id(user_id)
            if not user:
                return None
            
            for key, value in user_data.items():
                setattr(user, key, value)
            
            self.db.commit()
            self.db.refresh(user)
            logger.info(f"Usuario actualizado: {user.id}")
            return user
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error al actualizar usuario: {e}")
            raise
    
    def delete(self, user_id: int) -> bool:
        """
        Elimina un usuario (soft delete - marca como inactivo).
        
        Args:
            user_id: ID del usuario
        
        Returns:
            True si se eliminó, False si no existe
        """
        try:
            user = self.get_by_id(user_id)
            if not user:
                return False
            
            user.is_active = False
            self.db.commit()
            logger.info(f"Usuario eliminado (soft): {user.id}")
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error al eliminar usuario: {e}")
            raise
    
    def search(self, query: str) -> List[User]:
        """
        Busca usuarios por nombre o email.
        
        Args:
            query: Texto a buscar
        
        Returns:
            Lista de usuarios que coinciden
        """
        search_pattern = f"%{query}%"
        return self.db.query(User).filter(
            (User.full_name.ilike(search_pattern)) |
            (User.email.ilike(search_pattern))
        ).all()
```

### 2. Repository con SQL Raw
```python
# app/repositories/automation_repository.py
import logging
from typing import List, Dict, Any
from sqlalchemy import text
from app.db.oracle_fenix_session import SessionLocalFenix
from app.db.oracle_siebel_session import SessionLocalSiebel

logger = logging.getLogger("automation_repository")


class AutomationRepository:
    """
    Repository para queries a Oracle (Fenix, Siebel, MSS).
    Usa SQL raw para queries complejas.
    """
    
    def get_data_fenix(self, pedidos_list: List[str]) -> List[Dict[str, Any]]:
        """
        Obtiene datos de Fenix Standby usando SQL raw.
        
        Args:
            pedidos_list: Lista de números de pedido
        
        Returns:
            Lista de diccionarios con datos de Fenix
        """
        if not pedidos_list:
            return []
        
        db = SessionLocalFenix()
        try:
            query = text("""
                SELECT 
                    P.PEDIDO_ID,
                    P.PEDIDO_CRM,
                    P.ESTADO,
                    C.CONCEPTO_ID,
                    C.DESCRIPCION
                FROM FNX_PEDIDOS P
                INNER JOIN FNX_SOLICITUDES S ON P.PEDIDO_ID = S.PEDIDO_ID
                INNER JOIN FNX_CONCEPTOS C ON S.CONCEPTO_ID = C.CONCEPTO_ID
                WHERE P.PEDIDO_CRM IN :pedidos
                AND S.ESTADO_BLOQUEO = 'N'
            """)
            
            result = db.execute(query, {"pedidos": tuple(pedidos_list)})
            
            # Convertir a lista de diccionarios
            columns = result.keys()
            data = [dict(zip(columns, row)) for row in result.fetchall()]
            
            logger.info(f"Datos obtenidos de Fenix: {len(data)} registros")
            return data
            
        except Exception as e:
            logger.error(f"Error al obtener datos de Fenix: {e}")
            raise
        finally:
            db.close()
    
    def get_data_siebel(self, pedidos_list: List[str]) -> List[Dict[str, Any]]:
        """
        Obtiene datos de Siebel Standby.
        
        Args:
            pedidos_list: Lista de números de pedido
        
        Returns:
            Lista de diccionarios con datos de Siebel
        """
        if not pedidos_list:
            return []
        
        db = SessionLocalSiebel()
        try:
            query = text("""
                SELECT 
                    ORDER_NUM,
                    CUSTOMER_ID,
                    STATUS_CD,
                    CREATED_DT
                FROM SIEBEL.S_ORDER
                WHERE ORDER_NUM IN :pedidos
            """)
            
            result = db.execute(query, {"pedidos": tuple(pedidos_list)})
            columns = result.keys()
            data = [dict(zip(columns, row)) for row in result.fetchall()]
            
            logger.info(f"Datos obtenidos de Siebel: {len(data)} registros")
            return data
            
        except Exception as e:
            logger.error(f"Error al obtener datos de Siebel: {e}")
            raise
        finally:
            db.close()
```

### 3. Repository con MongoDB
```python
# app/repositories/log_repository.py
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from app.db.mongodb_client import mongo_db
from app.models.log_mongo import LogMongo

logger = logging.getLogger("log_repository")


class LogRepository:
    """
    Repository para gestión de logs en MongoDB.
    """
    
    def __init__(self):
        """Inicializa la colección de logs."""
        self.collection = mongo_db["logs"]
    
    def insert_log(
        self,
        level: str,
        message: str,
        user_id: int = None,
        extra_data: Dict[str, Any] = None
    ) -> str:
        """
        Inserta un log en MongoDB.
        
        Args:
            level: Nivel del log
            message: Mensaje
            user_id: ID del usuario (opcional)
            extra_data: Datos adicionales (opcional)
        
        Returns:
            ID del documento insertado
        """
        try:
            log_doc = LogMongo.create_log(level, message, user_id, extra_data)
            result = self.collection.insert_one(log_doc)
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Error al insertar log: {e}")
            raise
    
    def find_logs(
        self,
        level: Optional[str] = None,
        user_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Busca logs con filtros opcionales.
        
        Args:
            level: Filtrar por nivel
            user_id: Filtrar por usuario
            start_date: Fecha inicial
            end_date: Fecha final
            limit: Máximo de registros
        
        Returns:
            Lista de logs
        """
        try:
            filters = {}
            
            if level:
                filters["level"] = level
            
            if user_id:
                filters["user_id"] = user_id
            
            if start_date or end_date:
                date_filter = {}
                if start_date:
                    date_filter["$gte"] = start_date
                if end_date:
                    date_filter["$lte"] = end_date
                filters["created_at"] = date_filter
            
            logs = list(
                self.collection
                .find(filters)
                .sort("created_at", -1)
                .limit(limit)
            )
            
            # Convertir ObjectId a string para serialización
            for log in logs:
                log["_id"] = str(log["_id"])
            
            return logs
            
        except Exception as e:
            logger.error(f"Error al buscar logs: {e}")
            raise
    
    def delete_old_logs(self, days: int = 30) -> int:
        """
        Elimina logs antiguos.
        
        Args:
            days: Días de antigüedad
        
        Returns:
            Número de logs eliminados
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            result = self.collection.delete_many({
                "created_at": {"$lt": cutoff_date}
            })
            logger.info(f"Logs eliminados: {result.deleted_count}")
            return result.deleted_count
        except Exception as e:
            logger.error(f"Error al eliminar logs antiguos: {e}")
            raise
```

### 4. Repository para API Externa
```python
# app/repositories/external_api_repository.py
import logging
import requests
from typing import Dict, Any, Optional
from app.core.config import settings
from app.utils.constants import Constants

logger = logging.getLogger("external_api_repository")


class ExternalAPIRepository:
    """
    Repository para llamadas a APIs externas.
    """
    
    def __init__(self):
        """Inicializa configuración de API."""
        self.base_url = settings.EXTERNAL_API_URL
        self.timeout = 30
    
    def get_customer_data(self, customer_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene datos de cliente desde API externa.
        
        Args:
            customer_id: ID del cliente
        
        Returns:
            Datos del cliente o None si falla
        """
        try:
            url = f"{self.base_url}/customers/{customer_id}"
            
            response = requests.get(
                url,
                headers={
                    "Authorization": f"Bearer {Constants.API_TOKEN}",
                    "Content-Type": "application/json"
                },
                timeout=self.timeout
            )
            
            response.raise_for_status()
            data = response.json()
            
            logger.info(f"Datos de cliente obtenidos: {customer_id}")
            return data
            
        except requests.exceptions.Timeout:
            logger.error(f"Timeout al consultar API: {customer_id}")
            return None
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP Error al consultar API: {e}")
            return None
        except Exception as e:
            logger.error(f"Error al consultar API: {e}")
            return None
    
    def create_order(self, order_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Crea una orden en la API externa.
        
        Args:
            order_data: Datos de la orden
        
        Returns:
            Respuesta de la API o None si falla
        """
        try:
            url = f"{self.base_url}/orders"
            
            response = requests.post(
                url,
                json=order_data,
                headers={
                    "Authorization": f"Bearer {Constants.API_TOKEN}",
                    "Content-Type": "application/json"
                },
                timeout=self.timeout
            )
            
            response.raise_for_status()
            data = response.json()
            
            logger.info(f"Orden creada: {data.get('order_id')}")
            return data
            
        except Exception as e:
            logger.error(f"Error al crear orden: {e}")
            return None
```

## ✅ Buenas Prácticas

### 1. **Gestión de Sesiones**
- ✅ Crear sesión en `__init__`
- ✅ Cerrar sesión en `__del__` o `finally`
- ✅ Hacer `commit()` después de cambios
- ✅ Hacer `rollback()` en caso de error

### 2. **Queries**
- ✅ Usar ORM para queries simples
- ✅ Usar SQL raw para queries complejos o performance crítica
- ✅ Usar parámetros (`:param`) para evitar SQL injection
- ✅ Indexar columnas frecuentemente consultadas

### 3. **Transformación de Datos**
- ✅ Convertir resultados de SQL raw a diccionarios
- ✅ Manejar valores None apropiadamente
- ✅ Serializar fechas y tipos especiales

### 4. **Manejo de Errores**
- ✅ Loggear errores con contexto
- ✅ Hacer rollback en transacciones fallidas
- ✅ Re-lanzar excepciones para que service las maneje
- ✅ Retornar None o lista vacía en caso de no encontrar datos

### 5. **Performance**
- ✅ Usar paginación (offset, limit)
- ✅ Seleccionar solo columnas necesarias
- ✅ Usar joins en vez de N+1 queries
- ✅ Cachear resultados cuando sea apropiado (en service, no aquí)

### 6. **APIs Externas**
- ✅ Configurar timeouts
- ✅ Manejar errores HTTP apropiadamente
- ✅ Loggear requests y responses (sin datos sensibles)
- ✅ Implementar retry logic si es necesario

## 🚫 Anti-patrones (Evitar)

```python
# ❌ MAL: No cerrar sesiones
class UserRepository:
    def get_all(self):
        db = SessionLocal()
        return db.query(User).all()  # ❌ Sesión nunca se cierra

# ✅ BIEN: Cerrar sesión apropiadamente
class UserRepository:
    def __init__(self):
        self.db = SessionLocal()
    
    def __del__(self):
        if hasattr(self, 'db'):
            self.db.close()
    
    def get_all(self):
        return self.db.query(User).all()


# ❌ MAL: No hacer rollback en errores
def create(self, data):
    user = User(**data)
    self.db.add(user)
    self.db.commit()  # ❌ Si falla, transacción queda abierta

# ✅ BIEN: Rollback en errores
def create(self, data):
    try:
        user = User(**data)
        self.db.add(user)
        self.db.commit()
        return user
    except Exception as e:
        self.db.rollback()
        raise


# ❌ MAL: SQL injection vulnerable
def search(self, query):
    sql = f"SELECT * FROM users WHERE name = '{query}'"  # ❌ Vulnerable
    result = db.execute(text(sql))

# ✅ BIEN: Usar parámetros
def search(self, query):
    sql = "SELECT * FROM users WHERE name = :query"
    result = db.execute(text(sql), {"query": query})


# ❌ MAL: N+1 queries
def get_users_with_orders(self):
    users = self.db.query(User).all()
    for user in users:
        user.orders = self.db.query(Order).filter(Order.user_id == user.id).all()  # ❌ Query por cada usuario

# ✅ BIEN: Usar join o eager loading
def get_users_with_orders(self):
    from sqlalchemy.orm import joinedload
    return self.db.query(User).options(joinedload(User.orders)).all()


# ❌ MAL: Lógica de negocio en repository
def create_user_with_welcome_email(self, user_data):
    user = User(**user_data)
    self.db.add(user)
    self.db.commit()
    # ❌ Enviar email aquí es lógica de negocio
    send_email(user.email, "Welcome!")
    return user

# ✅ BIEN: Solo acceso a datos
def create_user(self, user_data):
    user = User(**user_data)
    self.db.add(user)
    self.db.commit()
    return user
# (El service se encarga del email)
```

## 📚 Recursos Adicionales
- [Repository Pattern](https://martinfowler.com/eaaCatalog/repository.html)
- [SQLAlchemy Query API](https://docs.sqlalchemy.org/en/20/orm/queryguide/)
- [Requests Documentation](https://requests.readthedocs.io/)
- [MongoDB Python Driver](https://pymongo.readthedocs.io/)