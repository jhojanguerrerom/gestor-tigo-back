"""
Migración: Agregar funcionalidades de OFERTA PAUSADA, MALO y RFS

Descripción:
    Esta migración agrega tres nuevos conceptos especiales al gestor de ofertas:
    
    1. OFERTA PAUSADA: Permite a los asesores pausar temporalmente ofertas que están gestionando.
       - Requiere tiempo mínimo de trabajo (configurable, default 7 min)
       - Límite de ofertas pausadas por asesor (configurable, default 3)
       - Estado nuevo: EN_TRAMITE_PAUSADO
       - Los supervisores pueden liberar ofertas pausadas
       
    2. MALO: Marca ofertas con datos incorrectos/inválidos
       - Cierra la oferta automáticamente
       - No se actualiza en cargas automáticas
       - Solo supervisores pueden liberar
       
    3. RFS (Ready For Service): Marca ofertas completadas
       - Cierra la oferta automáticamente  
       - No se actualiza en cargas automáticas
       - Solo supervisores pueden liberar

Cambios en Base de Datos:
    - Nueva tabla: oferta_configuracion_pausada (configuración de pausas)
    - Nueva tabla: oferta_pausada_tracking (histórico de pausas)
    - Nuevas acciones en catálogo: OFERTA PAUSADA, MALO, RFS
    - Nuevas subacciones asociadas

Fecha: 2026-04-23
Autor: Sistema Gestor v2
"""

import logging
from sqlalchemy.orm import Session
from app.db.postgres import SessionLocalPG, engine_pg
from app.db.base_model import Base
from app.models.oferta_gestion_model import (
    OfertaConfiguracionPausada,
    OfertaPausadaTracking,
    OfertaAccionCatalogo,
    OfertaSubaccionCatalogo
)
import uuid

logger = logging.getLogger("migration_pausada_malo_rfs")


