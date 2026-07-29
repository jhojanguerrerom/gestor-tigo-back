"""
Script de migración para agregar campos de control de estado de ofertas.
Agrega los campos estado_oferta y contador_cargas_ausente en enlistment_manager,
y estado_oferta en enlistment_manager_history.

Ejecutar: python -m app.migrations.add_estado_oferta_field
"""

import sys
import logging
from sqlalchemy import create_engine, text
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def add_estado_oferta_fields():
    """
    Agrega los campos de control de estado de ofertas a las tablas existentes.
    """
    try:
        logger.info("🚀 Iniciando migración: agregar campos de estado de oferta...")
        
        # Crear engine
        engine = create_engine(settings.POSTGRES_URL, pool_pre_ping=True)
        
        with engine.connect() as conn:
            logger.info("📋 Verificando existencia de tablas...")
            
            # Verificar que las tablas existan
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('enlistment_manager', 'enlistment_manager_history')
            """))
            tablas_existentes = [row[0] for row in result]
            
            if 'enlistment_manager' not in tablas_existentes:
                logger.error("❌ La tabla enlistment_manager no existe. Ejecutar create_enlistment_tables.py primero.")
                return False
            
            if 'enlistment_manager_history' not in tablas_existentes:
                logger.error("❌ La tabla enlistment_manager_history no existe. Ejecutar create_enlistment_tables.py primero.")
                return False
            
            logger.info("✅ Tablas verificadas correctamente")
            
            # Agregar campo estado_oferta en tabla principal
            logger.info("📝 Agregando campo estado_oferta en enlistment_manager...")
            try:
                conn.execute(text("""
                    ALTER TABLE enlistment_manager 
                    ADD COLUMN IF NOT EXISTS estado_oferta VARCHAR(50) DEFAULT 'ABIERTO' NOT NULL
                """))
                conn.commit()
                logger.info("✅ Campo estado_oferta agregado en enlistment_manager")
            except Exception as e:
                if "already exists" in str(e).lower():
                    logger.info("ℹ️  Campo estado_oferta ya existe en enlistment_manager")
                else:
                    raise
            
            # Agregar campo contador_cargas_ausente en tabla principal
            logger.info("📝 Agregando campo contador_cargas_ausente en enlistment_manager...")
            try:
                conn.execute(text("""
                    ALTER TABLE enlistment_manager 
                    ADD COLUMN IF NOT EXISTS contador_cargas_ausente INTEGER DEFAULT 0 NOT NULL
                """))
                conn.commit()
                logger.info("✅ Campo contador_cargas_ausente agregado en enlistment_manager")
            except Exception as e:
                if "already exists" in str(e).lower():
                    logger.info("ℹ️  Campo contador_cargas_ausente ya existe en enlistment_manager")
                else:
                    raise
            
            # Agregar campo estado_oferta en tabla de histórico
            logger.info("📝 Agregando campo estado_oferta en enlistment_manager_history...")
            try:
                conn.execute(text("""
                    ALTER TABLE enlistment_manager_history 
                    ADD COLUMN IF NOT EXISTS estado_oferta VARCHAR(50) NOT NULL DEFAULT 'ABIERTO'
                """))
                conn.commit()
                logger.info("✅ Campo estado_oferta agregado en enlistment_manager_history")
            except Exception as e:
                if "already exists" in str(e).lower():
                    logger.info("ℹ️  Campo estado_oferta ya existe en enlistment_manager_history")
                else:
                    raise
            
            # Crear índices
            logger.info("🔍 Creando índices...")
            
            try:
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_enlistment_manager_estado_oferta 
                    ON enlistment_manager (estado_oferta)
                """))
                conn.commit()
                logger.info("✅ Índice idx_enlistment_manager_estado_oferta creado")
            except Exception as e:
                if "already exists" in str(e).lower():
                    logger.info("ℹ️  Índice idx_enlistment_manager_estado_oferta ya existe")
                else:
                    raise
            
            try:
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_enlistment_history_estado_oferta 
                    ON enlistment_manager_history (estado_oferta)
                """))
                conn.commit()
                logger.info("✅ Índice idx_enlistment_history_estado_oferta creado")
            except Exception as e:
                if "already exists" in str(e).lower():
                    logger.info("ℹ️  Índice idx_enlistment_history_estado_oferta ya existe")
                else:
                    raise
            
            # Actualizar registros existentes
            logger.info("🔄 Actualizando registros existentes...")
            
            result = conn.execute(text("""
                UPDATE enlistment_manager 
                SET estado_oferta = 'ABIERTO', contador_cargas_ausente = 0 
                WHERE estado_oferta IS NULL OR estado_oferta = ''
            """))
            conn.commit()
            logger.info(f"✅ Actualizados {result.rowcount} registros en enlistment_manager")
            
            result = conn.execute(text("""
                UPDATE enlistment_manager_history 
                SET estado_oferta = 'ABIERTO' 
                WHERE estado_oferta IS NULL OR estado_oferta = ''
            """))
            conn.commit()
            logger.info(f"✅ Actualizados {result.rowcount} registros en enlistment_manager_history")
        
        logger.info("✅ Migración completada exitosamente")
        logger.info("📊 Campos agregados:")
        logger.info("   - enlistment_manager.estado_oferta (VARCHAR(50), DEFAULT 'ABIERTO')")
        logger.info("   - enlistment_manager.contador_cargas_ausente (INTEGER, DEFAULT 0)")
        logger.info("   - enlistment_manager_history.estado_oferta (VARCHAR(50))")
        logger.info("🔍 Índices creados:")
        logger.info("   - idx_enlistment_manager_estado_oferta")
        logger.info("   - idx_enlistment_history_estado_oferta")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en la migración: {e}", exc_info=True)
        return False
    finally:
        engine.dispose()


def verify_migration():
    """
    Verifica que los campos se agregaron correctamente.
    """
    try:
        engine = create_engine(settings.POSTGRES_URL, pool_pre_ping=True)
        
        with engine.connect() as conn:
            logger.info("\n🔍 Verificando migración...")
            
            # Verificar campos en enlistment_manager
            result = conn.execute(text("""
                SELECT column_name, data_type, column_default
                FROM information_schema.columns
                WHERE table_name = 'enlistment_manager'
                AND column_name IN ('estado_oferta', 'contador_cargas_ausente')
                ORDER BY column_name
            """))
            
            logger.info("📋 Campos en enlistment_manager:")
            for row in result:
                logger.info(f"   - {row[0]}: {row[1]} (default: {row[2]})")
            
            # Verificar campos en enlistment_manager_history
            result = conn.execute(text("""
                SELECT column_name, data_type, column_default
                FROM information_schema.columns
                WHERE table_name = 'enlistment_manager_history'
                AND column_name = 'estado_oferta'
            """))
            
            logger.info("📋 Campos en enlistment_manager_history:")
            for row in result:
                logger.info(f"   - {row[0]}: {row[1]} (default: {row[2]})")
            
            # Verificar índices
            result = conn.execute(text("""
                SELECT indexname
                FROM pg_indexes
                WHERE tablename IN ('enlistment_manager', 'enlistment_manager_history')
                AND indexname LIKE '%estado_oferta%'
                ORDER BY indexname
            """))
            
            logger.info("🔍 Índices creados:")
            for row in result:
                logger.info(f"   - {row[0]}")
            
            logger.info("\n✅ Verificación completada")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en la verificación: {e}", exc_info=True)
        return False
    finally:
        engine.dispose()


if __name__ == "__main__":
    logger.info("=" * 80)
    logger.info("MIGRACIÓN: Agregar campos de estado de oferta")
    logger.info("=" * 80)
    
    success = add_estado_oferta_fields()
    
    if success:
        verify_migration()
        logger.info("\n✅ Migración ejecutada exitosamente")
        sys.exit(0)
    else:
        logger.error("\n❌ Migración falló")
        sys.exit(1)
