#!/usr/bin/env python3
"""
Script de migración para carga de gestiones históricas desde CSV.

Carga datos históricos de gestiones canceladas en:
- enlistment_manager (ofertas con estado CERRADO)
- enlistment_manager_history (histórico de cambios)
- oferta_gestion_detalle (detalle de gestiones)
- oferta_historico_estados (auditoría de estados)

Uso:
    # Validación sin cambios (DRY-RUN)
    python -m app.migrations.load_historical_gestiones --dry-run
    
    # Ejecución real
    python -m app.migrations.load_historical_gestiones
    
    # Con path personalizado
    python -m app.migrations.load_historical_gestiones --csv-path /path/to/file.csv

Autor: Sistema de Gestión de Ofertas
Fecha: 2026-03-19
"""

import sys
import argparse
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import pandas as pd
import uuid
import pytz
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

# Configurar path para imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.db.postgres import SessionLocalPG
from app.models.user_model import UserModel
from app.models.oferta_gestion_model import (
    OfertaAccionCatalogo,
    OfertaSubaccionCatalogo,
    OfertaGestionDetalle,
    OfertaHistoricoEstados
)
from app.models.enlistment_manager_model import (
    EnlistmentManager,
    EnlistmentManagerHistory,
    TipoOperacion
)
from app.utils.hash_utils import generate_record_hash


# ==========================================
# CONFIGURACIÓN DE LOGGING CON ZONA HORARIA BOGOTÁ
# ==========================================

class BogotaFormatter(logging.Formatter):
    """Formatter que usa zona horaria America/Bogota (UTC-5)"""
    
    def formatTime(self, record, datefmt=None):
        """Override para usar America/Bogota en vez de UTC"""
        bogota_tz = pytz.timezone('America/Bogota')
        ct = datetime.fromtimestamp(record.created, bogota_tz)
        if datefmt:
            s = ct.strftime(datefmt)
        else:
            s = ct.strftime("%Y-%m-%d %H:%M:%S")
        return s


# Configurar logging con formateador personalizado
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Formato del log
formatter = BogotaFormatter('%(asctime)s - %(levelname)s - %(message)s')

