"""
Migración: Actualizar concepto desde concepto_id
Fecha: 2026-03-11
Descripción: Actualiza el campo 'concepto' dentro de campos_dinamicos (JSONB) 
            con el valor de 'concepto_id' cuando este último no sea nulo ni vacío.
"""

import logging
import json
from sqlalchemy import text
from app.db.postgres import SessionLocalPG

logger = logging.getLogger(__name__)


def migrate_concepto_from_concepto_id():
    """
    Actualiza todos los registros de enlistment_manager
    donde el campo 'concepto_id' dentro de campos_dinamicos tenga un valor válido,
    reemplazando el valor de 'concepto' con el valor de 'concepto_id'.
    """
    db = SessionLocalPG()
    try:
        logger.info("🔄 Iniciando migración: Actualizar concepto desde concepto_id...")
        
        # Buscar registros donde concepto_id existe, no es nulo, y no es cadena vacía
        select_query = text("""
            SELECT id, campos_dinamicos
            FROM enlistment_manager
            WHERE campos_dinamicos IS NOT NULL
              AND campos_dinamicos->>'concepto_id' IS NOT NULL
              AND TRIM(campos_dinamicos->>'concepto_id') != ''
        """)
        
        result = db.execute(select_query)
        registros = result.fetchall()
        
        logger.info(f"📊 Registros a actualizar: {len(registros)}")
        
        rows_updated = 0
        
        # Actualizar cada registro
        for row in registros:
            record_id = row[0]
            campos_dinamicos = row[1]
            
            # Verificar que concepto_id tenga un valor válido
            concepto_id = campos_dinamicos.get('concepto_id')
            
            if concepto_id and str(concepto_id).strip():
                # Crear una copia del diccionario y actualizar el campo concepto
                nuevo_campos_dinamicos = dict(campos_dinamicos)
                nuevo_campos_dinamicos['concepto'] = concepto_id
                
                # Actualizar el registro usando CAST para convertir el string a JSONB
                update_query = text("""
                    UPDATE enlistment_manager
                    SET campos_dinamicos = CAST(:campos_dinamicos AS jsonb),
                        updated_at = NOW()
                    WHERE id = :id
                """)
                
                db.execute(update_query, {
                    "campos_dinamicos": json.dumps(nuevo_campos_dinamicos),
                    "id": str(record_id)
                })
                
                rows_updated += 1
                
                # Commit cada 100 registros
                if rows_updated % 100 == 0:
                    db.commit()
                    logger.info(f"⏳ Procesados {rows_updated}/{len(registros)} registros...")
        
        # Commit final
        db.commit()
        
        logger.info(f"✅ Migración completada: {rows_updated} registros actualizados")
        
        return {
            "status": "success",
            "rows_updated": rows_updated,
            "message": f"Se actualizaron {rows_updated} registros correctamente"
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error en migración: {e}", exc_info=True)
        return {
            "status": "error",
            "message": str(e)
        }
    finally:
        db.close()


def verify_migration():
    """
    Verifica que la migración se haya aplicado correctamente.
    Compara concepto y concepto_id en registros que deberían estar sincronizados.
    """
    db = SessionLocalPG()
    try:
        logger.info("🔍 Verificando migración...")
        
        # Buscar registros donde concepto_id existe pero es diferente de concepto
        verify_query = text("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE 
                    WHEN campos_dinamicos->>'concepto' = campos_dinamicos->>'concepto_id' 
                    THEN 1 
                    ELSE 0 
                END) as sincronizados,
                SUM(CASE 
                    WHEN campos_dinamicos->>'concepto' != campos_dinamicos->>'concepto_id' 
                    THEN 1 
                    ELSE 0 
                END) as desincronizados
            FROM enlistment_manager
            WHERE campos_dinamicos->>'concepto_id' IS NOT NULL
              AND TRIM(campos_dinamicos->>'concepto_id') != ''
        """)
        
        result = db.execute(verify_query)
        row = result.fetchone()
        
        total = row[0] or 0
        sincronizados = row[1] or 0
        desincronizados = row[2] or 0
        
        logger.info(f"📊 Verificación completada:")
        logger.info(f"   Total registros con concepto_id: {total}")
        logger.info(f"   ✅ Sincronizados (concepto = concepto_id): {sincronizados}")
        logger.info(f"   ⚠️  Desincronizados (concepto != concepto_id): {desincronizados}")
        
        if desincronizados == 0:
            logger.info("✅ Verificación exitosa: Todos los registros están sincronizados")
        else:
            logger.warning(f"⚠️  Advertencia: {desincronizados} registros aún están desincronizados")
        
        return {
            "status": "success" if desincronizados == 0 else "warning",
            "total": total,
            "sincronizados": sincronizados,
            "desincronizados": desincronizados
        }
        
    except Exception as e:
        logger.error(f"❌ Error en verificación: {e}", exc_info=True)
        return {
            "status": "error",
            "message": str(e)
        }
    finally:
        db.close()


if __name__ == "__main__":
    """
    Permite ejecutar la migración desde la línea de comandos.
    
    Uso:
        python -m app.migrations.update_concepto_from_concepto_id
    """
    import sys
    
    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("\n" + "="*60)
    print("   MIGRACIÓN: Actualizar concepto desde concepto_id")
    print("="*60 + "\n")
    
    # Ejecutar migración
    resultado = migrate_concepto_from_concepto_id()
    
    print("\n" + "-"*60)
    print(f"Resultado: {resultado['status'].upper()}")
    if resultado['status'] == 'success':
        print(f"Registros actualizados: {resultado['rows_updated']}")
    else:
        print(f"Error: {resultado['message']}")
    print("-"*60 + "\n")
    
    # Verificar migración
    print("\n" + "="*60)
    print("   VERIFICACIÓN DE MIGRACIÓN")
    print("="*60 + "\n")
    
    verificacion = verify_migration()
    
    print("\n" + "-"*60)
    if verificacion['status'] == 'success':
        print("✅ VERIFICACIÓN EXITOSA")
    elif verificacion['status'] == 'warning':
        print("⚠️  VERIFICACIÓN CON ADVERTENCIAS")
    else:
        print("❌ ERROR EN VERIFICACIÓN")
    print("-"*60 + "\n")
    
    # Salir con código apropiado
    sys.exit(0 if verificacion['status'] in ['success', 'warning'] else 1)
