# Models (Modelos ORM)

## 📋 Descripción
Esta carpeta contiene las **definiciones de modelos ORM** usando SQLAlchemy. Cada modelo representa una tabla en la base de datos y define su estructura (columnas, tipos de datos, relaciones, constraints).

## 🔗 Conexiones
- **Usado por**: Repositories (queries ORM)
- **Usa**: 
  - DB/base_model.py (clase Base)
  - SQLAlchemy (ORM)
- **Define**: Estructura de tablas en PostgreSQL/Oracle/MySQL

## 🎯 Responsabilidades
1. **Definir estructura** de tablas (columnas, tipos)
2. **Establecer relaciones** entre tablas (ForeignKey, relationships)
3. **Definir constraints** (unique, nullable, default)
4. **Agregar índices** para optimización
5. **Métodos auxiliares** (to_dict, __repr__)
6. **Validaciones** a nivel de modelo (opcional)

## 📂 Estructura
```
models/
├── __init__.py
├── readme.md
├── user_model.py                  # Usuarios del sistema
├── menu_model.py                  # Menús de navegación
├── submenu_model.py               # Submenús
├── enlistment_manager_model.py    # Gestión de enlistments
├── automation_config_model.py     # Configuración automatización
├── gestor_operacion_model.py      # Operaciones del gestor
└── log_mongo.py                   # Logs en MongoDB
```

## 🔄 Flujo en la Arquitectura
```
Migration → Crea tabla basada en Model
                      ↓
Repository → Query usando Model ORM → Database
                      ↓
            Retorna instancias del Model
                      ↓
Service → Manipula objetos Model
                      ↓
Schema → Serializa Model a dict/JSON
```

## 📝 Ejemplos de Implementación

### 1. Modelo Básico
```python
# app/models/user_model.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base_model import Base


class User(Base):
    """
    Modelo de Usuario del sistema.
    Tabla: users
    """
    __tablename__ = "users"
    
    # Columnas
    id = Column(Integer, primary_key=True, index=True)
    login = Column(String(50), unique=True, nullable=False, index=True)
    full_name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False, index=True)
    user_identify = Column(String(20), unique=True, nullable=False)  # DNI/Cédula
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Método auxiliar para serialización
    def to_dict(self):
        """Convierte el modelo a diccionario."""
        return {
            "id": self.id,
            "login": self.login,
            "full_name": self.full_name,
            "email": self.email,
            "user_identify": self.user_identify,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def __repr__(self):
        """Representación legible del objeto."""
        return f"<User(id={self.id}, login='{self.login}', email='{self.email}')>"
```

### 2. Modelo con Relaciones (One-to-Many)
```python
# app/models/categoria_model.py
from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.orm import relationship
from app.db.base_model import Base


class Categoria(Base):
    """Modelo de Categoría de productos."""
    __tablename__ = "categorias"
    
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False, unique=True)
    descripcion = Column(Text, nullable=True)
    
    # Relación: Una categoría tiene muchos productos
    productos = relationship("Producto", back_populates="categoria")
    
    def to_dict(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "descripcion": self.descripcion,
        }


# app/models/producto_model.py
from sqlalchemy import Column, Integer, String, Numeric, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base_model import Base


class Producto(Base):
    """Modelo de Producto."""
    __tablename__ = "productos"
    
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(200), nullable=False, index=True)
    precio = Column(Numeric(10, 2), nullable=False)
    categoria_id = Column(Integer, ForeignKey("categorias.id"), nullable=False)
    
    # Relación: Muchos productos pertenecen a una categoría
    categoria = relationship("Categoria", back_populates="productos")
    
    def to_dict(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "precio": float(self.precio),
            "categoria_id": self.categoria_id,
            "categoria": self.categoria.to_dict() if self.categoria else None,
        }
```

### 3. Modelo con Relaciones (Many-to-Many)
```python
# app/models/estudiante_model.py
from sqlalchemy import Column, Integer, String, Table, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base_model import Base

# Tabla intermedia (many-to-many)
estudiante_curso = Table(
    'estudiante_curso',
    Base.metadata,
    Column('estudiante_id', Integer, ForeignKey('estudiantes.id'), primary_key=True),
    Column('curso_id', Integer, ForeignKey('cursos.id'), primary_key=True),
)


class Estudiante(Base):
    """Modelo de Estudiante."""
    __tablename__ = "estudiantes"
    
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    
    # Relación many-to-many con Curso
    cursos = relationship("Curso", secondary=estudiante_curso, back_populates="estudiantes")
    
    def to_dict(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "cursos": [curso.to_dict() for curso in self.cursos] if self.cursos else []
        }


class Curso(Base):
    """Modelo de Curso."""
    __tablename__ = "cursos"
    
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    
    # Relación many-to-many con Estudiante
    estudiantes = relationship("Estudiante", secondary=estudiante_curso, back_populates="cursos")
    
    def to_dict(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
        }
```

