# Migrations (Migraciones de Base de Datos)

## 📋 Descripción
Esta carpeta contiene **scripts de migración** para crear, modificar o eliminar estructuras de base de datos. Las migraciones aseguran que el esquema de la base de datos esté sincronizado con los modelos de la aplicación.

## 🔗 Conexiones
- **Usa**: 
  - DB (engines y conexiones)
  - Models (definiciones de tablas)
  - Core/config.py (URLs de bases de datos)
- **Ejecutado**: Manualmente o en CI/CD
- **NO usado por**: Runtime de la aplicación

## 🎯 Responsabilidades
1. **Crear tablas** nuevas basándose en modelos
2. **Modificar esquemas** existentes (agregar columnas, índices)
3. **Crear índices** para optimización de queries
4. **Poblar datos** iniciales (seeds)
5. **Reversiones** si es necesario (rollback)
6. **Documentar cambios** en el esquema

## 📂 Estructura
```
migrations/
├── __init__.py
├── readme.md
├── create_enlistment_tables.py    # Crea tablas de enlistment
├── create_oferta_gestion_tables.py # Crea tablas de oferta_gestion
├── add_estado_oferta_field.py     # Agrega campo estado_oferta
├── fix_campos_modificados_keys.py # Fix: Estandariza claves JSON (anterior→old, nuevo→new)
└── ...
```

## 🔄 Flujo de Migración
```
Desarrollo → Crear/Modificar Models → Crear Script de Migración
                                            ↓
                                    Ejecutar migración en DEV
                                            ↓
                                    Probar cambios
                                            ↓
                                    Commit a repositorio
                                            ↓
                                    Ejecutar en QA/PROD
```

## 📝 Ejemplos de Implementación

### 1. Crear Tablas Nuevas
```python
# app/migrations/create_producto_tables.py
"""
Migración: Crear tablas de productos
Fecha: 2026-02-17
Autor: [Tu nombre]
Descripción: Crea las tablas producto, categoria y producto_categoria
"""

import sys
import logging
from sqlalchemy import create_engine, text
from app.core.config import settings
from app.db.base_model import Base
from app.models.producto_model import Producto, Categoria, ProductoCategoria

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_producto_tables():
    """
    Crea las tablas relacionadas con productos.
    """
    try:
        logger.info("🚀 Iniciando migración: create_producto_tables")
        
        # Crear engine
        engine = create_engine(settings.POSTGRES_URL, pool_pre_ping=True)
        
        # Crear tablas
        logger.info("📋 Creando tablas...")
        Base.metadata.create_all(bind=engine, tables=[
            Producto.__table__,
            Categoria.__table__,
            ProductoCategoria.__table__
        ])
        
        # Crear índices adicionales
        logger.info("🔍 Creando índices...")
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_producto_nombre 
                ON producto (nombre);
            """))
            
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_producto_categoria_producto_id 
                ON producto_categoria (producto_id);
            """))
            
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_producto_categoria_categoria_id 
                ON producto_categoria (categoria_id);
            """))
            
            conn.commit()
        
        logger.info("✅ Migración completada exitosamente")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en migración: {e}")
        return False


def rollback_producto_tables():
    """
    Revierte la migración (elimina las tablas).
    ⚠️ USAR CON PRECAUCIÓN - SE PIERDEN TODOS LOS DATOS
    """
    try:
        logger.warning("⚠️ Iniciando rollback: drop_producto_tables")
        engine = create_engine(settings.POSTGRES_URL, pool_pre_ping=True)
        
        with engine.connect() as conn:
            conn.execute(text("DROP TABLE IF EXISTS producto_categoria CASCADE;"))
            conn.execute(text("DROP TABLE IF EXISTS producto CASCADE;"))
            conn.execute(text("DROP TABLE IF EXISTS categoria CASCADE;"))
            conn.commit()
        
        logger.info("✅ Rollback completado")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en rollback: {e}")
        return False


if __name__ == "__main__":
    # Ejecutar: python -m app.migrations.create_producto_tables
    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        rollback_producto_tables()
    else:
        create_producto_tables()
```

