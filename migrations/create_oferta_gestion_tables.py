"""
Migración para crear tablas de gestión de ofertas.

Ejecutar con:
    python -m app.migrations.create_oferta_gestion_tables
"""

import sys
import logging
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.db.postgres import SessionLocalPG
from sqlalchemy import text

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


SQL_CREATE_TABLES = """
-- ==========================================
-- TABLA: oferta_accion_catalogo
-- ==========================================
CREATE TABLE IF NOT EXISTS oferta_accion_catalogo (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre_accion VARCHAR(100) NOT NULL UNIQUE,
    descripcion TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    orden INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_oferta_accion_nombre ON oferta_accion_catalogo(nombre_accion);
CREATE INDEX IF NOT EXISTS idx_oferta_accion_active ON oferta_accion_catalogo(is_active);

COMMENT ON TABLE oferta_accion_catalogo IS 'Catálogo de acciones disponibles para gestión de ofertas';
COMMENT ON COLUMN oferta_accion_catalogo.nombre_accion IS 'Nombre de la acción (ej: Asignado, Cancelado, Reconfigurar)';
COMMENT ON COLUMN oferta_accion_catalogo.is_active IS 'Estado activo/inactivo';
COMMENT ON COLUMN oferta_accion_catalogo.orden IS 'Orden de visualización';


-- ==========================================
-- TABLA: oferta_subaccion_catalogo
-- ==========================================
CREATE TABLE IF NOT EXISTS oferta_subaccion_catalogo (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    accion_id UUID NOT NULL REFERENCES oferta_accion_catalogo(id) ON DELETE CASCADE,
    nombre_subaccion TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    orden INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    UNIQUE(accion_id, nombre_subaccion)
);

CREATE INDEX IF NOT EXISTS idx_oferta_subaccion_accion ON oferta_subaccion_catalogo(accion_id);
CREATE INDEX IF NOT EXISTS idx_oferta_subaccion_active ON oferta_subaccion_catalogo(is_active);

COMMENT ON TABLE oferta_subaccion_catalogo IS 'Catálogo de subacciones asociadas a cada acción';
COMMENT ON COLUMN oferta_subaccion_catalogo.accion_id IS 'Referencia a la acción padre';
COMMENT ON COLUMN oferta_subaccion_catalogo.nombre_subaccion IS 'Nombre de la subacción';
COMMENT ON COLUMN oferta_subaccion_catalogo.is_active IS 'Estado activo/inactivo';


-- ==========================================
-- TABLA: oferta_gestion_detalle
-- ==========================================
CREATE TABLE IF NOT EXISTS oferta_gestion_detalle (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    oferta TEXT NOT NULL,
    accion_id UUID NOT NULL REFERENCES oferta_accion_catalogo(id),
    subaccion_id UUID NOT NULL REFERENCES oferta_subaccion_catalogo(id),
    observacion TEXT,
    usuario_login TEXT NOT NULL,
    usuario_nombre TEXT NOT NULL,
    usuario_profile_id INTEGER NOT NULL,
    fecha_gestion TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_gestion_oferta ON oferta_gestion_detalle(oferta);
CREATE INDEX IF NOT EXISTS idx_gestion_usuario ON oferta_gestion_detalle(usuario_login);
CREATE INDEX IF NOT EXISTS idx_gestion_accion ON oferta_gestion_detalle(accion_id);
CREATE INDEX IF NOT EXISTS idx_gestion_fecha ON oferta_gestion_detalle(fecha_gestion);

COMMENT ON TABLE oferta_gestion_detalle IS 'Almacena el detalle de la gestión realizada por el asesor al cerrar una oferta';
COMMENT ON COLUMN oferta_gestion_detalle.oferta IS 'Número de oferta gestionada';
COMMENT ON COLUMN oferta_gestion_detalle.accion_id IS 'Acción seleccionada';
COMMENT ON COLUMN oferta_gestion_detalle.subaccion_id IS 'Subacción seleccionada';
COMMENT ON COLUMN oferta_gestion_detalle.observacion IS 'Observaciones del asesor';
COMMENT ON COLUMN oferta_gestion_detalle.usuario_login IS 'Login del usuario que gestionó';
COMMENT ON COLUMN oferta_gestion_detalle.fecha_gestion IS 'Fecha y hora de la gestión';


-- ==========================================
-- TABLA: oferta_historico_estados
-- ==========================================
CREATE TABLE IF NOT EXISTS oferta_historico_estados (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    oferta TEXT NOT NULL,
    accion_sistema VARCHAR(50) NOT NULL,
    estado_anterior VARCHAR(50) NOT NULL,
    estado_nuevo VARCHAR(50) NOT NULL,
    usuario_login TEXT NOT NULL,
    usuario_nombre TEXT NOT NULL,
    usuario_profile_id INTEGER NOT NULL,
    asesor_asignado_login TEXT,
    asesor_asignado_nombre TEXT,
    motivo TEXT,
    ip_address VARCHAR(50),
    fecha_accion TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_historico_oferta ON oferta_historico_estados(oferta);
CREATE INDEX IF NOT EXISTS idx_historico_usuario ON oferta_historico_estados(usuario_login);
CREATE INDEX IF NOT EXISTS idx_historico_fecha ON oferta_historico_estados(fecha_accion);
CREATE INDEX IF NOT EXISTS idx_historico_accion ON oferta_historico_estados(accion_sistema);

COMMENT ON TABLE oferta_historico_estados IS 'Almacena el histórico completo de cambios de estado de ofertas';
COMMENT ON COLUMN oferta_historico_estados.oferta IS 'Número de oferta';
COMMENT ON COLUMN oferta_historico_estados.accion_sistema IS 'Acción del sistema: CONGELAR, DESCONGELAR, REASIGNAR, GESTIONAR';
COMMENT ON COLUMN oferta_historico_estados.estado_anterior IS 'Estado previo de la oferta';
COMMENT ON COLUMN oferta_historico_estados.estado_nuevo IS 'Estado nuevo de la oferta';
COMMENT ON COLUMN oferta_historico_estados.usuario_login IS 'Usuario que ejecutó la acción';
COMMENT ON COLUMN oferta_historico_estados.asesor_asignado_login IS 'Login del asesor asignado (para reasignaciones)';
COMMENT ON COLUMN oferta_historico_estados.motivo IS 'Motivo de la acción (opcional)';
COMMENT ON COLUMN oferta_historico_estados.ip_address IS 'Dirección IP del usuario';


-- ==========================================
-- TABLA: oferta_configuracion
-- ==========================================
CREATE TABLE IF NOT EXISTS oferta_configuracion (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id INTEGER NOT NULL UNIQUE,
    orden_busqueda VARCHAR(4) NOT NULL DEFAULT 'ASC',
    descripcion TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    updated_by TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    CONSTRAINT check_orden_busqueda CHECK (orden_busqueda IN ('ASC', 'DESC'))
);

CREATE INDEX IF NOT EXISTS idx_configuracion_profile ON oferta_configuracion(profile_id);

COMMENT ON TABLE oferta_configuracion IS 'Configuración de orden de búsqueda de ofertas por perfil de usuario';
COMMENT ON COLUMN oferta_configuracion.profile_id IS 'ID del perfil de usuario';
COMMENT ON COLUMN oferta_configuracion.orden_busqueda IS 'ASC = más antigua primero, DESC = más reciente primero';
COMMENT ON COLUMN oferta_configuracion.descripcion IS 'Descripción del perfil';
COMMENT ON COLUMN oferta_configuracion.updated_by IS 'Usuario que actualizó la configuración';


-- ==========================================
-- MODIFICAR TABLA: enlistment_manager
-- Agregar campos de asignación
-- ==========================================
DO $$ 
BEGIN
    -- Agregar columna usuario_asignado_login
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'enlistment_manager' 
        AND column_name = 'usuario_asignado_login'
    ) THEN
        ALTER TABLE enlistment_manager 
        ADD COLUMN usuario_asignado_login TEXT;
        
        CREATE INDEX idx_enlistment_usuario ON enlistment_manager(usuario_asignado_login);
        
        COMMENT ON COLUMN enlistment_manager.usuario_asignado_login IS 'Login del usuario que tiene asignada la oferta';
    END IF;
    
    -- Agregar columna usuario_asignado_nombre
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'enlistment_manager' 
        AND column_name = 'usuario_asignado_nombre'
    ) THEN
        ALTER TABLE enlistment_manager 
        ADD COLUMN usuario_asignado_nombre TEXT;
        
        COMMENT ON COLUMN enlistment_manager.usuario_asignado_nombre IS 'Nombre completo del usuario asignado';
    END IF;
    
    -- Agregar columna usuario_asignado_profile_id
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'enlistment_manager' 
        AND column_name = 'usuario_asignado_profile_id'
    ) THEN
        ALTER TABLE enlistment_manager 
        ADD COLUMN usuario_asignado_profile_id INTEGER;
        
        COMMENT ON COLUMN enlistment_manager.usuario_asignado_profile_id IS 'Profile ID del usuario asignado';
    END IF;
    
    -- Agregar columna fecha_asignacion
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'enlistment_manager' 
        AND column_name = 'fecha_asignacion'
    ) THEN
        ALTER TABLE enlistment_manager 
        ADD COLUMN fecha_asignacion TIMESTAMP WITH TIME ZONE;
        
        CREATE INDEX idx_enlistment_fecha_asignacion ON enlistment_manager(fecha_asignacion);
        
        COMMENT ON COLUMN enlistment_manager.fecha_asignacion IS 'Fecha y hora en que se asignó la oferta';
    END IF;
    
    -- Agregar columna fecha_gestion
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'enlistment_manager' 
        AND column_name = 'fecha_gestion'
    ) THEN
        ALTER TABLE enlistment_manager 
        ADD COLUMN fecha_gestion TIMESTAMP WITH TIME ZONE;
        
        COMMENT ON COLUMN enlistment_manager.fecha_gestion IS 'Fecha y hora en que se gestionó/cerró la oferta';
    END IF;
END $$;
"""