# Handler para consola
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Handler para archivo
file_handler = logging.FileHandler(f'load_historical_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# ==========================================
# CONFIGURACIÓN
# ==========================================
DEFAULT_CSV_PATH = "/workspaces/project_gestor_v2/Datacanceladosoferta.csv"
BATCH_SIZE = 100
ACCION_NOMBRE = "Cancelado"
TICKET_PREFIX = "HISTORICAL_LOAD"


# ==========================================
# FUNCIONES AUXILIARES
# ==========================================

def get_bogota_time() -> datetime:
    """
    Retorna la fecha/hora actual en zona horaria America/Bogota (UTC-5).
    Sin timezone info (naive datetime).
    """
    bogota_tz = pytz.timezone('America/Bogota')
    utc_now = datetime.now(pytz.UTC)
    bogota_now = utc_now.astimezone(bogota_tz)
    # Retornar sin timezone info para compatibilidad con BD
    return bogota_now.replace(tzinfo=None)


def print_separator(char="=", length=60):
    """Imprime un separador visual"""
    print(char * length)


def print_header(title: str):
    """Imprime un encabezado destacado"""
    print_separator()
    print(f"  {title}")
    print_separator()
    print()


def load_csv(csv_path: str) -> Tuple[pd.DataFrame, Optional[str]]:
    """
    Carga y valida el CSV de gestiones históricas.
    
    Returns:
        Tuple[DataFrame, error_message]
    """
    try:
        logger.info(f"📁 Cargando CSV: {csv_path}")
        
        # Intentar detectar encoding
        encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
        df = None
        
        for encoding in encodings:
            try:
                df = pd.read_csv(csv_path, sep=';', encoding=encoding)
                logger.info(f"✅ CSV cargado con encoding: {encoding}")
                break
            except UnicodeDecodeError:
                continue
        
        if df is None:
            return None, "No se pudo leer el CSV con ningún encoding soportado"
        
        # Validar columnas requeridas
        required_columns = [
            'Oferta', 'Accion', 'Sub Accion', 'Observaciones',
            'Login usuario', 'fecha_fin', 'DIRECCION'
        ]
        
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            return None, f"Columnas faltantes en CSV: {missing_columns}"
        
        # Limpiar datos
        df = df.dropna(subset=['Oferta', 'Login usuario', 'fecha_fin'])
        
        # Normalizar nombres de columnas
        df = df.rename(columns={
            'Oferta': 'oferta',
            'Accion': 'accion',
            'Sub Accion': 'subaccion',
            'Observaciones': 'observaciones',
            'Login usuario': 'login_usuario',
            'fecha_fin': 'fecha_fin',
            'DIRECCION': 'direccion'
        })
        
        # Convertir fecha_fin a datetime
        df['fecha_fin'] = pd.to_datetime(df['fecha_fin'], errors='coerce')
        registros_con_fecha_invalida = df['fecha_fin'].isna().sum()
        
        if registros_con_fecha_invalida > 0:
            logger.warning(f"⚠️  {registros_con_fecha_invalida} registros con fecha inválida (serán omitidos)")
            df = df.dropna(subset=['fecha_fin'])
        
        # Limpiar espacios en blanco
        df['oferta'] = df['oferta'].str.strip()
        df['login_usuario'] = df['login_usuario'].str.strip()
        df['accion'] = df['accion'].str.strip()
        df['subaccion'] = df['subaccion'].str.strip()
        
        # Rellenar observaciones vacías con string vacío
        df['observaciones'] = df['observaciones'].fillna('')
        
        logger.info(f"✅ CSV validado correctamente")
        logger.info(f"   Total registros válidos: {len(df)}")
        
        return df, None
        
    except FileNotFoundError:
        return None, f"Archivo no encontrado: {csv_path}"
    except Exception as e:
        return None, f"Error al cargar CSV: {str(e)}"


def prepare_catalogos(db_session, df: pd.DataFrame, dry_run: bool = False) -> Tuple[Dict[str, uuid.UUID], Optional[str]]:
    """
    Prepara catálogos de acciones y subacciones.
    
    Returns:
        Tuple[Dict[nombre_subaccion: uuid], error_message]
    """
    try:
        logger.info("📋 Preparando catálogos de Acción/Subacción...")
        
        # Buscar o crear acción "Cancelado"
        accion = db_session.query(OfertaAccionCatalogo).filter(
            OfertaAccionCatalogo.nombre_accion == ACCION_NOMBRE
        ).first()
        
        if not accion:
            if dry_run:
                logger.info(f"   [DRY-RUN] Se crearía acción: '{ACCION_NOMBRE}'")
                accion_id = uuid.uuid4()  # ID temporal para dry-run
            else:
                accion = OfertaAccionCatalogo(
                    nombre_accion=ACCION_NOMBRE,
                    descripcion="Oferta cancelada por gestión",
                    orden=100
                )
                db_session.add(accion)
                db_session.commit()
                db_session.refresh(accion)
                accion_id = accion.id
                logger.info(f"   ✅ Acción creada: '{ACCION_NOMBRE}'")
        else:
            accion_id = accion.id
            logger.info(f"   ✅ Acción encontrada: '{ACCION_NOMBRE}'")
        
        # Obtener subacciones únicas del CSV
        subacciones_unicas = df['subaccion'].unique()
        logger.info(f"   Subacciones únicas en CSV: {len(subacciones_unicas)}")
        
        subacciones_map = {}
        
        for idx, nombre_subaccion in enumerate(subacciones_unicas):
            # Buscar si existe
            subaccion = db_session.query(OfertaSubaccionCatalogo).filter(
                OfertaSubaccionCatalogo.accion_id == accion_id,
                OfertaSubaccionCatalogo.nombre_subaccion == nombre_subaccion
            ).first()
            
            if not subaccion:
                if dry_run:
                    logger.info(f"   [DRY-RUN] Se crearía subacción: '{nombre_subaccion}'")
                    subacciones_map[nombre_subaccion] = uuid.uuid4()
                else:
                    subaccion = OfertaSubaccionCatalogo(
                        accion_id=accion_id,
                        nombre_subaccion=nombre_subaccion,
                        orden=idx
                    )
                    db_session.add(subaccion)
                    db_session.flush()
                    subacciones_map[nombre_subaccion] = subaccion.id
                    logger.info(f"   ✅ Subacción creada: '{nombre_subaccion}'")
            else:
                subacciones_map[nombre_subaccion] = subaccion.id
                logger.info(f"   ✅ Subacción encontrada: '{nombre_subaccion}'")
        
        if not dry_run:
            db_session.commit()
        
        logger.info(f"✅ Catálogos preparados: {len(subacciones_map)} subacciones")
        
        return {
            'accion_id': accion_id,
            'subacciones': subacciones_map
        }, None
        
    except Exception as e:
        if not dry_run:
            db_session.rollback()
        logger.error(f"❌ Error al preparar catálogos: {e}")
        return None, str(e)


def prepare_users(db_session, df: pd.DataFrame, dry_run: bool = False) -> Tuple[Dict[str, Dict], Optional[str]]:
    """
    Prepara usuarios: busca existentes y crea los faltantes.
    
    Returns:
        Tuple[Dict[login: user_data], error_message]
    """
    try:
        logger.info("👥 Preparando usuarios...")
        
        # Obtener logins únicos
        logins_unicos = df['login_usuario'].unique()
        logger.info(f"   Total usuarios únicos en CSV: {len(logins_unicos)}")
        
        # Buscar usuarios existentes
        usuarios_existentes = db_session.query(UserModel).filter(
            UserModel.login.in_(logins_unicos.tolist())
        ).all()
        
        usuarios_map = {}
        
        for user in usuarios_existentes:
            usuarios_map[user.login] = {
                'id': user.id,
                'login': user.login,
                'full_name': user.full_name or user.login,
                'profile_id': user.profile_id or 4
            }
        
        logger.info(f"   Usuarios existentes en BD: {len(usuarios_map)}")
        
        # Identificar usuarios faltantes
        logins_existentes = set(usuarios_map.keys())
        logins_faltantes = [login for login in logins_unicos if login not in logins_existentes]
        
        if logins_faltantes:
            logger.info(f"   Usuarios a crear: {len(logins_faltantes)}")
            
            for login in logins_faltantes:
                if dry_run:
                    logger.info(f"   [DRY-RUN] Se crearía usuario: {login}")
                    usuarios_map[login] = {
                        'id': uuid.uuid4(),
                        'login': login,
                        'full_name': login,
                        'profile_id': 4
                    }
                else:
                    nuevo_usuario = UserModel(
                        id=uuid.uuid4(),
                        login=login,
                        full_name=login,
                        profile_id=4,
                        user_state=True,
                        create_at=get_bogota_time()
                    )
                    db_session.add(nuevo_usuario)
                    db_session.flush()
                    
                    usuarios_map[login] = {
                        'id': nuevo_usuario.id,
                        'login': nuevo_usuario.login,
                        'full_name': nuevo_usuario.full_name,
                        'profile_id': nuevo_usuario.profile_id
                    }
                    logger.info(f"   ✅ Usuario creado: {login}")
            
            if not dry_run:
                db_session.commit()
        else:
            logger.info(f"   ✅ Todos los usuarios ya existen en BD")
        
        logger.info(f"✅ Usuarios preparados: {len(usuarios_map)}")
        return usuarios_map, None
        
    except Exception as e:
        if not dry_run:
            db_session.rollback()
        logger.error(f"❌ Error al preparar usuarios: {e}")
        return None, str(e)


def build_campos_dinamicos(row: pd.Series) -> Dict[str, Any]:
    """
    Construye el diccionario de campos dinámicos JSONB.
    Solo incluye datos del CSV y nulls explícitos para campos del proceso normal.
    Limpia valores NaN/None para evitar errores de JSON.
    """
    # Función auxiliar para limpiar valores NaN
    def clean_value(value):
        if pd.isna(value):
            return None
        return value
    
    return {
        # Campos del CSV (limpiar NaN)
        'oferta': clean_value(row['oferta']),
        'direccion': clean_value(row['direccion']),
        'garantia': False,
        
        # Campos del proceso normal que no están en CSV = null
        'concepto': None,
        'concepto_original': None,
        'concepto_id': None,
        'tecnologia': None,
        'producto': None,
        'uen': None,
        'responsable': None,
        'fecha_creado': None,
        'fecha_estado': None,
        'fecha_pendiente': None,
        'estado_direccion': None,
        'flag_hfc': None,
        'flag_gpon': None,
        'flag_tercero': None,
        'validacion_anulacion': None,
        'pedido_crm': None,
        'cliente': None,
        'tipo_cliente': None
    }


def check_gestion_exists(db_session, oferta: str, usuario_login: str, fecha_gestion: datetime) -> bool:
    """Verifica si ya existe una gestión para esta oferta/usuario/fecha (idempotencia)"""
    try:
        count = db_session.query(OfertaGestionDetalle).filter(
            OfertaGestionDetalle.oferta == oferta,
            OfertaGestionDetalle.usuario_login == usuario_login,
            func.date(OfertaGestionDetalle.fecha_gestion) == fecha_gestion.date()
        ).count()
        return count > 0
    except Exception:
        return False


def process_batch(
    db_session,
    batch_df: pd.DataFrame,
    catalogos: Dict,
    usuarios_map: Dict,
    ticket_carga: str,
    dry_run: bool = False
) -> Dict[str, int]:
    """
    Procesa un lote de registros del CSV.
    
    Returns:
        Dict con estadísticas del procesamiento
    """
    stats = {
        'ofertas_nuevas': 0,
        'ofertas_actualizadas': 0,
        'ofertas_ya_cerradas': 0,
        'gestiones_creadas': 0,
        'gestiones_duplicadas': 0,
        'historicos_creados': 0,
        'errores': 0
    }
    
    accion_id = catalogos['accion_id']
    subacciones_map = catalogos['subacciones']
    
    for idx, row in batch_df.iterrows():
        try:
            oferta = row['oferta']
            login_usuario = row['login_usuario']
            subaccion_nombre = row['subaccion']
            observacion = row['observaciones']
            fecha_gestion = row['fecha_fin']
            
            # Obtener IDs
            subaccion_id = subacciones_map.get(subaccion_nombre)
            user_data = usuarios_map.get(login_usuario)
            
            if not subaccion_id or not user_data:
                logger.warning(f"   ⚠️  Oferta {oferta}: datos incompletos (skip)")
                stats['errores'] += 1
                continue
            
            # Verificar si oferta existe
            oferta_existente = db_session.query(EnlistmentManager).filter(
                EnlistmentManager.oferta == oferta
            ).first()
            
            # Construir campos dinámicos
            campos_dinamicos = build_campos_dinamicos(row)
            hash_registro = generate_record_hash(campos_dinamicos)
            
            estado_anterior = None
            oferta_id = None
            
            if not oferta_existente:
                # CASO 1: Oferta nueva - INSERT
                if not dry_run:
                    nuevo_id = uuid.uuid4()
                    nueva_oferta = EnlistmentManager(
                        id=nuevo_id,
                        ticket_carga=ticket_carga,
                        oferta=oferta,
                        hash_registro=hash_registro,
                        campos_dinamicos=campos_dinamicos,
                        estado_oferta='CERRADO',
                        contador_cargas_ausente=0,
                        usuario_asignado_login=user_data['login'],
                        usuario_asignado_nombre=user_data['full_name'],
                        usuario_asignado_profile_id=user_data['profile_id'],
                        fecha_asignacion=fecha_gestion,
                        fecha_gestion=fecha_gestion
                    )
                    db_session.add(nueva_oferta)
                    db_session.flush()
                    
                    # Agregar a histórico
                    history = EnlistmentManagerHistory(
                        fk_enlistment_manager_id=nuevo_id,
                        ticket_carga=ticket_carga,
                        create_date_automation=get_bogota_time(),
                        oferta=oferta,
                        hash_registro=hash_registro,
                        tipo_operacion=TipoOperacion.INSERT,
                        campos_dinamicos=campos_dinamicos,
                        campos_modificados=None,
                        estado_oferta='CERRADO'
                    )
                    db_session.add(history)
                    
                    oferta_id = nuevo_id
                    estado_anterior = 'ABIERTO'  # Asumimos que era abierta
                    stats['historicos_creados'] += 1
                
                stats['ofertas_nuevas'] += 1
                logger.debug(f"   [NEW] {oferta}")
                
            elif oferta_existente.estado_oferta == 'CERRADO':
                # CASO 2: Ya está cerrada - Solo registrar gestión
                oferta_id = oferta_existente.id
                estado_anterior = 'CERRADO'
                stats['ofertas_ya_cerradas'] += 1
                logger.debug(f"   [SKIP UPDATE] {oferta} (ya CERRADO)")
                
            else:
                # CASO 3: Actualizar a CERRADO (estaba ABIERTO, EN_TRAMITE, CERRADO_AUTOMATICO)
                if not dry_run:
                    estado_anterior = oferta_existente.estado_oferta
                    
                    oferta_existente.estado_oferta = 'CERRADO'
                    oferta_existente.usuario_asignado_login = user_data['login']
                    oferta_existente.usuario_asignado_nombre = user_data['full_name']
                    oferta_existente.usuario_asignado_profile_id = user_data['profile_id']
                    oferta_existente.fecha_asignacion = fecha_gestion
                    oferta_existente.fecha_gestion = fecha_gestion
                    oferta_existente.hash_registro = hash_registro
                    oferta_existente.campos_dinamicos = campos_dinamicos
                    oferta_existente.ticket_carga = ticket_carga
                    
                    db_session.flush()
                    
                    # Agregar a histórico
                    history = EnlistmentManagerHistory(
                        fk_enlistment_manager_id=oferta_existente.id,
                        ticket_carga=ticket_carga,
                        create_date_automation=get_bogota_time(),
                        oferta=oferta,
                        hash_registro=hash_registro,
                        tipo_operacion=TipoOperacion.UPDATE,
                        campos_dinamicos=campos_dinamicos,
                        campos_modificados={
                            'estado_oferta': {'old': estado_anterior, 'new': 'CERRADO'}
                        },
                        estado_oferta='CERRADO'
                    )
                    db_session.add(history)
                    
                    oferta_id = oferta_existente.id
                    stats['historicos_creados'] += 1
                else:
                    estado_anterior = oferta_existente.estado_oferta
                    oferta_id = oferta_existente.id
                
                stats['ofertas_actualizadas'] += 1
                logger.debug(f"   [UPDATE] {oferta}: {estado_anterior} → CERRADO")
            
            # Verificar idempotencia de gestión
            if not dry_run and check_gestion_exists(db_session, oferta, login_usuario, fecha_gestion):
                logger.debug(f"   [SKIP GESTION] {oferta} (ya existe)")
                stats['gestiones_duplicadas'] += 1
                continue
            
            # Crear detalle de gestión
            if not dry_run:
                gestion_detalle = OfertaGestionDetalle(
                    oferta=oferta,
                    accion_id=accion_id,
                    subaccion_id=subaccion_id,
                    observacion=observacion if observacion else None,
                    usuario_login=user_data['login'],
                    usuario_nombre=user_data['full_name'],
                    usuario_profile_id=user_data['profile_id'],
                    fecha_gestion=fecha_gestion
                )
                db_session.add(gestion_detalle)
            
            stats['gestiones_creadas'] += 1
            
            # Crear histórico de estados
            if not dry_run and estado_anterior:
                historico_estado = OfertaHistoricoEstados(
                    oferta=oferta,
                    accion_sistema='GESTIONAR',
                    estado_anterior=estado_anterior,
                    estado_nuevo='CERRADO',
                    usuario_login=user_data['login'],
                    usuario_nombre=user_data['full_name'],
                    usuario_profile_id=user_data['profile_id'],
                    motivo=f"Carga histórica: {subaccion_nombre}",
                    fecha_accion=fecha_gestion
                )
                db_session.add(historico_estado)
            
        except Exception as e:
            logger.error(f"   ❌ Error procesando oferta {row.get('oferta', 'Unknown')}: {e}")
            stats['errores'] += 1
            continue
    
    # Commit del lote
    if not dry_run:
        try:
            db_session.commit()
        except Exception as e:
            db_session.rollback()
            logger.error(f"❌ Error al hacer commit del lote: {e}")
            # Incrementar contador de errores para reflejar que todo el lote falló
            stats['errores'] = len(batch_df)
            raise
    
    return stats


def print_statistics(stats: Dict[str, int], total_registros: int, tiempo_segundos: float):
    """Imprime estadísticas finales del procesamiento"""
    print()
    print_header("ESTADÍSTICAS FINALES")
    
    print(f"📊 Registros procesados: {total_registros}")
    print()
    print(f"   Ofertas:")
    print(f"   ├─ Nuevas insertadas:       {stats['ofertas_nuevas']}")
    print(f"   ├─ Actualizadas a CERRADO:  {stats['ofertas_actualizadas']}")
    print(f"   └─ Ya cerradas (skip):      {stats['ofertas_ya_cerradas']}")
    print()
    print(f"   Gestiones:")
    print(f"   ├─ Creadas:                 {stats['gestiones_creadas']}")
    print(f"   └─ Duplicadas (skip):       {stats['gestiones_duplicadas']}")
    print()
    print(f"   Históricos:")
    print(f"   └─ Registros creados:       {stats['historicos_creados']}")
    print()
    
    if stats['errores'] > 0:
        print(f"   ❌ Errores: {stats['errores']}")
        print()
    
    print(f"⏱️  Tiempo total: {tiempo_segundos:.2f} segundos")
    print()


# ==========================================
# FUNCIÓN PRINCIPAL
# ==========================================

def main():
    """Función principal de ejecución"""
    
    # Parsear argumentos
    parser = argparse.ArgumentParser(
        description='Carga de gestiones históricas desde CSV'
    )
    parser.add_argument(
        '--csv-path',
        type=str,
        default=DEFAULT_CSV_PATH,
        help=f'Path al archivo CSV (default: {DEFAULT_CSV_PATH})'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Ejecutar en modo validación sin hacer cambios en BD'
    )
    
    args = parser.parse_args()
    
    # Header inicial
    print()
    if args.dry_run:
        print_header("MODO DRY-RUN - VALIDACIÓN DE CARGA HISTÓRICA")
    else:
        print_header("CARGA HISTÓRICA DE GESTIONES CANCELADAS")
    
    print(f"📁 Archivo: {args.csv_path}")
    print(f"📅 Fecha: {get_bogota_time().strftime('%Y-%m-%d %H:%M:%S')} (America/Bogota UTC-5)")
    
    if args.dry_run:
        print(f"⚠️  MODO: DRY-RUN (sin cambios en BD)")
    
    print()
    
    inicio = get_bogota_time()
    
    # Generar ticket de carga
    ticket_carga = f"{TICKET_PREFIX}_{get_bogota_time().strftime('%Y%m%d_%H%M%S')}"
    if not args.dry_run:
        print(f"🎫 Ticket: {ticket_carga}")
        print()
    
    # Fase 1: Cargar CSV
    print_separator("-")
    print("📋 FASE 1: Cargando y validando CSV...")
    print_separator("-")
    print()
    
    df, error = load_csv(args.csv_path)
    if error:
        logger.error(f"❌ {error}")
        return 1
    
    print(f"✅ Total registros válidos: {len(df)}")
    print()
    
    # Crear sesión de BD
    db_session = SessionLocalPG()
    
    try:
        # Fase 2: Preparar catálogos
        print_separator("-")
        print("📋 FASE 2: Preparando catálogos de Acción/Subacción...")
        print_separator("-")
        print()
        
        catalogos, error = prepare_catalogos(db_session, df, args.dry_run)
        if error:
            logger.error(f"❌ {error}")
            return 1
        
        print()
        
        # Fase 3: Preparar usuarios
        print_separator("-")
        print("👥 FASE 3: Preparando usuarios...")
        print_separator("-")
        print()
        
        usuarios_map, error = prepare_users(db_session, df, args.dry_run)
        if error:
            logger.error(f"❌ {error}")
            return 1
        
        print()
        
        if args.dry_run:
            # En dry-run, mostrar resumen y salir
            print_separator("-")
            print("📊 RESUMEN DRY-RUN")
            print_separator("-")
            print()
            print(f"   ✅ CSV válido con {len(df)} registros")
            print(f"   ✅ Catálogos validados")
            print(f"   ✅ {len(usuarios_map)} usuarios preparados")
            print()
            print(f"   ⏱️  Tiempo estimado de ejecución real: 1-2 minutos")
            print()
            print_separator()
            print("✅ Validación completada. Ejecute sin --dry-run para aplicar cambios")
            print_separator()
            return 0
        
        # Fase 4: Procesamiento por lotes
        print_separator("-")
        print(f"📦 FASE 4: Procesando registros (lotes de {BATCH_SIZE})...")
        print_separator("-")
        print()
        
        total_batches = (len(df) // BATCH_SIZE) + (1 if len(df) % BATCH_SIZE > 0 else 0)
        
        stats_totales = {
            'ofertas_nuevas': 0,
            'ofertas_actualizadas': 0,
            'ofertas_ya_cerradas': 0,
            'gestiones_creadas': 0,
            'gestiones_duplicadas': 0,
            'historicos_creados': 0,
            'errores': 0
        }
        
        for batch_num in range(total_batches):
            start_idx = batch_num * BATCH_SIZE
            end_idx = min((batch_num + 1) * BATCH_SIZE, len(df))
            batch_df = df.iloc[start_idx:end_idx]
            
            logger.info(f"📦 Procesando lote {batch_num + 1}/{total_batches} ({len(batch_df)} registros)...")
            
            try:
                batch_stats = process_batch(
                    db_session,
                    batch_df,
                    catalogos,
                    usuarios_map,
                    ticket_carga,
                    dry_run=False
                )
                
                # Acumular estadísticas
                for key in stats_totales:
                    stats_totales[key] += batch_stats[key]
                
                logger.info(f"   ✅ Lote completado: +{batch_stats['ofertas_nuevas']} nuevas, +{batch_stats['ofertas_actualizadas']} actualizadas")
                
            except Exception as e:
                logger.error(f"   ❌ Lote {batch_num + 1} falló completamente: {e}")
                stats_totales['errores'] += len(batch_df)
                # Resetear la sesión para continuar con el siguiente lote
                db_session.rollback()
                continue
        
        # Estadísticas finales
        fin = get_bogota_time()
        tiempo_segundos = (fin - inicio).total_seconds()
        
        print_statistics(stats_totales, len(df), tiempo_segundos)
        
        print_separator()
        print("✅ CARGA COMPLETADA EXITOSAMENTE")
        print_separator()
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Error fatal en ejecución: {e}", exc_info=True)
        db_session.rollback()
        return 1
    
    finally:
        db_session.close()


if __name__ == "__main__":
    sys.exit(main())