### 2. Agregar Columnas a Tabla Existente
```python
# app/migrations/add_user_phone_column.py
"""
Migración: Agregar columna teléfono a tabla users
Fecha: 2026-02-17
Descripción: Agrega columna phone (nullable) a la tabla users
"""

import logging
from sqlalchemy import create_engine, text
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def add_phone_column():
    """Agrega columna phone a la tabla users."""
    try:
        logger.info("🚀 Iniciando migración: add_user_phone_column")
        engine = create_engine(settings.POSTGRES_URL, pool_pre_ping=True)
        
        with engine.connect() as conn:
            # Verificar si la columna ya existe
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'users' AND column_name = 'phone';
            """))
            
            if result.fetchone():
                logger.info("⚠️ La columna 'phone' ya existe, saltando...")
                return True
            
            # Agregar columna
            conn.execute(text("""
                ALTER TABLE users 
                ADD COLUMN phone VARCHAR(20) NULL;
            """))
            
            # Crear índice (opcional)
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_users_phone 
                ON users (phone);
            """))
            
            conn.commit()
        
        logger.info("✅ Migración completada: columna 'phone' agregada")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en migración: {e}")
        return False


def rollback_phone_column():
    """Elimina la columna phone."""
    try:
        logger.warning("⚠️ Iniciando rollback: remove phone column")
        engine = create_engine(settings.POSTGRES_URL, pool_pre_ping=True)
        
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE users DROP COLUMN IF EXISTS phone;"))
            conn.commit()
        
        logger.info("✅ Rollback completado")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en rollback: {e}")
        return False


if __name__ == "__main__":
    add_phone_column()
```

### 3. Poblar Datos Iniciales (Seed)
```python
# app/migrations/seed_initial_roles.py
"""
Migración: Poblar roles iniciales
Fecha: 2026-02-17
Descripción: Inserta roles básicos del sistema
"""

import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.models.role_model import Role

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def seed_initial_roles():
    """Inserta roles iniciales."""
    try:
        logger.info("🚀 Iniciando seed: initial_roles")
        engine = create_engine(settings.POSTGRES_URL, pool_pre_ping=True)
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()
        
        initial_roles = [
            {"name": "admin", "description": "Administrador del sistema"},
            {"name": "user", "description": "Usuario estándar"},
            {"name": "guest", "description": "Usuario invitado (solo lectura)"},
        ]
        
        for role_data in initial_roles:
            # Verificar si ya existe
            existing = db.query(Role).filter(Role.name == role_data["name"]).first()
            if existing:
                logger.info(f"⚠️ Rol '{role_data['name']}' ya existe, saltando...")
                continue
            
            # Crear rol
            role = Role(**role_data)
            db.add(role)
            logger.info(f"✅ Rol '{role_data['name']}' creado")
        
        db.commit()
        db.close()
        
        logger.info("✅ Seed completado: roles iniciales insertados")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en seed: {e}")
        return False


if __name__ == "__main__":
    seed_initial_roles()
```

### 4. Crear Índices de Performance
```python
# app/migrations/add_performance_indexes.py
"""
Migración: Agregar índices de performance
Fecha: 2026-02-17
Descripción: Crea índices para queries frecuentes
"""

import logging
from sqlalchemy import create_engine, text
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def add_performance_indexes():
    """Crea índices para mejorar performance."""
    try:
        logger.info("🚀 Iniciando migración: add_performance_indexes")
        engine = create_engine(settings.POSTGRES_URL, pool_pre_ping=True)
        
        indexes = [
            # Índice compuesto para búsquedas frecuentes
            """
            CREATE INDEX IF NOT EXISTS idx_orders_user_date 
            ON orders (user_id, created_at DESC);
            """,
            
            # Índice para campos JSONB (PostgreSQL)
            """
            CREATE INDEX IF NOT EXISTS idx_logs_data_gin 
            ON logs USING GIN (data);
            """,
            
            # Índice parcial (solo registros activos)
            """
            CREATE INDEX IF NOT EXISTS idx_users_active_email 
            ON users (email) 
            WHERE is_active = true;
            """,
            
            # Índice para búsqueda full-text
            """
            CREATE INDEX IF NOT EXISTS idx_products_name_trgm 
            ON products USING GIN (name gin_trgm_ops);
            """,
        ]
        
        with engine.connect() as conn:
            for idx_sql in indexes:
                logger.info(f"Creando índice...")
                conn.execute(text(idx_sql))
            conn.commit()
        
        logger.info("✅ Migración completada: índices creados")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en migración: {e}")
        return False


if __name__ == "__main__":
    add_performance_indexes()
```

## ✅ Buenas Prácticas

