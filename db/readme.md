# DB (Database Connections)

## 📋 Descripción
Esta carpeta gestiona todas las **conexiones a bases de datos** de la aplicación. Incluye configuración de engines, session makers y clientes para PostgreSQL, MongoDB y múltiples instancias de Oracle (Fenix, MSS, Siebel).

## 🔗 Conexiones
- **Usado por**: Repositories (acceso a datos)
- **Conecta con**: 
  - **PostgreSQL** (base de datos principal - gestor)
  - **MongoDB** (logs y datos no estructurados)
  - **Oracle Fenix Standby** (datos de Fenix)
  - **Oracle MSS Standby** (datos de MSS)
  - **Oracle Siebel Standby** (datos de Siebel)
  - **SQL Server 2019** (Gestión Operativa)
- **Usa**: Core/config.py (URLs de conexión)

## 🎯 Responsabilidades
1. **Crear engines** de SQLAlchemy para cada base de datos
2. **Configurar session makers** para manejo de sesiones
3. **Gestionar conexiones** (pool, timeout, ping)
4. **Proveer clientes** listos para usar en repositories
5. **Definir base model** para ORM (base_model.py)

## 📂 Estructura
```
db/
├── __init__.py
├── readme.md
├── base_model.py                            # Base para modelos SQLAlchemy
├── postgres.py                              # PostgreSQL (BD principal)
├── mongodb_client.py                        # MongoDB (logs)
├── oracle_fenix_session.py                  # Oracle Fenix Standby
├── oracle_mss_session.py                    # Oracle MSS Standby
├── oracle_siebel_session.py                 # Oracle Siebel Standby
├── mysql_session.py                         # MySQL (si se usa)
├── sqlserver_gestion_operativa_session.py   # SQL Server 2019 (Gestión Operativa)
└── oracle_readme.md                         # Documentación Oracle
```

## 🔄 Flujo en la Arquitectura
```
Startup (main.py) → wait_for_db() → engines (testear conexiones)
                                          ↓
Repository → SessionLocal() → Query/ORM → Database
                    ↓
            SessionLocal.close() (liberar conexión)
```

## 📝 Ejemplos de Implementación

### 1. PostgreSQL (postgres.py)
```python
# app/db/postgres.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Crear engine con pool pre-ping para reconexión automática
engine_pg = create_engine(
    settings.POSTGRES_URL,
    pool_pre_ping=True,        # Verificar conexión antes de usar
    pool_size=10,              # Número de conexiones en el pool
    max_overflow=20,           # Conexiones adicionales si se necesitan
    pool_recycle=3600,         # Reciclar conexiones cada hora
    echo=False                 # True para debug SQL
)

# Session maker
SessionLocalPG = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine_pg
)
```

### 2. MongoDB (mongodb_client.py)
```python
# app/db/mongodb_client.py
from pymongo import MongoClient
from app.core.config import settings

# Crear cliente con timeouts
client = MongoClient(
    settings.MONGO_URL,
    serverSelectionTimeoutMS=3000,  # Timeout selección de servidor
    socketTimeoutMS=5000,           # Timeout de operaciones
    connectTimeoutMS=3000           # Timeout de conexión inicial
)

# Obtener database
mongo_db = client.get_database("gestor")

# Colecciones comunes (opcional)
logs_collection = mongo_db["logs"]
audit_collection = mongo_db["audit"]
```

### 3. Oracle (oracle_*_session.py)
```python
# app/db/oracle_fenix_session.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

engine_fenix = create_engine(
    settings.ORACLE_FENIX_URL,  # oracle+cx_oracle://user:pass@host:port/?service_name=SERVICE
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    echo=False
)

SessionLocalFenix = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine_fenix
)
```

### 4. Base Model (base_model.py)
```python
# app/db/base_model.py
from sqlalchemy.ext.declarative import declarative_base

# Base para todos los modelos ORM
Base = declarative_base()

# Uso en models:
# from app.db.base_model import Base
# class User(Base):
#     __tablename__ = "users"
#     ...
```

## 📝 Uso en Repositories

### PostgreSQL
```python
# app/repositories/user_repository.py
from app.db.postgres import SessionLocalPG
from app.models.user_model import User

class UserRepository:
    def __init__(self):
        self.db = SessionLocalPG()
    
    def __del__(self):
        """Cerrar sesión al destruir el repository"""
        if hasattr(self, 'db'):
            self.db.close()
    
    def get_by_id(self, user_id: int):
        return self.db.query(User).filter(User.id == user_id).first()
    
    def create(self, user_data: dict):
        user = User(**user_data)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
```

### MongoDB
```python
# app/repositories/log_repository.py
from app.db.mongodb_client import mongo_db
from datetime import datetime

class LogRepository:
    def __init__(self):
        self.collection = mongo_db["logs"]
    
    def insert_log(self, log_data: dict):
        log_data["created_at"] = datetime.utcnow()
        result = self.collection.insert_one(log_data)
        return str(result.inserted_id)
    
    def find_logs(self, filters: dict, limit: int = 100):
        return list(self.collection.find(filters).limit(limit))
```