SQL_INSERT_DATA = """
-- ==========================================
-- DATOS INICIALES: Acciones
-- ==========================================
INSERT INTO oferta_accion_catalogo (nombre_accion, descripcion, orden) 
VALUES 
    ('Asignado', 'Oferta asignada a un elemento de red', 1),
    ('Cancelado', 'Oferta cancelada por diversos motivos', 2),
    ('Reconfigurar', 'Requiere reconfiguración de cobertura', 3)
ON CONFLICT (nombre_accion) DO NOTHING;


-- ==========================================
-- DATOS INICIALES: Subacciones para "Asignado"
-- ==========================================
INSERT INTO oferta_subaccion_catalogo (accion_id, nombre_subaccion, orden)
SELECT 
    id,
    'Se busca elemento con red libre',
    1
FROM oferta_accion_catalogo 
WHERE nombre_accion = 'Asignado'
ON CONFLICT (accion_id, nombre_subaccion) DO NOTHING;

INSERT INTO oferta_subaccion_catalogo (accion_id, nombre_subaccion, orden)
SELECT 
    id,
    'Se busca elemento con red libre / Dirección Estado E',
    2
FROM oferta_accion_catalogo 
WHERE nombre_accion = 'Asignado'
ON CONFLICT (accion_id, nombre_subaccion) DO NOTHING;

INSERT INTO oferta_subaccion_catalogo (accion_id, nombre_subaccion, orden)
SELECT 
    id,
    'Se corrige dirección Estado E',
    3
FROM oferta_accion_catalogo 
WHERE nombre_accion = 'Asignado'
ON CONFLICT (accion_id, nombre_subaccion) DO NOTHING;


-- ==========================================
-- DATOS INICIALES: Subacciones para "Cancelado"
-- ==========================================
INSERT INTO oferta_subaccion_catalogo (accion_id, nombre_subaccion, orden)
SELECT 
    id,
    'Dirección no existe/errada',
    1
FROM oferta_accion_catalogo 
WHERE nombre_accion = 'Cancelado'
ON CONFLICT (accion_id, nombre_subaccion) DO NOTHING;

INSERT INTO oferta_subaccion_catalogo (accion_id, nombre_subaccion, orden)
SELECT 
    id,
    'Sin cobertura',
    2
FROM oferta_accion_catalogo 
WHERE nombre_accion = 'Cancelado'
ON CONFLICT (accion_id, nombre_subaccion) DO NOTHING;

INSERT INTO oferta_subaccion_catalogo (accion_id, nombre_subaccion, orden)
SELECT 
    id,
    'Red copada',
    3
FROM oferta_accion_catalogo 
WHERE nombre_accion = 'Cancelado'
ON CONFLICT (accion_id, nombre_subaccion) DO NOTHING;

INSERT INTO oferta_subaccion_catalogo (accion_id, nombre_subaccion, orden)
SELECT 
    id,
    'Garantia en el ingreso',
    4
FROM oferta_accion_catalogo 
WHERE nombre_accion = 'Cancelado'
ON CONFLICT (accion_id, nombre_subaccion) DO NOTHING;

INSERT INTO oferta_subaccion_catalogo (accion_id, nombre_subaccion, orden)
SELECT 
    id,
    'Minipoligono',
    5
FROM oferta_accion_catalogo 
WHERE nombre_accion = 'Cancelado'
ON CONFLICT (accion_id, nombre_subaccion) DO NOTHING;

INSERT INTO oferta_subaccion_catalogo (accion_id, nombre_subaccion, orden)
SELECT 
    id,
    'Gpon Extendido',
    6
FROM oferta_accion_catalogo 
WHERE nombre_accion = 'Cancelado'
ON CONFLICT (accion_id, nombre_subaccion) DO NOTHING;


-- ==========================================
-- DATOS INICIALES: Subacciones para "Reconfigurar"
-- ==========================================
INSERT INTO oferta_subaccion_catalogo (accion_id, nombre_subaccion, orden)
SELECT 
    id,
    'Cobertura GPON',
    1
FROM oferta_accion_catalogo 
WHERE nombre_accion = 'Reconfigurar'
ON CONFLICT (accion_id, nombre_subaccion) DO NOTHING;

INSERT INTO oferta_subaccion_catalogo (accion_id, nombre_subaccion, orden)
SELECT 
    id,
    'Cobertura HFC',
    2
FROM oferta_accion_catalogo 
WHERE nombre_accion = 'Reconfigurar'
ON CONFLICT (accion_id, nombre_subaccion) DO NOTHING;


-- ==========================================
-- DATOS INICIALES: Configuración para perfil Regular (profile_id = 4)
-- ==========================================
INSERT INTO oferta_configuracion (profile_id, orden_busqueda, descripcion)
VALUES (4, 'ASC', 'Usuarios Regulares - Orden ascendente (más antigua primero)')
ON CONFLICT (profile_id) DO NOTHING;
"""