### 1. **Documentación**
- ✅ Incluir docstring con descripción, fecha y autor
- ✅ Comentar cambios complejos o no obvios
- ✅ Mantener un registro de migraciones aplicadas

### 2. **Idempotencia**
- ✅ Verificar existencia antes de crear (IF NOT EXISTS)
- ✅ Permitir ejecutar la migración múltiples veces sin error
- ✅ Usar `CREATE IF NOT EXISTS`, `ALTER IF EXISTS`

### 3. **Reversiones**
- ✅ Incluir función de rollback cuando sea posible
- ✅ Probar rollback en ambiente de desarrollo
- ⚠️ Backups antes de migraciones en producción

### 4. **Testing**
- ✅ Probar en ambiente de desarrollo primero
- ✅ Verificar que la app funcione después de la migración
- ✅ Revisar logs para detectar errores

### 5. **Nomenclatura**
- ✅ Nombres descriptivos: `create_*`, `add_*`, `modify_*`, `seed_*`
- ✅ Incluir fecha o versión si es necesario
- ✅ Usar snake_case para archivos

### 6. **Seguridad**
- ✅ No incluir datos sensibles en migraciones
- ✅ Usar parámetros en queries cuando sea necesario
- ✅ Aplicar principio de mínimo privilegio

## 🚫 Anti-patrones (Evitar)

```python
# ❌ MAL: No verificar si ya existe
def create_table():
    conn.execute("CREATE TABLE users (...)")  # Falla si existe

# ✅ BIEN: Verificar existencia
def create_table():
    conn.execute("CREATE TABLE IF NOT EXISTS users (...)")


# ❌ MAL: No usar transacciones
def migrate():
    conn.execute("CREATE TABLE a ...")
    conn.execute("CREATE TABLE b ...")  # Si falla, tabla 'a' queda creada

# ✅ BIEN: Usar transacciones
def migrate():
    with engine.begin() as conn:  # Rollback automático si falla
        conn.execute("CREATE TABLE a ...")
        conn.execute("CREATE TABLE b ...")


# ❌ MAL: Modificar migraciones ya aplicadas
# Nunca modificar una migración que ya fue ejecutada en producción

# ✅ BIEN: Crear nueva migración
# Siempre crear nueva migración para cambios adicionales


# ❌ MAL: No documentar
def do_stuff():
    conn.execute("""...""")  # ¿Qué hace esto?

# ✅ BIEN: Documentar claramente
def add_user_email_index():
    """
    Crea índice en users.email para mejorar performance de login.
    Fecha: 2026-02-17
    """
    conn.execute("""...""")
```

## 🛠️ Ejecución de Migraciones

### Modo Manual
```bash
# Ejecutar migración
python -m app.migrations.create_producto_tables

# Ejecutar con rollback
python -m app.migrations.create_producto_tables rollback

# Ejecutar seed
python -m app.migrations.seed_initial_roles
```

### Con Docker
```bash
# Ejecutar en contenedor
docker-compose exec app python -m app.migrations.create_enlistment_tables
```

### En CI/CD
```yaml
# .github/workflows/deploy.yml
- name: Run migrations
  run: |
    python -m app.migrations.migration_script_1
    python -m app.migrations.migration_script_2
```

## 📊 Control de Migraciones

### Tabla de control (opcional)
```python
# app/models/migration_model.py
from sqlalchemy import Column, String, DateTime, Boolean
from app.db.base_model import Base
from datetime import datetime

class Migration(Base):
    __tablename__ = "migrations"
    
    name = Column(String(255), primary_key=True)
    applied_at = Column(DateTime, default=datetime.utcnow)
    success = Column(Boolean, default=True)
    rollback_at = Column(DateTime, nullable=True)

# Registrar migración
def register_migration(name: str, success: bool = True):
    db = SessionLocal()
    migration = Migration(name=name, success=success)
    db.add(migration)
    db.commit()
    db.close()
```

## 📚 Recursos Adicionales
- [SQLAlchemy Migrations](https://alembic.sqlalchemy.org/)  (herramienta avanzada)
- [Database Migration Best Practices](https://www.prisma.io/dataguide/types/relational/migration-best-practices)
- [PostgreSQL ALTER TABLE](https://www.postgresql.org/docs/current/sql-altertable.html)
- [Database Indexing Strategies](https://use-the-index-luke.com/)