### 4. Modelo con JSONB (PostgreSQL)
```python
# app/models/enlistment_manager_model.py
from sqlalchemy import Column, Integer, String, DateTime, JSON
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
from app.db.base_model import Base


class EnlistmentManager(Base):
    """
    Modelo de Enlistment Manager con campos dinámicos.
    Usa JSONB para almacenar datos flexibles.
    """
    __tablename__ = "enlistment_manager"
    
    id = Column(Integer, primary_key=True, index=True)
    pedido_crm = Column(String(50), nullable=False, unique=True, index=True)
    estado = Column(String(50), nullable=False, index=True)
    
    # Campos dinámicos almacenados en JSONB
    campos_dinamicos = Column(JSONB, nullable=False, default={})
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            "id": self.id,
            "pedido_crm": self.pedido_crm,
            "estado": self.estado,
            "campos_dinamicos": self.campos_dinamicos,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
```

### 5. Modelo para MongoDB
```python
# app/models/log_mongo.py
from datetime import datetime
from typing import Dict, Any


class LogMongo:
    """
    Modelo para logs en MongoDB (no usa ORM).
    Define estructura de documentos de logs.
    """
    
    @staticmethod
    def create_log(
        level: str,
        message: str,
        user_id: int = None,
        extra_data: Dict[str, Any] = None
    ) -> dict:
        """
        Crea un documento de log para MongoDB.
        
        Args:
            level: Nivel del log (INFO, WARNING, ERROR)
            message: Mensaje del log
            user_id: ID del usuario (opcional)
            extra_data: Datos adicionales (opcional)
        
        Returns:
            Diccionario con estructura del log
        """
        return {
            "level": level,
            "message": message,
            "user_id": user_id,
            "extra_data": extra_data or {},
            "created_at": datetime.utcnow(),
            "hostname": "app-server",  # Puede ser dinámico
        }
    
    @staticmethod
    def create_audit_log(
        action: str,
        user_id: int,
        resource_type: str,
        resource_id: int = None,
        changes: Dict[str, Any] = None
    ) -> dict:
        """
        Crea un log de auditoría.
        
        Args:
            action: Acción realizada (CREATE, UPDATE, DELETE)
            user_id: ID del usuario que realizó la acción
            resource_type: Tipo de recurso afectado
            resource_id: ID del recurso (opcional)
            changes: Cambios realizados (opcional)
        
        Returns:
            Diccionario con estructura del audit log
        """
        return {
            "action": action,
            "user_id": user_id,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "changes": changes or {},
            "timestamp": datetime.utcnow(),
        }
```

## ✅ Buenas Prácticas

### 1. **Nomenclatura**
- ✅ Nombres de clases en PascalCase (User, ProductCategory)
- ✅ Nombres de tablas en snake_case (users, product_categories)
- ✅ Nombres de columnas en snake_case (user_id, created_at)
- ✅ Agregar docstrings a cada modelo

### 2. **Columnas**
- ✅ Definir primary_key explícitamente
- ✅ Usar index=True para columnas frecuentemente consultadas
- ✅ Definir nullable apropiadamente (False por defecto es más seguro)
- ✅ Usar unique=True para campos únicos
- ✅ Agregar valores default cuando sea apropiado

### 3. **Tipos de Datos**
- ✅ String(length) para textos cortos con límite
- ✅ Text para textos largos sin límite
- ✅ Numeric(precision, scale) para valores monetarios
- ✅ DateTime para timestamps
- ✅ Boolean para flags
- ✅ JSONB (PostgreSQL) para datos flexibles

### 4. **Relaciones**
- ✅ Definir ForeignKey correctamente
- ✅ Usar relationship() para navegación ORM
- ✅ Especificar back_populates para relaciones bidireccionales
- ✅ Usar cascade cuando sea apropiado

### 5. **Métodos Auxiliares**
- ✅ Implementar to_dict() para serialización
- ✅ Implementar __repr__() para debugging
- ✅ Agregar métodos de negocio si son específicos del modelo

### 6. **Timestamps**
- ✅ Agregar created_at con default=datetime.utcnow
- ✅ Agregar updated_at con onupdate=datetime.utcnow
- ✅ Usar UTC para todos los timestamps

## 🚫 Anti-patrones (Evitar)

