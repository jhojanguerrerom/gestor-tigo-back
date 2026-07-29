import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
import time
import uuid
from app.db.timezone_types import get_bogota_now
from app.repositories.enlistment_repository import EnlistmentRepository
from app.models.enlistment_manager_model import EstadoCarga, TipoOperacion
from app.utils.hash_utils import (
    generate_record_hash, 
    compare_records, 
    generate_ticket_carga,
    prepare_for_json
)
from app.core.constants import CONCEPTOS_ANULACION

logger = logging.getLogger("enlistment_service")


class EnlistmentService:
    """
    Servicio para gestión de Enlistment Manager.
    Implementa la lógica de detección de cambios (delta detection) y carga masiva.
    """

    def __init__(self, db: Session):
        """Inicializa el service con la sesión de base de datos.
        
        Args:
            db: Sesión de SQLAlchemy inyectada por dependency
        """
        self.db = db
        self.repository = EnlistmentRepository(db)

    # ==========================================
    # FUNCIONES HELPER
    # ==========================================

    def _get_usuario_fields_for_estado(self, estado_oferta: str, registro_existente=None) -> Dict[str, Any]:
        """
        Retorna los valores de campos de usuario basados en el estado de la oferta.
        
        Args:
            estado_oferta: Estado de la oferta (ABIERTO, CERRADO_AUTOMATICO, etc.)
            registro_existente: Registro existente (para preservar valores en estados no automáticos)
            
        Returns:
            Dict con los campos de usuario a setear
        """
        if estado_oferta == 'CERRADO_AUTOMATICO':
            # Limpiar todos los campos de usuario para cierres automáticos
            return {
                "usuario_asignado_login": None,
                "usuario_asignado_nombre": None,
                "usuario_asignado_profile_id": None,
                "fecha_asignacion": None,
                "fecha_gestion": None
            }
        else:
            # Preservar valores existentes o dejar en None si es nuevo
            if registro_existente:
                return {
                    "usuario_asignado_login": registro_existente.usuario_asignado_login,
                    "usuario_asignado_nombre": registro_existente.usuario_asignado_nombre,
                    "usuario_asignado_profile_id": registro_existente.usuario_asignado_profile_id,
                    "fecha_asignacion": registro_existente.fecha_asignacion,
                    "fecha_gestion": registro_existente.fecha_gestion
                }
            else:
                # Registro nuevo, dejar en None
                return {
                    "usuario_asignado_login": None,
                    "usuario_asignado_nombre": None,
                    "usuario_asignado_profile_id": None,
                    "fecha_asignacion": None,
                    "fecha_gestion": None
                }

    # ==========================================
    # PROCESAMIENTO Y CARGA DE DATOS
    # ==========================================

    async def process_and_store(
        self, 
        data_merged: List[Dict[str, Any]], 
        columnas: List[str]
    ) -> Dict[str, Any]:
        """
        Procesa el DataFrame fusionado y almacena los datos con detección de cambios.
        Este es el método principal que se llama desde automation_service.
        
        Args:
            data_merged: Lista de diccionarios del DataFrame fusionado
            columnas: Lista de nombres de columnas del DataFrame
            
        Returns:
            Dict con estadísticas de la carga
        """
        start_time = time.time()
        ticket_carga = generate_ticket_carga()
        create_date_automation = get_bogota_now() #datetime.now().astimezone()
        
        logger.info(f"🚀 Iniciando carga con ticket: {ticket_carga}")
        logger.info(f"📊 Total de registros a procesar: {len(data_merged)}")
        
        try:
            # Crear registro de control inicial
            control_data = {
                "ticket_carga": ticket_carga,
                "create_date_automation": create_date_automation,
                "total_registros_procesados": len(data_merged),
                "total_registros_nuevos": 0,
                "total_registros_actualizados": 0,
                "total_registros_sin_cambios": 0,
                "estado": EstadoCarga.EN_PROCESO,
                "columnas_detectadas": columnas
            }
            control = self.repository.create_control_record(control_data)
            logger.info(f"✅ Registro de control creado: {control.id}")
            
            # Validar que haya datos
            if not data_merged or len(data_merged) == 0:
                logger.warning("⚠️ No hay datos para procesar")
                self.repository.update_control_record(ticket_carga, {
                    "estado": EstadoCarga.COMPLETADO,
                    "tiempo_ejecucion_segundos": time.time() - start_time
                })
                return {
                    "ticket_carga": ticket_carga,
                    "total_procesados": 0,
                    "nuevos": 0,
                    "modificados": 0,
                    "sin_cambios": 0,
                    "tiempo_ejecucion": 0
                }
            
            # Validar campo clave 'oferta'
            if 'oferta' not in columnas:
                raise ValueError("El campo 'oferta' es obligatorio en el DataFrame")
            
            # Procesar registros con delta detection
            resultado = await self._process_delta_detection(
                data_merged, 
                ticket_carga, 
                create_date_automation
            )
            
            # Calcular tiempo de ejecución
            tiempo_ejecucion = time.time() - start_time
            
            # Actualizar control con resultados finales
            self.repository.update_control_record(ticket_carga, {
                "total_registros_nuevos": resultado['nuevos'],
                "total_registros_actualizados": resultado['modificados'],
                "total_registros_sin_cambios": resultado['sin_cambios'],
                "estado": EstadoCarga.COMPLETADO,
                "tiempo_ejecucion_segundos": tiempo_ejecucion
            })
            
            logger.info(f"✅ Carga completada exitosamente en {tiempo_ejecucion:.2f}s")
            logger.info(f"📈 Nuevos: {resultado['nuevos']} | Modificados: {resultado['modificados']} | Sin cambios: {resultado['sin_cambios']}")
            
            return {
                "ticket_carga": ticket_carga,
                "total_procesados": len(data_merged),
                "nuevos": resultado['nuevos'],
                "modificados": resultado['modificados'],
                "sin_cambios": resultado['sin_cambios'],
                "tiempo_ejecucion": tiempo_ejecucion
            }
            
        except Exception as e:
            logger.error(f"❌ Error en process_and_store: {e}", exc_info=True)
            
            # Actualizar control con error
            try:
                self.repository.update_control_record(ticket_carga, {
                    "estado": EstadoCarga.ERROR,
                    "mensaje_error": str(e),
                    "tiempo_ejecucion_segundos": time.time() - start_time
                })
            except:
                pass
            
            raise

    async def _process_delta_detection(
        self, 
        data_merged: List[Dict[str, Any]], 
        ticket_carga: str,
        create_date_automation: datetime
    ) -> Dict[str, int]:
        """
        Implementa el algoritmo de detección de cambios.
        Compara cada registro con la BD y determina si es INSERT, UPDATE o sin cambios.
        Incluye gestión de cierre automático de ofertas ausentes.
        
        Args:
            data_merged: Datos a procesar
            ticket_carga: Ticket de la carga
            create_date_automation: Fecha de la carga
            
        Returns:
            Dict con contadores: nuevos, modificados, sin_cambios
        """
        from app.core.config import settings
        
        logger.info("🔍 Iniciando delta detection...")
        
        # Obtener el umbral de cargas desde la configuración
        umbral_cargas = settings.ENLISTMENT_CARGAS_INACTIVIDAD
        logger.info(f"🔍 Umbral de cargas para cierre automático: {umbral_cargas}")
        
        # Contadores
        contador_nuevos = 0
        contador_modificados = 0
        contador_sin_cambios = 0
        
        # Listas para operaciones en batch
        registros_para_insertar = []
        registros_para_actualizar = []
        registros_historico = []
        
        # Paso 1: Obtener TODAS las ofertas ABIERTAS de la BD
        ofertas_abiertas_bd = self.repository.get_all_ofertas_abiertas()
        logger.info(f"📋 Ofertas ABIERTAS en BD: {len(ofertas_abiertas_bd)}")
        
        # Ofertas que llegaron en esta carga
        ofertas_en_carga = set([reg['oferta'] for reg in data_merged if reg.get('oferta')])
        logger.info(f"📥 Ofertas en carga actual: {len(ofertas_en_carga)}")
        
        # Ofertas ABIERTAS que NO llegaron en esta carga
        ofertas_ausentes = [o for o in ofertas_abiertas_bd if o not in ofertas_en_carga]
        
        # Incrementar contador de ausencias y cerrar si alcanzan el umbral
        if ofertas_ausentes:
            logger.info(f"🔍 Ofertas ausentes detectadas: {len(ofertas_ausentes)}")
            resultado_cierre = self.repository.increment_contador_ausencias(
                ofertas_ausentes, 
                umbral_cargas
            )
            logger.info(f"🔄 Ofertas con contador incrementado: {resultado_cierre['incrementadas']}")
            logger.info(f"🔒 Cerradas automáticamente: {resultado_cierre['cerradas']} ofertas")
            
            # Registrar en histórico las ofertas cerradas automáticamente
            if resultado_cierre['ofertas_cerradas']:
                self._registrar_cierres_automaticos(
                    resultado_cierre['ofertas_cerradas'],
                    ticket_carga,
                    create_date_automation
                )
        else:
            logger.info("✅ No hay ofertas ausentes en esta carga")
        
        # Paso 2: Obtener las ofertas que llegaron en la carga para comparar
        ofertas_nuevas = list(ofertas_en_carga)
        registros_existentes = self.repository.get_by_ofertas_batch(ofertas_nuevas)
        
        # Crear diccionario para búsqueda rápida
        existentes_dict = {reg.oferta: reg for reg in registros_existentes}
        logger.info(f"📋 Registros existentes para comparar: {len(existentes_dict)}")
        
        # Paso 3: Procesar cada registro del DataFrame
        chunk_size = 1000
        for i, registro in enumerate(data_merged):
            oferta = registro.get('oferta')
            
            if not oferta:
                logger.warning(f"⚠️ Registro sin oferta en índice {i}, omitiendo...")
                continue
            
            # Generar hash del registro nuevo
            hash_nuevo = generate_record_hash(registro)
            
            # Verificar si existe
            registro_existente = existentes_dict.get(oferta)
            
            if not registro_existente:
                # CASO 1: Registro NUEVO (INSERT)
                nuevo_id = uuid.uuid4()
                
                # Convertir pandas Timestamps a strings JSON serializables
                registro_json = prepare_for_json(registro)
                
                # Agregar garantia=False por defecto
                registro_json['garantia'] = False
                
                # Validar concepto de anulación
                concepto = registro.get('concepto', '').strip().upper()
                # estado_inicial = "CERRADO_AUTOMATICO" if concepto in CONCEPTOS_ANULACION else "ABIERTO"
                estado_inicial = "ABIERTO"
                
                registros_para_insertar.append({
                    "id": nuevo_id,
                    "ticket_carga": ticket_carga,
                    "oferta": oferta,
                    "hash_registro": hash_nuevo,
                    "campos_dinamicos": registro_json,
                    "estado_oferta": estado_inicial,
                    "contador_cargas_ausente": 0
                })
                
                # Agregar al histórico como INSERT
                registros_historico.append({
                    "fk_enlistment_manager_id": nuevo_id,
                    "ticket_carga": ticket_carga,
                    "create_date_automation": create_date_automation,
                    "oferta": oferta,
                    "hash_registro": hash_nuevo,
                    "tipo_operacion": TipoOperacion.INSERT,
                    "campos_dinamicos": registro_json,
                    "campos_modificados": None,
                    "estado_oferta": estado_inicial
                })
                
                contador_nuevos += 1
                
            else:
                # CASO 2: Registro EXISTENTE - Verificar estado
                estado_actual = registro_existente.estado_oferta
                concepto_actual = registro_existente.campos_dinamicos.get('concepto', '')
                
                # CASO 2.1: Oferta EN_TRAMITE - NO TOCAR
                if estado_actual == 'EN_TRAMITE':
                    contador_sin_cambios += 1
                    continue
                
                # CASO 2.1.1: Oferta EN_TRAMITE_PAUSADO con concepto OFERTA PAUSADA - NO TOCAR
                # Las ofertas pausadas no deben modificarse hasta que se reanuden
                if estado_actual == 'EN_TRAMITE_PAUSADO' and concepto_actual == 'OFERTA PAUSADA':
                    logger.debug(f"Oferta {oferta} está pausada, omitiendo actualización")
                    contador_sin_cambios += 1
                    continue
                
                # CASO 2.2: Oferta CERRADA - Verificar concepto antes de reabrir
                elif estado_actual == 'CERRADO':
                    # Si está en concepto MALO o RFS, NO actualizar
                    # Estas ofertas solo pueden ser liberadas manualmente por supervisores
                    if concepto_actual in ['MALO', 'RFS']:
                        logger.debug(f"Oferta {oferta} está en concepto {concepto_actual}, omitiendo actualización")
                        contador_sin_cambios += 1
                        continue
                    
                    # ============================================
                    # VALIDACIÓN ESPECIAL: Concepto 15 o 99 con gestión
                    # ============================================
                    concepto_nuevo = registro.get('concepto', '').strip()
                    if concepto_nuevo in ['15', '99']:
                        # Verificar si tiene gestión
                        from app.repositories.oferta_gestion_repository import OfertaGestionRepository
                        gestion_repo = OfertaGestionRepository(self.db)
                        tiene_gestion = gestion_repo.get_gestion_detalle_by_oferta(oferta) is not None
                        
                        if tiene_gestion:
                            # Oferta CERRADA con gestión y concepto 15/99 → NO reabrir
                            logger.info(f"Oferta {oferta} CERRADA con concepto {concepto_nuevo} y gestión, NO se reabre")
                            contador_sin_cambios += 1
                            continue
                    
                    # ============================================
                    # VALIDACIÓN: Verificar si fue gestionada por asesor
                    # ============================================
                    tiene_asesor_asignado = registro_existente.usuario_asignado_login is not None
                    tiene_gestion = False
                    
                    if tiene_asesor_asignado:
                        # Verificar si existe gestión en oferta_gestion_detalle
                        from app.repositories.oferta_gestion_repository import OfertaGestionRepository
                        gestion_repo = OfertaGestionRepository(self.db)
                        gestion = gestion_repo.get_gestion_detalle_by_oferta(oferta)
                        tiene_gestion = gestion is not None
                    
                    # Si tiene asesor Y gestión, requiere 3 cargas consecutivas antes de reabrir
                    if tiene_asesor_asignado and tiene_gestion:
                        contador_actual = registro_existente.contador_cargas_reapertura
                        nuevo_contador = contador_actual + 1
                        
                        if nuevo_contador < 3:
                            # Aún no alcanza el umbral - Solo incrementar contador, NO modificar oferta
                            registros_para_actualizar.append({
                                "id": registro_existente.id,
                                "ticket_carga": ticket_carga,
                                "hash_registro": registro_existente.hash_registro,  # Mantener hash original
                                "campos_dinamicos": registro_existente.campos_dinamicos,  # NO modificar campos
                                "estado_oferta": "CERRADO",  # Mantener CERRADO
                                "contador_cargas_reapertura": nuevo_contador,  # Incrementar contador
                                "contador_cargas_ausente": 0
                            })
                            
                            logger.info(f"Oferta {oferta} CERRADA con gestión, contador reapertura: {nuevo_contador}/3")
                            contador_sin_cambios += 1
                            continue
                        
                        # Alcanzó umbral de 3 cargas - Proceder con reapertura
                        logger.info(f"Oferta {oferta} alcanzó umbral de 3 cargas, reabriendo con garantía")
                    
                    # ============================================
                    # REAPERTURA: Sin gestión O alcanzó umbral de 3 cargas
                    # ============================================
                    registro_json = prepare_for_json(registro)
                    
                    # Verificar concepto antes de definir estado
                    # concepto_nuevo = registro.get('concepto', '').strip().upper()
                    
                    # if concepto_nuevo in CONCEPTOS_ANULACION:
                    #     # Es un concepto de anulación, cerrar automáticamente
                    #     estado_nuevo = "CERRADO_AUTOMATICO"
                    #     # No marcar garantía para conceptos de anulación
                    #     campos_modificados_reapertura = {
                    #         "estado_oferta": {"old": "CERRADO", "new": "CERRADO_AUTOMATICO"}
                    #     }
                    # else:
                    # Concepto normal, reabrir con garantía
                    estado_nuevo = "ABIERTO"
                    garantia_actual = registro_existente.campos_dinamicos.get('garantia', False)
                    registro_json['garantia'] = True  # Marcar TRUE en reapertura
                    campos_modificados_reapertura = {
                        "estado_oferta": {"old": "CERRADO", "new": "ABIERTO"},
                        "garantia": {"old": garantia_actual, "new": True}
                    }
                    
                    registros_para_actualizar.append({
                        "id": registro_existente.id,
                        "ticket_carga": ticket_carga,
                        "hash_registro": hash_nuevo,
                        "campos_dinamicos": registro_json,
                        "estado_oferta": estado_nuevo,
                        "contador_cargas_reapertura": 0,  # Resetear contador al reabrir
                        "contador_cargas_ausente": 0
                    })
                    
                    registros_historico.append({
                        "fk_enlistment_manager_id": registro_existente.id,
                        "ticket_carga": ticket_carga,
                        "create_date_automation": create_date_automation,
                        "oferta": oferta,
                        "hash_registro": hash_nuevo,
                        "tipo_operacion": TipoOperacion.UPDATE,
                        "campos_dinamicos": registro_json,
                        "campos_modificados": campos_modificados_reapertura,
                        "estado_oferta": estado_nuevo
                    })
                    contador_modificados += 1
                
                # CASO 2.3: Oferta CERRADO_AUTOMATICO que vuelve
                elif estado_actual == 'CERRADO_AUTOMATICO':
                    # ============================================
                    # VALIDACIÓN: Comparar hash PRIMERO
                    # ============================================
                    hash_existente = registro_existente.hash_registro
                    
                    if hash_nuevo == hash_existente:
                        # Hash igual → Sin cambios → NO registrar en histórico
                        self.repository.reset_contador_ausencia(registro_existente.id)
                        contador_sin_cambios += 1
                        continue
                    
                    # ============================================
                    # Hash diferente → Verificar cambios reales
                    # ============================================
                    registro_json = prepare_for_json(registro)
                    
                    # Verificar si sigue siendo concepto de anulación
                    # concepto_nuevo = registro.get('concepto', '').strip().upper()
                    
                    # if concepto_nuevo in CONCEPTOS_ANULACION:
                    #     # Sigue siendo concepto de anulación, mantener cerrado
                    #     estado_nuevo = "CERRADO_AUTOMATICO"
                    # else:
                    # El concepto cambió a uno normal, puede reabrirse
                    estado_nuevo = "ABIERTO"
                    
                    # Mantener garantia existente o asignar False si no existe
                    if 'garantia' not in registro_json:
                        registro_json['garantia'] = False
                    
                    # Comparar campos para detectar cambios reales
                    campos_modificados = compare_records(
                        registro_existente.campos_dinamicos,
                        registro_json
                    )
                    
                    # Si el estado cambió, agregarlo a campos_modificados
                    if estado_nuevo != estado_actual:
                        if not campos_modificados:
                            campos_modificados = {}
                        campos_modificados["estado_oferta"] = {
                            "old": estado_actual,
                            "new": estado_nuevo
                        }
                    
                    # Determinar campos de usuario según el estado
                    usuario_fields = self._get_usuario_fields_for_estado(estado_nuevo, registro_existente)
                    
                    # SOLO registrar en histórico si hay cambios reales
                    if campos_modificados and len(campos_modificados) > 0:
                        registros_para_actualizar.append({
                            "id": registro_existente.id,
                            "ticket_carga": ticket_carga,
                            "hash_registro": hash_nuevo,
                            "campos_dinamicos": registro_json,
                            "estado_oferta": estado_nuevo,
                            "contador_cargas_ausente": 0,
                            **usuario_fields
                        })
                        
                        registros_historico.append({
                            "fk_enlistment_manager_id": registro_existente.id,
                            "ticket_carga": ticket_carga,
                            "create_date_automation": create_date_automation,
                            "oferta": oferta,
                            "hash_registro": hash_nuevo,
                            "tipo_operacion": TipoOperacion.UPDATE,
                            "campos_dinamicos": registro_json,
                            "campos_modificados": campos_modificados,
                            "estado_oferta": estado_nuevo
                        })
                        contador_modificados += 1
                    else:
                        # Hash diferente pero sin cambios de contenido real
                        registros_para_actualizar.append({
                            "id": registro_existente.id,
                            "ticket_carga": ticket_carga,
                            "hash_registro": hash_nuevo,
                            "campos_dinamicos": registro_json,
                            "estado_oferta": estado_nuevo,
                            "contador_cargas_ausente": 0,
                            **usuario_fields
                        })
                        contador_sin_cambios += 1
                
                # CASO 2.4: Oferta ABIERTA - Lógica normal de comparación
                elif estado_actual == 'ABIERTO':
                    # ============================================
                    # VALIDACIÓN ESPECIAL: Concepto 15 o 99 sin gestión
                    # ============================================
                    concepto_nuevo = registro.get('concepto', '').strip()
                    
                    if concepto_nuevo in ['15', '99']:
                        # Verificar si tiene gestión
                        from app.repositories.oferta_gestion_repository import OfertaGestionRepository
                        gestion_repo = OfertaGestionRepository(self.db)
                        tiene_gestion = gestion_repo.get_gestion_detalle_by_oferta(oferta) is not None
                        
                        if not tiene_gestion:
                            # Cerrar automáticamente
                            registro_json = prepare_for_json(registro)
                            # Preservar garantía actual
                            registro_json['garantia'] = registro_existente.campos_dinamicos.get('garantia', False)
                            
                            registros_para_actualizar.append({
                                "id": registro_existente.id,
                                "ticket_carga": ticket_carga,
                                "hash_registro": hash_nuevo,
                                "campos_dinamicos": registro_json,
                                "estado_oferta": "CERRADO_AUTOMATICO",
                                "contador_cargas_ausente": 0,
                                **self._get_usuario_fields_for_estado("CERRADO_AUTOMATICO")
                            })
                            
                            registros_historico.append({
                                "fk_enlistment_manager_id": registro_existente.id,
                                "ticket_carga": ticket_carga,
                                "create_date_automation": create_date_automation,
                                "oferta": oferta,
                                "hash_registro": hash_nuevo,
                                "tipo_operacion": TipoOperacion.UPDATE,
                                "campos_dinamicos": registro_json,
                                "campos_modificados": {
                                    "estado_oferta": {"old": "ABIERTO", "new": "CERRADO_AUTOMATICO"},
                                    "concepto": {"old": registro_existente.campos_dinamicos.get('concepto'), "new": concepto_nuevo}
                                },
                                "estado_oferta": "CERRADO_AUTOMATICO"
                            })
                            
                            logger.info(f"Oferta {oferta} ABIERTA con concepto {concepto_nuevo} sin gestión → CERRADO_AUTOMATICO")
                            contador_modificados += 1
                            continue
                    
                    # ============================================
                    # Lógica normal de comparación de hash
                    # ============================================
                    hash_existente = registro_existente.hash_registro
                    
                    if hash_nuevo != hash_existente:
                        # Hash diferente - UPDATE
                        registro_json = prepare_for_json(registro)
                        
                        # # Verificar si cambió a concepto de anulación
                        # concepto_nuevo = registro.get('concepto', '').strip().upper()
                        
                        # if concepto_nuevo in CONCEPTOS_ANULACION:
                        #     # Cambió a concepto de anulación, cerrar automáticamente
                        #     estado_actualizado = "CERRADO_AUTOMATICO"
                        # else:
                        # Concepto normal, mantener abierta
                        estado_actualizado = "ABIERTO"
                        
                        # PROTECCIÓN DE GARANTÍA: Una vez TRUE, nunca vuelve a FALSE
                        garantia_actual = registro_existente.campos_dinamicos.get('garantia', False)
                        if 'garantia' not in registro_json:
                            # Si no viene en la carga, mantener valor actual
                            registro_json['garantia'] = garantia_actual
                        elif garantia_actual and not registro_json.get('garantia', False):
                            # Si era TRUE y ahora viene FALSE, mantener TRUE
                            registro_json['garantia'] = True
                        
                        # Comparar campos para detectar qué cambió
                        campos_modificados = compare_records(
                            registro_existente.campos_dinamicos, 
                            registro_json
                        )
                        
                        # Si el estado cambió, agregarlo a campos_modificados
                        if estado_actualizado != estado_actual:
                            if not campos_modificados:  # Si está vacío o None
                                campos_modificados = {}
                            campos_modificados["estado_oferta"] = {
                                "old": estado_actual, 
                                "new": estado_actualizado
                            }
                        
                        # Determinar campos de usuario según el estado
                        usuario_fields = self._get_usuario_fields_for_estado(estado_actualizado, registro_existente)
                        
                        # VALIDACIÓN: Solo registrar en histórico si hay cambios reales
                        if campos_modificados and len(campos_modificados) > 0:
                            registros_para_actualizar.append({
                                "id": registro_existente.id,
                                "ticket_carga": ticket_carga,
                                "hash_registro": hash_nuevo,
                                "campos_dinamicos": registro_json,
                                "estado_oferta": estado_actualizado,
                                "contador_cargas_ausente": 0,
                                **usuario_fields
                            })
                            
                            registros_historico.append({
                                "fk_enlistment_manager_id": registro_existente.id,
                                "ticket_carga": ticket_carga,
                                "create_date_automation": create_date_automation,
                                "oferta": oferta,
                                "hash_registro": hash_nuevo,
                                "tipo_operacion": TipoOperacion.UPDATE,
                                "campos_dinamicos": registro_json,
                                "campos_modificados": campos_modificados,
                                "estado_oferta": estado_actualizado
                            })
                            
                            contador_modificados += 1
                        else:
                            # Hash diferente pero sin cambios de contenido real (ej: solo orden de campos)
                            # Solo actualizar sin registrar en histórico
                            registros_para_actualizar.append({
                                "id": registro_existente.id,
                                "ticket_carga": ticket_carga,
                                "hash_registro": hash_nuevo,
                                "campos_dinamicos": registro_json,
                                "estado_oferta": estado_actualizado,
                                "contador_cargas_ausente": 0,
                                **usuario_fields
                            })
                            contador_sin_cambios += 1
                    else:
                        # Hash igual pero resetear contador porque llegó
                        self.repository.reset_contador_ausencia(registro_existente.id)
                        contador_sin_cambios += 1
            
            # Log de progreso cada 1000 registros
            if (i + 1) % chunk_size == 0:
                logger.info(f"⏳ Procesados {i + 1}/{len(data_merged)} registros...")
        
        logger.info(f"✅ Delta detection completado")
        logger.info(f"   📊 Nuevos: {contador_nuevos}")
        logger.info(f"   📊 Modificados: {contador_modificados}")
        logger.info(f"   📊 Sin cambios: {contador_sin_cambios}")
        
        # Paso 4: Ejecutar operaciones en batch
        if registros_para_insertar:
            logger.info(f"💾 Insertando {len(registros_para_insertar)} registros nuevos...")
            self.repository.bulk_insert(registros_para_insertar)
        
        if registros_para_actualizar:
            logger.info(f"🔄 Actualizando {len(registros_para_actualizar)} registros...")
            self.repository.bulk_update(registros_para_actualizar)
        
        if registros_historico:
            logger.info(f"📚 Guardando {len(registros_historico)} registros en histórico...")
            self.repository.bulk_insert_history(registros_historico)
        
        return {
            "nuevos": contador_nuevos,
            "modificados": contador_modificados,
            "sin_cambios": contador_sin_cambios
        }

    def _registrar_cierres_automaticos(
        self,
        ofertas_cerradas: List[Dict[str, Any]],
        ticket_carga: str,
        create_date_automation: datetime
    ) -> None:
        """
        Registra en el histórico las ofertas cerradas automáticamente.
        
        Args:
            ofertas_cerradas: Lista de dict con datos de ofertas cerradas
            ticket_carga: Ticket de la carga
            create_date_automation: Fecha de la carga
        """
        from app.core.config import settings
        
        registros_historico = []
        
        for oferta_data in ofertas_cerradas:
            registros_historico.append({
                "fk_enlistment_manager_id": oferta_data['id'],
                "ticket_carga": ticket_carga,
                "create_date_automation": create_date_automation,
                "oferta": oferta_data['oferta'],
                "hash_registro": oferta_data['hash_registro'],
                "tipo_operacion": TipoOperacion.UPDATE,
                "campos_dinamicos": oferta_data['campos_dinamicos'],
                "campos_modificados": {
                    "estado_oferta": {
                        "old": "ABIERTO", 
                        "new": "CERRADO_AUTOMATICO"
                    },
                    "motivo": f"Oferta no apareció en las últimas {settings.ENLISTMENT_CARGAS_INACTIVIDAD} cargas"
                },
                "estado_oferta": "CERRADO_AUTOMATICO"
            })
        
        if registros_historico:
            self.repository.bulk_insert_history(registros_historico)
            logger.info(f"📚 Cierres automáticos registrados en histórico: {len(registros_historico)}")

    # ==========================================
    # CONSULTAS
    # ==========================================

    async def get_data_with_filters(
        self, 
        page: int = 1, 
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Obtiene datos con filtros y paginación.
        
        Args:
            page: Página actual
            limit: Registros por página
            filters: Filtros opcionales
            
        Returns:
            Dict con datos y metadata de paginación
        """
        try:
            registros, total = self.repository.get_all_paginated(page, limit, filters)
            
            # Convertir a diccionarios
            data = []
            for reg in registros:
                data.append({
                    "id": str(reg.id),
                    "oferta": reg.oferta,
                    "ticket_carga": reg.ticket_carga,
                    "hash_registro": reg.hash_registro,
                    "estado_oferta": reg.estado_oferta,
                    "usuario_asignado_login": reg.usuario_asignado_login,
                    "usuario_asignado_nombre": reg.usuario_asignado_nombre,
                    "campos_dinamicos": reg.campos_dinamicos,
                    "created_at": reg.created_at.isoformat() if reg.created_at else None,
                    "updated_at": reg.updated_at.isoformat() if reg.updated_at else None
                })
            
            total_pages = (total + limit - 1) // limit
            
            return {
                "data": data,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": total,
                    "total_pages": total_pages
                }
            }
            
        except Exception as e:
            logger.error(f"Error en get_data_with_filters: {e}")
            raise

    async def get_by_oferta(self, oferta: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene un registro específico por oferta.
        
        Args:
            oferta: Número de oferta
            
        Returns:
            Datos del registro o None
        """
        try:
            registro = self.repository.get_by_oferta(oferta)
            
            if not registro:
                return None
            
            return {
                "id": str(registro.id),
                "oferta": registro.oferta,
                "ticket_carga": registro.ticket_carga,
                "hash_registro": registro.hash_registro,
                "campos_dinamicos": registro.campos_dinamicos,
                "created_at": registro.created_at.isoformat() if registro.created_at else None,
                "updated_at": registro.updated_at.isoformat() if registro.updated_at else None
            }
            
        except Exception as e:
            logger.error(f"Error en get_by_oferta: {e}")
            raise

    async def get_history_by_oferta(self, oferta: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Obtiene el histórico de cambios de una oferta.
        
        Args:
            oferta: Número de oferta
            limit: Límite de registros
            
        Returns:
            Lista de cambios históricos
        """
        try:
            registros = self.repository.get_history_by_oferta(oferta, limit)
            
            return [{
                "id": str(reg.id),
                "oferta": reg.oferta,
                "ticket_carga": reg.ticket_carga,
                "create_date_automation": reg.create_date_automation.isoformat() if reg.create_date_automation else None,
                "tipo_operacion": reg.tipo_operacion.value,
                "hash_registro": reg.hash_registro,
                "campos_dinamicos": reg.campos_dinamicos,
                "campos_modificados": reg.campos_modificados,
                "created_at": reg.created_at.isoformat() if reg.created_at else None
            } for reg in registros]
            
        except Exception as e:
            logger.error(f"Error en get_history_by_oferta: {e}")
            raise

    async def get_last_load_stats(self) -> Optional[Dict[str, Any]]:
        """
        Obtiene estadísticas de la última carga.
        
        Returns:
            Dict con estadísticas o None
        """
        try:
            control = self.repository.get_last_control()
            
            if not control:
                return None
            
            return {
                "ticket_carga": control.ticket_carga,
                "create_date_automation": control.create_date_automation.isoformat() if control.create_date_automation else None,
                "total_registros_procesados": control.total_registros_procesados,
                "total_registros_nuevos": control.total_registros_nuevos,
                "total_registros_actualizados": control.total_registros_actualizados,
                "total_registros_sin_cambios": control.total_registros_sin_cambios,
                "tiempo_ejecucion_segundos": control.tiempo_ejecucion_segundos,
                "estado": control.estado.value,
                "mensaje_error": control.mensaje_error,
                "columnas_detectadas": control.columnas_detectadas
            }
            
        except Exception as e:
            logger.error(f"Error en get_last_load_stats: {e}")
            raise

    async def get_stats_by_field(self, field_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Obtiene estadísticas agrupadas por un campo.
        
        Args:
            field_name: Nombre del campo
            limit: Límite de resultados
            
        Returns:
            Lista de estadísticas
        """
        try:
            return self.repository.get_stats_by_field(field_name, limit)
        except Exception as e:
            logger.error(f"Error en get_stats_by_field: {e}")
            raise

