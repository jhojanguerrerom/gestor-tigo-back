"""
Migración: Estandarizar claves de campos_modificados
Fecha: 2026-03-06
Descripción: Cambia las claves "anterior" y "nuevo" a "old" y "new" en el campo JSONB campos_modificados
            de la tabla enlistment_manager_history.
"""

import logging
import json
from sqlalchemy import text
from app.db.postgres import SessionLocalPG

logger = logging.getLogger(__name__)


def migrate_campos_modificados():
    """
    Actualiza todos los registros de enlistment_manager_history
    que tengan las claves 'anterior' y 'nuevo' en campos_modificados
    y las reemplaza por 'old' y 'new'.
    """
    db = SessionLocalPG()
    try:
        logger.info("🔄 Iniciando migración de campos_modificados...")
        
        # Método más seguro: Procesar registro por registro
        # Buscar específicamente las claves 'anterior' y 'nuevo', no el contenido de los valores
        select_query = text("""
            SELECT id, campos_modificados
            FROM enlistment_manager_history
            WHERE campos_modificados IS NOT NULL
              AND (
                  campos_modificados::text ~ '"anterior"\\s*:'
                  OR campos_modificados::text ~ '"nuevo"\\s*:'
              )
        """)
        
        result = db.execute(select_query)
        registros = result.fetchall()
        
        logger.info(f"📊 Registros a actualizar: {len(registros)}")
        
        rows_updated = 0
        
        # Actualizar cada registro
        for row in registros:
            record_id = row[0]
            campos_mod = row[1]
            
            # Transformar el JSON reemplazando las claves
            nuevo_campos_mod = transform_campos_modificados(campos_mod)
            
            # Actualizar el registro usando CAST para convertir el string a JSONB
            update_query = text("""
                UPDATE enlistment_manager_history
                SET campos_modificados = CAST(:campos_modificados AS jsonb)
                WHERE id = :id
            """)
            
            db.execute(update_query, {
                "campos_modificados": json.dumps(nuevo_campos_mod),
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


def transform_campos_modificados(campos_modificados):
    """
    Transforma un diccionario de campos_modificados
    reemplazando 'anterior' por 'old' y 'nuevo' por 'new'.
    
    Args:
        campos_modificados: Dict con campos_modificados
        
    Returns:
        Dict transformado
    """
    if not campos_modificados:
        return campos_modificados
    
    resultado = {}
    
    for key, value in campos_modificados.items():
        if isinstance(value, dict):
            # Si es un dict, transformar las claves internas
            nuevo_value = {}
            for inner_key, inner_value in value.items():
                if inner_key == "anterior":
                    nuevo_value["old"] = inner_value
                elif inner_key == "nuevo":
                    nuevo_value["new"] = inner_value
                else:
                    nuevo_value[inner_key] = inner_value
            resultado[key] = nuevo_value
        else:
            # Si no es un dict, mantener el valor
            resultado[key] = value
    
    return resultado


def verify_migration():
    """
    Verifica que no queden registros con las claves antiguas.
    Busca específicamente las claves 'anterior' y 'nuevo', no el contenido de los valores.
    """
    db = SessionLocalPG()
    try:
        # Query más preciso que busca las claves específicamente, no el contenido
        query = text("""
            SELECT COUNT(*)
            FROM enlistment_manager_history
            WHERE campos_modificados IS NOT NULL
              AND (
                  campos_modificados::text ~ '"anterior"\\s*:'
                  OR campos_modificados::text ~ '"nuevo"\\s*:'
              )
        """)
        
        result = db.execute(query)
        count = result.scalar()
        
        if count == 0:
            logger.info("✅ Verificación exitosa: No hay registros con claves antiguas")
            return True
        else:
            logger.warning(f"⚠️ Aún quedan {count} registros con claves antiguas")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error en verificación: {e}")
        return False
    finally:
        db.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("\n" + "="*60)
    print("MIGRACIÓN: Estandarizar campos_modificados")
    print("="*60)
    
    # Ejecutar migración
    result = migrate_campos_modificados()
    print(f"\nResultado: {result}")
    
    # Verificar
    print("\n" + "-"*60)
    print("Verificando migración...")
    print("-"*60)
    is_ok = verify_migration()
    
    if is_ok:
        print("\n✅ Migración completada exitosamente")
    else:
        print("\n⚠️ La migración requiere revisión")