def run_migration():
    """
    Ejecuta la migración para agregar las funcionalidades de OFERTA PAUSADA, MALO y RFS.
    """
    db: Session = SessionLocalPG()
    
    try:
        logger.info("="*80)
        logger.info("INICIANDO MIGRACIÓN: Agregar OFERTA PAUSADA, MALO y RFS")
        logger.info("="*80)
        
        # ==========================================
        # PASO 0: Crear las tablas nuevas en la base de datos
        # ==========================================
        logger.info("\n📝 PASO 0: Creando tablas nuevas en PostgreSQL...")
        
        # Importar todos los modelos para asegurar que estén registrados
        from app.models import oferta_gestion_model
        
        # Crear solo las tablas nuevas si no existen
        Base.metadata.create_all(bind=engine_pg, checkfirst=True)
        logger.info("   ✅ Tablas creadas/verificadas en PostgreSQL")
        
        # ==========================================
        # PASO 1: Crear configuración inicial para ofertas pausadas
        # ==========================================
        logger.info("\n📝 PASO 1: Creando configuración inicial de ofertas pausadas...")
        
        # Verificar si ya existe configuración
        config_existente = db.query(OfertaConfiguracionPausada).filter(
            OfertaConfiguracionPausada.is_active == True
        ).first()
        
        if config_existente:
            logger.info(f"   ⚠️  Configuración ya existe: ID {config_existente.id}")
        else:
            config_pausada = OfertaConfiguracionPausada(
                tiempo_minimo_pausa_minutos=7,  # 7 minutos por defecto
                max_ofertas_pausadas_por_asesor=3,  # 3 ofertas máximo por defecto
                is_active=True,
                updated_by="MIGRATION_SYSTEM"
            )
            db.add(config_pausada)
            db.commit()
            db.refresh(config_pausada)
            logger.info(f"   ✅ Configuración creada: ID {config_pausada.id}")
            logger.info(f"      - Tiempo mínimo para pausar: 7 minutos")
            logger.info(f"      - Máximo ofertas pausadas por asesor: 3")
        
        # ==========================================
        # PASO 2: Crear acción OFERTA PAUSADA
        # ==========================================
        logger.info("\n📝 PASO 2: Creando acción OFERTA PAUSADA...")
        
        accion_pausada = db.query(OfertaAccionCatalogo).filter(
            OfertaAccionCatalogo.nombre_accion == "OFERTA PAUSADA"
        ).first()
        
        if accion_pausada:
            logger.info(f"   ⚠️  Acción 'OFERTA PAUSADA' ya existe: ID {accion_pausada.id}")
        else:
            accion_pausada = OfertaAccionCatalogo(
                nombre_accion="OFERTA PAUSADA",
                descripcion="Pausa temporal de oferta para gestión posterior. Requiere tiempo mínimo de trabajo.",
                is_active=True,
                orden=100
            )
            db.add(accion_pausada)
            db.commit()
            db.refresh(accion_pausada)
            logger.info(f"   ✅ Acción 'OFERTA PAUSADA' creada: ID {accion_pausada.id}")
        
        # Crear subacción para OFERTA PAUSADA
        subaccion_pausada = db.query(OfertaSubaccionCatalogo).filter(
            OfertaSubaccionCatalogo.accion_id == accion_pausada.id,
            OfertaSubaccionCatalogo.nombre_subaccion == "EN TRAMITE"
        ).first()
        
        if subaccion_pausada:
            logger.info(f"   ⚠️  Subacción 'EN TRAMITE' ya existe: ID {subaccion_pausada.id}")
        else:
            subaccion_pausada = OfertaSubaccionCatalogo(
                accion_id=accion_pausada.id,
                nombre_subaccion="EN TRAMITE",
                is_active=True,
                orden=1
            )
            db.add(subaccion_pausada)
            db.commit()
            db.refresh(subaccion_pausada)
            logger.info(f"   ✅ Subacción 'EN TRAMITE' creada: ID {subaccion_pausada.id}")
        
        # ==========================================
        # PASO 3: Crear acción MALO
        # ==========================================
        logger.info("\n📝 PASO 3: Creando acción MALO...")
        
        accion_malo = db.query(OfertaAccionCatalogo).filter(
            OfertaAccionCatalogo.nombre_accion == "MALO"
        ).first()
        
        if accion_malo:
            logger.info(f"   ⚠️  Acción 'MALO' ya existe: ID {accion_malo.id}")
        else:
            accion_malo = OfertaAccionCatalogo(
                nombre_accion="MALO",
                descripcion="Oferta con datos incorrectos o inválidos. Se cierra automáticamente.",
                is_active=True,
                orden=101
            )
            db.add(accion_malo)
            db.commit()
            db.refresh(accion_malo)
            logger.info(f"   ✅ Acción 'MALO' creada: ID {accion_malo.id}")
        
        # Crear subacción para MALO
        subaccion_malo = db.query(OfertaSubaccionCatalogo).filter(
            OfertaSubaccionCatalogo.accion_id == accion_malo.id,
            OfertaSubaccionCatalogo.nombre_subaccion == "MALO"
        ).first()
        
        if subaccion_malo:
            logger.info(f"   ⚠️  Subacción 'MALO' ya existe: ID {subaccion_malo.id}")
        else:
            subaccion_malo = OfertaSubaccionCatalogo(
                accion_id=accion_malo.id,
                nombre_subaccion="MALO",
                is_active=True,
                orden=1
            )
            db.add(subaccion_malo)
            db.commit()
            db.refresh(subaccion_malo)
            logger.info(f"   ✅ Subacción 'MALO' creada: ID {subaccion_malo.id}")
        
        # ==========================================
        # PASO 4: Crear acción RFS
        # ==========================================
        logger.info("\n📝 PASO 4: Creando acción RFS...")
        
        accion_rfs = db.query(OfertaAccionCatalogo).filter(
            OfertaAccionCatalogo.nombre_accion == "RFS"
        ).first()
        
        if accion_rfs:
            logger.info(f"   ⚠️  Acción 'RFS' ya existe: ID {accion_rfs.id}")
        else:
            accion_rfs = OfertaAccionCatalogo(
                nombre_accion="RFS",
                descripcion="Ready For Service - Oferta completada y lista. Se cierra automáticamente.",
                is_active=True,
                orden=102
            )
            db.add(accion_rfs)
            db.commit()
            db.refresh(accion_rfs)
            logger.info(f"   ✅ Acción 'RFS' creada: ID {accion_rfs.id}")
        
        # Crear subacción para RFS
        subaccion_rfs = db.query(OfertaSubaccionCatalogo).filter(
            OfertaSubaccionCatalogo.accion_id == accion_rfs.id,
            OfertaSubaccionCatalogo.nombre_subaccion == "RFS"
        ).first()
        
        if subaccion_rfs:
            logger.info(f"   ⚠️  Subacción 'RFS' ya existe: ID {subaccion_rfs.id}")
        else:
            subaccion_rfs = OfertaSubaccionCatalogo(
                accion_id=accion_rfs.id,
                nombre_subaccion="RFS",
                is_active=True,
                orden=1
            )
            db.add(subaccion_rfs)
            db.commit()
            db.refresh(subaccion_rfs)
            logger.info(f"   ✅ Subacción 'RFS' creada: ID {subaccion_rfs.id}")
        
        # ==========================================
        # RESUMEN FINAL
        # ==========================================
        logger.info("\n" + "="*80)
        logger.info("✅ MIGRACIÓN COMPLETADA EXITOSAMENTE")
        logger.info("="*80)
        logger.info("\n📊 RESUMEN DE CAMBIOS:")
        logger.info(f"   ✓ Tabla 'oferta_configuracion_pausada' creada/verificada")
        logger.info(f"   ✓ Tabla 'oferta_pausada_tracking' creada/verificada")
        logger.info(f"   ✓ Acción 'OFERTA PAUSADA' → Subacción 'EN TRAMITE'")
        logger.info(f"   ✓ Acción 'MALO' → Subacción 'MALO'")
        logger.info(f"   ✓ Acción 'RFS' → Subacción 'RFS'")
        
        logger.info("\n📝 PRÓXIMOS PASOS:")
        logger.info("   1. Los asesores pueden usar 'OFERTA PAUSADA' después de 7 minutos de trabajo")
        logger.info("   2. Máximo 3 ofertas pausadas simultáneamente por asesor")
        logger.info("   3. 'MALO' y 'RFS' cierran ofertas automáticamente")
        logger.info("   4. Supervisores/SuperUsers pueden liberar ofertas en estos estados")
        logger.info("   5. Las cargas automáticas omitirán ofertas en estos conceptos especiales")
        
        logger.info("\n" + "="*80)
        
        return True
        
    except Exception as e:
        logger.error(f"\n❌ ERROR EN MIGRACIÓN: {e}", exc_info=True)
        db.rollback()
        return False
        
    finally:
        db.close()


if __name__ == "__main__":
    """
    Ejecutar directamente este script para aplicar la migración:
    
    python -m app.migrations.add_pausada_malo_rfs_features
    """
    import sys
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    success = run_migration()
    sys.exit(0 if success else 1)
