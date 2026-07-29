"""
Migración: Agregar índice compuesto para optimizar filtrado por concepto en enlistment_manager

Este índice mejora el performance de queries que filtran por oferta y concepto,
especialmente para reportes que hacen JOIN entre oferta_gestion_detalle y enlistment_manager.

Índice: idx_enlistment_manager_oferta_concepto
Campos: (oferta, (campos_dinamicos->>'concepto'))

Fecha: 2026-04-24
"""
import logging
from app.db.postgres import engine_pg
from sqlalchemy import text

logger = logging.getLogger("migration_index_concepto")


def run_migration():
    """
    Ejecuta la migración para agregar el índice compuesto.
    """
    try:
        logger.info("=" * 60)
        logger.info("INICIANDO MIGRACIÓN: add_index_concepto_enlistment")
        logger.info("=" * 60)
        
        # Usar conexión con autocommit para CREATE INDEX CONCURRENTLY
        conn = engine_pg.raw_connection()
        conn.set_isolation_level(0)  # AUTOCOMMIT mode
        cursor = conn.cursor()
        
        try:
            # Verificar si el índice ya existe
            logger.info("Verificando si el índice ya existe...")
            cursor.execute("""
                SELECT indexname 
                FROM pg_indexes 
                WHERE tablename = 'enlistment_manager' 
                AND indexname = 'idx_enlistment_manager_oferta_concepto'
            """)
            
            if cursor.fetchone():
                logger.info("ℹ️  El índice ya existe, omitiendo creación")
                return True
            
            # Crear índice compuesto
            logger.info("Creando índice compuesto (oferta, concepto)...")
            logger.info("⚠️  Este proceso puede tomar varios minutos dependiendo del volumen de datos...")
            
            cursor.execute("""
                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_enlistment_manager_oferta_concepto 
                ON enlistment_manager (oferta, (campos_dinamicos->>'concepto'))
            """)
            
            # Verificar creación
            logger.info("Verificando creación del índice...")
            cursor.execute("""
                SELECT 
                    indexname,
                    indexdef
                FROM pg_indexes 
                WHERE tablename = 'enlistment_manager' 
                AND indexname = 'idx_enlistment_manager_oferta_concepto'
            """)
            
            index_info = cursor.fetchone()
            if index_info:
                logger.info(f"✅ Índice creado: {index_info[0]}")
                logger.info(f"   Definición: {index_info[1]}")
            
            logger.info("✅ Migración completada exitosamente")
            
        finally:
            cursor.close()
            conn.close()
            
        logger.info("=" * 60)
        logger.info("RESUMEN DE MIGRACIÓN")
        logger.info("=" * 60)
        logger.info("✅ Índice compuesto creado: idx_enlistment_manager_oferta_concepto")
        logger.info("✅ Campos: (oferta, campos_dinamicos->>'concepto')")
        logger.info("✅ Performance mejorado para JOINs con filtro de concepto")
        logger.info("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error durante la migración: {e}")
        raise


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_migration()
