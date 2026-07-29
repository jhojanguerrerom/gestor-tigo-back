"""
Script de migración para crear las tablas de Enlistment Manager en PostgreSQL.
Ejecutar: python -m app.migrations.create_enlistment_tables
"""

import sys
import logging
from sqlalchemy import create_engine, text
from app.core.config import settings
from app.db.base_model import Base
from app.models.enlistment_manager_model import (
    EnlistmentManager,
    EnlistmentManagerHistory,
    EnlistmentManagerControl
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_enlistment_tables():
    """
    Crea las tablas de Enlistment Manager y sus índices.
    """
    try:
        logger.info("🚀 Iniciando creación de tablas Enlistment Manager...")
        
        # Crear engine
        engine = create_engine(settings.POSTGRES_URL, pool_pre_ping=True)
        
        # Crear tablas
        logger.info("📋 Creando tablas...")
        Base.metadata.create_all(bind=engine, tables=[
            EnlistmentManager.__table__,
            EnlistmentManagerHistory.__table__,
            EnlistmentManagerControl.__table__
        ])
        
        # Crear índices adicionales para JSONB
        logger.info("🔍 Creando índices GIN para campos JSONB...")
        
        with engine.connect() as conn:
            # Índice GIN para búsquedas en JSONB de enlistment_manager
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_enlistment_manager_campos_gin 
                ON enlistment_manager USING GIN (campos_dinamicos);
            """))
            
            # Índice GIN para búsquedas en JSONB de history
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_enlistment_history_campos_gin 
                ON enlistment_manager_history USING GIN (campos_dinamicos);
            """))
            
            # Índices adicionales para campos frecuentes en JSONB
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_enlistment_manager_responsable 
                ON enlistment_manager ((campos_dinamicos->>'responsable'));
            """))
            
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_enlistment_manager_estado_oferta 
                ON enlistment_manager ((campos_dinamicos->>'estado_oferta'));
            """))
            
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_enlistment_manager_tecnologia 
                ON enlistment_manager ((campos_dinamicos->>'tecnologia'));
            """))
            
            # Índice para fechas en el histórico
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_enlistment_history_date 
                ON enlistment_manager_history (create_date_automation DESC);
            """))
            
            conn.commit()
        
        logger.info("✅ Tablas e índices creados exitosamente")
        logger.info("📊 Tablas creadas:")
        logger.info("   - enlistment_manager")
        logger.info("   - enlistment_manager_history")
        logger.info("   - enlistment_manager_control")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error al crear tablas: {e}", exc_info=True)
        return False
    finally:
        engine.dispose()


def verify_tables():
    """
    Verifica que las tablas se crearon correctamente.
    """
    try:
        engine = create_engine(settings.POSTGRES_URL, pool_pre_ping=True)
        
        with engine.connect() as conn:
            # Verificar tabla principal
            result = conn.execute(text("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_name IN ('enlistment_manager', 'enlistment_manager_history', 'enlistment_manager_control');
            """))
            
            count = result.scalar()
            
            if count == 3:
                logger.info("✅ Verificación exitosa: 3 tablas encontradas")
                return True
            else:
                logger.warning(f"⚠️ Solo se encontraron {count} de 3 tablas")
                return False
                
    except Exception as e:
        logger.error(f"❌ Error en verificación: {e}")
        return False
    finally:
        engine.dispose()


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("MIGRACIÓN: Crear tablas Enlistment Manager")
    logger.info("=" * 60)
    
    success = create_enlistment_tables()
    
    if success:
        logger.info("\n🔍 Verificando tablas creadas...")
        verify_tables()
        logger.info("\n✅ Migración completada exitosamente")
        logger.info("\n📝 Próximos pasos:")
        logger.info("   1. Ejecutar POST /v1/processdatagestor para la primera carga")
        logger.info("   2. Verificar los logs de carga")
        logger.info("   3. Consultar datos con GET /v1/enlistment")
        sys.exit(0)
    else:
        logger.error("\n❌ Migración falló")
        sys.exit(1)
