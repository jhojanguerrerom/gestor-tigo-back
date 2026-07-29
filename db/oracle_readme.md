# Oracle Database Connection

Este módulo proporciona la conexión a Oracle Database utilizando SQLAlchemy y el driver oracledb.

## Configuración

### 1. Variables de Entorno

Agrega la siguiente variable a tu archivo `.env`:

```env
ORACLE_URL=oracle+oracledb://username:password@hostname:port/service_name
```

Ejemplos de URLs de conexión:
- Con SID: `oracle+oracledb://user:password@localhost:1521/XE`
- Con Service Name: `oracle+oracledb://user:password@localhost:1521/XEPDB1`
- Con TNS: `oracle+oracledb://user:password@(DESCRIPTION=(ADDRESS=(PROTOCOL=TCP)(HOST=hostname)(PORT=1521))(CONNECT_DATA=(SERVICE_NAME=service_name)))`

### 2. Instalación de Dependencias

La dependencia `oracledb` ya está incluida en `requirements.txt`. Para instalar:

```bash
pip install -r requirements.txt
```

### 3. Cliente Oracle (Opcional)

Para mejor rendimiento, instala el Oracle Instant Client:
- Descarga desde: https://www.oracle.com/database/technologies/instant-client.html
- Sigue las instrucciones de instalación para tu SO

## Uso

### Modelo de Ejemplo

```python
from sqlalchemy import Column, Integer, String, Float
from app.db.base_model import Base

class ProductOracle(Base):
    __tablename__ = "products_oracle"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    price = Column(Float, nullable=False)
    description = Column(String(500), nullable=True)
```

### Repositorio

```python
from app.db.oracle_session import SessionLocalOracle
from app.models.product_oracle import ProductOracle

class ProductOracleRepository:
    def __init__(self):
        self.db = SessionLocalOracle()
    
    def list_all(self):
        return self.db.query(ProductOracle).all()
```

### API Endpoints

Los endpoints de Oracle están disponibles en:
- `GET /oracle/products/` - Lista todos los productos
- `POST /oracle/products/` - Crea un nuevo producto
- `GET /oracle/products/{id}` - Obtiene un producto por ID
- `PUT /oracle/products/{id}` - Actualiza un producto
- `DELETE /oracle/products/{id}` - Elimina un producto

## Consideraciones Especiales para Oracle

### 1. Tipos de Datos
- Usa `String(length)` en lugar de `Text` para campos de texto
- Oracle no distingue entre mayúsculas y minúsculas en nombres de tablas/columnas por defecto

### 2. Secuencias
Para auto-incremento en Oracle < 12c:
```python
from sqlalchemy import Sequence
id = Column(Integer, Sequence('product_id_seq'), primary_key=True)
```

### 3. Pool de Conexiones
Oracle soporta pool de conexiones avanzado:
```python
engine_oracle = create_engine(
    settings.ORACLE_URL, 
    pool_pre_ping=True,
    pool_size=20,
    max_overflow=30
)
```

## Troubleshooting

### Error: "DPI-1047: Cannot locate a 64-bit Oracle Client library"
- Instala Oracle Instant Client
- Configura las variables de entorno LD_LIBRARY_PATH (Linux) o PATH (Windows)

### Error de Conexión
- Verifica que el servicio Oracle esté ejecutándose
- Confirma la URL de conexión
- Verifica los permisos del usuario

### Performance
- Usa pool de conexiones apropiado
- Considera usar Oracle RAC para alta disponibilidad
- Implementa índices apropiados en las tablas