### Oracle
```python
# app/repositories/automation_repository.py
from app.db.oracle_fenix_session import SessionLocalFenix
from sqlalchemy import text

class AutomationRepository:
    def get_data_fenix(self, pedidos: list):
        db = SessionLocalFenix()
        try:
            query = text("""
                SELECT * FROM fenix_table
                WHERE pedido_id IN :pedidos
            """)
            result = db.execute(query, {"pedidos": tuple(pedidos)})
            return result.fetchall()
        finally:
            db.close()
```

## ✅ Buenas Prácticas

### 1. **Gestión de Conexiones**
- ✅ Usar `pool_pre_ping=True` para reconexión automática
- ✅ Configurar pool_size y max_overflow apropiados
- ✅ Reciclar conexiones periódicamente (`pool_recycle`)
- ✅ Cerrar sesiones en `__del__` o usar context managers
- ❌ No dejar sesiones abiertas indefinidamente

### 2. **Timeouts**
- ✅ Configurar timeouts de conexión y operación
- ✅ Usar valores conservadores (3-5 segundos)
- ✅ Manejar errores de timeout gracefully

### 3. **Seguridad**
- ✅ Usar variables de entorno para URLs de conexión
- ✅ No hardcodear credenciales
- ✅ Usar usuarios con privilegios mínimos necesarios
- ❌ No commitear credenciales al repositorio

### 4. **Logging**
- ✅ Loggear errores de conexión
- ✅ Usar `echo=True` solo en desarrollo para debug SQL
- ❌ No loggear credenciales en los logs

### 5. **Performance**
- ✅ Usar connection pooling
- ✅ Cerrar sesiones apropiadamente
- ✅ Evitar N+1 queries (usar joins, eager loading)
- ✅ Indexar columnas frecuentemente consultadas

### 6. **Transacciones**
- ✅ Usar `autocommit=False` para control manual
- ✅ Hacer `commit()` explícito después de cambios
- ✅ Hacer `rollback()` en caso de error
- ✅ Usar transacciones para operaciones múltiples

## 🚫 Anti-patrones (Evitar)

```python
# ❌ MAL: Hardcodear URL de conexión
engine = create_engine("postgresql://user:pass@localhost/db")

# ✅ BIEN: Usar configuración
from app.core.config import settings
engine = create_engine(settings.POSTGRES_URL)


# ❌ MAL: No cerrar sesiones
def get_users():
    db = SessionLocalPG()
    return db.query(User).all()  # ❌ Sesión nunca se cierra

# ✅ BIEN: Cerrar sesión
def get_users():
    db = SessionLocalPG()
    try:
        return db.query(User).all()
    finally:
        db.close()


# ❌ MAL: No configurar pool
engine = create_engine(url)  # Usa defaults que pueden no ser óptimos

# ✅ BIEN: Configurar pool apropiadamente
engine = create_engine(
    url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600
)


# ❌ MAL: No manejar errores de conexión
result = db.execute(query)  # ¿Y si falla la conexión?

# ✅ BIEN: Manejar errores
try:
    result = db.execute(query)
except OperationalError as e:
    logger.error(f"Error de conexión: {e}")
    raise HTTPException(503, "Servicio temporalmente no disponible")
```

## 🔧 Configuración de URLs

### PostgreSQL
```bash
POSTGRES_URL=postgresql://user:password@host:port/database
# Ejemplo: postgresql://gestor:pass123@localhost:5432/gestor_db
```

### MongoDB
```bash
MONGO_URL=mongodb://user:password@host:port/
# Ejemplo: mongodb://admin:pass123@localhost:27017/
```

### Oracle
```bash
# Método 1: Service Name
ORACLE_FENIX_URL=oracle+cx_oracle://user:pass@host:port/?service_name=SERVICE_NAME

# Método 2: SID
ORACLE_FENIX_URL=oracle+cx_oracle://user:pass@host:port/SID

# Ejemplo real (Fenix Standby):
ORACLE_FENIX_URL=oracle+cx_oracle://fenix_user:pass@10.10.10.10:1521/?service_name=FENIXSTD
```

## 📦 Dependencias Requeridas
```bash
# requirements.txt
sqlalchemy>=2.0.0
psycopg2-binary>=2.9.0      # PostgreSQL
pymongo>=4.0.0               # MongoDB
cx-Oracle>=8.3.0             # Oracle
pymysql>=1.0.0               # MySQL (opcional)
```

## 🧪 Testing de Conexiones
```python
# Ejecutar en main.py al startup
def wait_for_db(engine, retries=10, delay=2):
    for i in range(retries):
        try:
            conn = engine.connect()
            conn.close()
            logger.info(f"✅ Conexión exitosa a {engine.url}")
            return True
        except Exception as e:
            logger.error(f"❌ Intento {i+1} fallido: {e}")
            time.sleep(delay)
    return False

# En startup:
wait_for_db(postgres.engine_pg)
wait_for_db(oracle_fenix_session.engine_fenix)
```

## 📚 Recursos Adicionales
- [SQLAlchemy Core Documentation](https://docs.sqlalchemy.org/en/20/core/)
- [SQLAlchemy Engine Configuration](https://docs.sqlalchemy.org/en/20/core/engines.html)
- [PyMongo Documentation](https://pymongo.readthedocs.io/)
- [cx_Oracle Documentation](https://cx-oracle.readthedocs.io/)