def run_migration():
    """Ejecuta la migración"""
    db = SessionLocalPG()
    
    try:
        logger.info("=" * 60)
        logger.info("Iniciando migración: create_oferta_gestion_tables")
        logger.info("=" * 60)
        
        # Crear tablas
        logger.info("\n📋 Creando tablas...")
        db.execute(text(SQL_CREATE_TABLES))
        db.commit()
        logger.info("✅ Tablas creadas correctamente")
        
        # Insertar datos iniciales
        logger.info("\n📋 Insertando datos iniciales...")
        db.execute(text(SQL_INSERT_DATA))
        db.commit()
        logger.info("✅ Datos iniciales insertados correctamente")
        
        # Verificar tablas creadas
        logger.info("\n📋 Verificando tablas creadas...")
        result = db.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name LIKE 'oferta_%'
            ORDER BY table_name;
        """))
        
        tables = result.fetchall()
        logger.info(f"✅ Tablas encontradas: {len(tables)}")
        for table in tables:
            logger.info(f"   - {table[0]}")
        
        # Verificar datos insertados
        logger.info("\n📋 Verificando datos insertados...")
        
        result = db.execute(text("SELECT COUNT(*) FROM oferta_accion_catalogo"))
        count_acciones = result.scalar()
        logger.info(f"✅ Acciones insertadas: {count_acciones}")
        
        result = db.execute(text("SELECT COUNT(*) FROM oferta_subaccion_catalogo"))
        count_subacciones = result.scalar()
        logger.info(f"✅ Subacciones insertadas: {count_subacciones}")
        
        result = db.execute(text("SELECT COUNT(*) FROM oferta_configuracion"))
        count_config = result.scalar()
        logger.info(f"✅ Configuraciones insertadas: {count_config}")
        
        # Verificar modificaciones a enlistment_manager
        logger.info("\n📋 Verificando modificaciones a enlistment_manager...")
        result = db.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'enlistment_manager' 
            AND column_name LIKE 'usuario_asignado%' 
            OR column_name LIKE 'fecha_%'
            ORDER BY column_name;
        """))
        
        columns = result.fetchall()
        logger.info(f"✅ Columnas agregadas: {len(columns)}")
        for col in columns:
            logger.info(f"   - {col[0]}")
        
        logger.info("\n" + "=" * 60)
        logger.info("✅ MIGRACIÓN COMPLETADA EXITOSAMENTE")
        logger.info("=" * 60)
        
    except Exception as e:
        db.rollback()
        logger.error(f"\n❌ ERROR en la migración: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run_migration()