```python
# ❌ MAL: No especificar longitud en String
nombre = Column(String)  # Sin límite, no recomendado

# ✅ BIEN: Especificar longitud
nombre = Column(String(100))


# ❌ MAL: No usar índices
email = Column(String(100), unique=True)  # Sin índice explícito

# ✅ BIEN: Agregar índice
email = Column(String(100), unique=True, index=True)


# ❌ MAL: No definir nullable
descripcion = Column(String(200))  # ¿Puede ser NULL?

# ✅ BIEN: Ser explícito
descripcion = Column(String(200), nullable=True)


# ❌ MAL: No usar ForeignKey correctamente
categoria_id = Column(Integer)  # Sin constraint

# ✅ BIEN: Usar ForeignKey
categoria_id = Column(Integer, ForeignKey("categorias.id"))


# ❌ MAL: Lógica de negocio compleja en to_dict()
def to_dict(self):
    # ❌ No hacer queries aquí
    related_data = db.query(OtherModel).filter(...).all()
    return {...}

# ✅ BIEN: Solo serializar datos del modelo
def to_dict(self):
    return {
        "id": self.id,
        "nombre": self.nombre,
    }


# ❌ MAL: No usar datetime.utcnow() como función
created_at = Column(DateTime, default=datetime.utcnow())  # ❌ Se evalúa al definir

# ✅ BIEN: Pasar la función sin ejecutarla
created_at = Column(DateTime, default=datetime.utcnow)  # ✅ Se evalúa al insertar
```

## 📚 Tipos de Datos Comunes

### SQLAlchemy Core Types
```python
from sqlalchemy import (
    Integer,      # Enteros
    String,       # Texto con longitud fija
    Text,         # Texto sin límite
    Boolean,      # True/False
    DateTime,     # Fecha y hora
    Date,         # Solo fecha
    Time,         # Solo hora
    Numeric,      # Números decimales precisos
    Float,        # Números decimales (menos precisión)
    JSON,         # JSON (genérico)
)

# PostgreSQL específicos
from sqlalchemy.dialects.postgresql import (
    JSONB,        # JSON binario (más eficiente)
    ARRAY,        # Arrays
    UUID,         # UUIDs
)
```

## 🔧 Ejemplo Completo: Modelo de Pedido

```python
# app/models/pedido_model.py
"""
Modelo completo de Pedido con todas las buenas prácticas.
"""
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.db.base_model import Base


class EstadoPedido(enum.Enum):
    """Enum para estados del pedido."""
    PENDIENTE = "pendiente"
    PROCESANDO = "procesando"
    COMPLETADO = "completado"
    CANCELADO = "cancelado"


class Pedido(Base):
    """
    Modelo de Pedido.
    
    Attributes:
        id: Identificador único
        numero: Número de pedido (único)
        cliente_id: ID del cliente
        total: Total del pedido
        estado: Estado actual del pedido
        created_at: Fecha de creación
        updated_at: Fecha de última actualización
    """
    __tablename__ = "pedidos"
    
    # Primary Key
    id = Column(Integer, primary_key=True, index=True)
    
    # Datos del pedido
    numero = Column(String(50), unique=True, nullable=False, index=True)
    total = Column(Numeric(10, 2), nullable=False, default=0)
    estado = Column(
        Enum(EstadoPedido),
        nullable=False,
        default=EstadoPedido.PENDIENTE,
        index=True
    )
    
    # Relaciones
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False, index=True)
    cliente = relationship("Cliente", back_populates="pedidos")
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self, include_cliente=False):
        """
        Serializa el pedido a diccionario.
        
        Args:
            include_cliente: Si True, incluye datos del cliente
        
        Returns:
            Diccionario con datos del pedido
        """
        data = {
            "id": self.id,
            "numero": self.numero,
            "total": float(self.total),
            "estado": self.estado.value,
            "cliente_id": self.cliente_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        
        if include_cliente and self.cliente:
            data["cliente"] = self.cliente.to_dict()
        
        return data
    
    def __repr__(self):
        return f"<Pedido(id={self.id}, numero='{self.numero}', estado='{self.estado.value}')>"
```

## 📚 Recursos Adicionales
- [SQLAlchemy ORM Tutorial](https://docs.sqlalchemy.org/en/20/orm/tutorial.html)
- [SQLAlchemy Relationships](https://docs.sqlalchemy.org/en/20/orm/relationship_api.html)
- [SQLAlchemy Column Types](https://docs.sqlalchemy.org/en/20/core/type_basics.html)
- [Database Design Best Practices](https://www.ibm.com/topics/database-design)