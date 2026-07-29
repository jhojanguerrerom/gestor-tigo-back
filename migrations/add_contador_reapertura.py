"""
Migración: Agregar campo contador_cargas_reapertura a enlistment_manager

Este campo controla la reapertura de ofertas CERRADAS que fueron gestionadas.
Si una oferta tiene asesor asignado y gestión, requiere 3 cargas consecutivas
antes de reabrirse automáticamente.

Fecha: 2026-04-23
"""
import logging
from app.db.postgres import engine_pg
from sqlalchemy import text

logger = logging.getLogger("migration_contador_reapertura")


def run_migration():
    """
    Ejecuta la migración para agregar el campo contador_cargas_reapertura.
    """
    try:
        logger.info("=" * 60)
        logger.info("INICIANDO MIGRACIÓN: add_contador_reapertura")
        logger.info("=" * 60)
        
        with engine_pg.begin() as conn:  # Usar begin() para auto-commit
            # Agregar columna contador_cargas_reapertura
            logger.info("Agregando columna contador_cargas_reapertura...")
            conn.execute(text("""
                ALTER TABLE enlistment_manager 
                ADD COLUMN IF NOT EXISTS contador_cargas_reapertura INTEGER DEFAULT 0 NOT NULL;
            """))
            
            # Agregar comentario
            logger.info("Agregando comentario a la columna...")
            conn.execute(text("""
                COMMENT ON COLUMN enlistment_manager.contador_cargas_reapertura IS 
                'Contador de cargas consecutivas donde oferta CERRADA vuelve a aparecer. Se usa para evitar reaperturas inmediatas de ofertas gestionadas.';
            """))
            
            logger.info("✅ Migración completada exitosamente")
            
        logger.info("=" * 60)
        logger.info("RESUMEN DE MIGRACIÓN")
        logger.info("=" * 60)
        logger.info("✅ Campo contador_cargas_reapertura agregado")
        logger.info("✅ Valores inicializados en 0 (por DEFAULT)")
        logger.info("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error durante la migración: {e}")
        raise


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_migration()
