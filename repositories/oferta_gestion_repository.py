import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc, func, and_, or_
from sqlalchemy.exc import IntegrityError
from app.models.oferta_gestion_model import (
    OfertaAccionCatalogo,
    OfertaSubaccionCatalogo,
    OfertaGestionDetalle,
    OfertaHistoricoEstados,
    OfertaConfiguracion,
    OfertaConfiguracionAvanzada,
    OfertaConfiguracionAvanzadaHistory
)
from app.models.enlistment_manager_model import EnlistmentManager
from app.db.postgres import SessionLocalPG
from app.db.timezone_types import get_bogota_now
from app.repositories.enlistment_repository import EnlistmentRepository
from app.core.constants import CONCEPTOS_ANULACION, CONCEPTOS_EXCLUIDOS_ALEATORIO
import uuid

logger = logging.getLogger("oferta_gestion_repository")


class OfertaGestionRepository:
    """Repository para operaciones de gestión de ofertas"""
    
    # Constante para máximo de intentos de búsqueda
    MAX_INTENTOS_BUSQUEDA = 10  # Máximo de ofertas a revisar antes de rendirse

    def __init__(self, db: Session):
        """Inicializa el repository con la sesión de base de datos.
        
        Args:
            db: Sesión de SQLAlchemy inyectada por dependency
        """
        self.db = db
        self.enlistment_repo = EnlistmentRepository(db)

    # ==========================================
    # CATÁLOGO DE ACCIONES
    # ==========================================

    def get_all_acciones(self, include_inactive: bool = False) -> List[OfertaAccionCatalogo]:
        """Obtiene todas las acciones del catálogo"""
        try:
            query = self.db.query(OfertaAccionCatalogo)
            if not include_inactive:
                query = query.filter(OfertaAccionCatalogo.is_active == True)
            return query.order_by(OfertaAccionCatalogo.orden).all()
        except Exception as e:
            logger.error(f"Error al obtener acciones: {e}")
            return []

    def get_accion_by_id(self, accion_id: str) -> Optional[OfertaAccionCatalogo]:
        """Obtiene una acción por ID"""
        try:
            return self.db.query(OfertaAccionCatalogo).filter(
                OfertaAccionCatalogo.id == uuid.UUID(accion_id)
            ).first()
        except Exception as e:
            logger.error(f"Error al obtener acción {accion_id}: {e}")
            return None

    def get_accion_by_nombre(self, nombre: str) -> Optional[OfertaAccionCatalogo]:
        """Obtiene una acción por nombre"""
        try:
            return self.db.query(OfertaAccionCatalogo).filter(
                OfertaAccionCatalogo.nombre_accion == nombre,
                OfertaAccionCatalogo.is_active == True
            ).first()
        except Exception as e:
            logger.error(f"Error al obtener acción por nombre {nombre}: {e}")
            return None

    def create_accion(self, data: Dict[str, Any]) -> Optional[OfertaAccionCatalogo]:
        """Crea una nueva acción"""
        try:
            accion = OfertaAccionCatalogo(
                nombre_accion=data['nombre'],
                descripcion=data.get('descripcion'),
                orden=data.get('orden', 0)
            )
            self.db.add(accion)
            self.db.commit()
            self.db.refresh(accion)
            logger.info(f"Acción creada: {accion.nombre_accion}")
            return accion
        except IntegrityError:
            self.db.rollback()
            logger.error(f"La acción '{data['nombre']}' ya existe")
            return None
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error al crear acción: {e}")
            return None

    def update_accion(self, accion_id: str, data: Dict[str, Any]) -> Optional[OfertaAccionCatalogo]:
        """Actualiza una acción existente"""
        try:
            accion = self.get_accion_by_id(accion_id)
            if not accion:
                return None
            
            for key, value in data.items():
                if value is not None and hasattr(accion, key):
                    setattr(accion, key, value)
            
            self.db.commit()
            self.db.refresh(accion)
            logger.info(f"Acción actualizada: {accion_id}")
            return accion
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error al actualizar acción: {e}")
            return None

    def delete_accion(self, accion_id: str) -> bool:
        """Elimina (desactiva) una acción"""
        try:
            accion = self.get_accion_by_id(accion_id)
            if not accion:
                return False
            
            accion.is_active = False
            self.db.commit()
            logger.info(f"Acción desactivada: {accion_id}")
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error al desactivar acción: {e}")
            return False

    # ==========================================
    # CATÁLOGO DE SUBACCIONES
    # ==========================================

    def get_subacciones_by_accion(self, accion_id: str, include_inactive: bool = False) -> List[OfertaSubaccionCatalogo]:
        """Obtiene todas las subacciones de una acción"""
        try:
            query = self.db.query(OfertaSubaccionCatalogo).filter(
                OfertaSubaccionCatalogo.accion_id == uuid.UUID(accion_id)
            )
            if not include_inactive:
                query = query.filter(OfertaSubaccionCatalogo.is_active == True)
            return query.order_by(OfertaSubaccionCatalogo.orden).all()
        except Exception as e:
            logger.error(f"Error al obtener subacciones: {e}")
            return []

    def get_subaccion_by_id(self, subaccion_id: str) -> Optional[OfertaSubaccionCatalogo]:
        """Obtiene una subacción por ID"""
        try:
            return self.db.query(OfertaSubaccionCatalogo).filter(
                OfertaSubaccionCatalogo.id == uuid.UUID(subaccion_id)
            ).first()
        except Exception as e:
            logger.error(f"Error al obtener subacción {subaccion_id}: {e}")
            return None

    def create_subaccion(self, data: Dict[str, Any]) -> Optional[OfertaSubaccionCatalogo]:
        """Crea una nueva subacción"""
        try:
            subaccion = OfertaSubaccionCatalogo(
                accion_id=uuid.UUID(data['accion_id']),
                nombre_subaccion=data['nombre'],
                orden=data.get('orden', 0)
            )
            self.db.add(subaccion)
            self.db.commit()
            self.db.refresh(subaccion)
            logger.info(f"Subacción creada: {subaccion.nombre_subaccion}")
            return subaccion
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error al crear subacción: {e}")
            return None

    def update_subaccion(self, subaccion_id: str, data: Dict[str, Any]) -> Optional[OfertaSubaccionCatalogo]:
        """Actualiza una subacción existente"""
        try:
            subaccion = self.get_subaccion_by_id(subaccion_id)
            if not subaccion:
                return None
            
            for key, value in data.items():
                if value is not None and hasattr(subaccion, key):
                    setattr(subaccion, key, value)
            
            self.db.commit()
            self.db.refresh(subaccion)
            logger.info(f"Subacción actualizada: {subaccion_id}")
            return subaccion
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error al actualizar subacción: {e}")
            return None

    def delete_subaccion(self, subaccion_id: str) -> bool:
        """Elimina (desactiva) una subacción"""
        try:
            subaccion = self.get_subaccion_by_id(subaccion_id)
            if not subaccion:
                return False
            
            subaccion.is_active = False
            self.db.commit()
            logger.info(f"Subacción desactivada: {subaccion_id}")
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error al desactivar subacción: {e}")
            return False

    def validate_subaccion_belongs_to_accion(self, subaccion_id: str, accion_id: str) -> bool:
        """Valida que una subacción pertenezca a una acción específica"""
        try:
            subaccion = self.get_subaccion_by_id(subaccion_id)
            return subaccion and str(subaccion.accion_id) == accion_id
        except Exception as e:
            logger.error(f"Error al validar subacción: {e}")
            return False

    # ==========================================
    # GESTIÓN DE OFERTAS
    # ==========================================

    def get_oferta_disponible(self, concepto: Optional[str] = None) -> Optional[EnlistmentManager]:
        """
        Obtiene oferta disponible según configuración GLOBAL.
        
        LÓGICA V3 GLOBAL:
        1. Obtener configuración GLOBAL activa
        2. Construir query base (estado ABIERTO)
          3. Aplicar filtros según configuración GLOBAL:
           - Conceptos (TODOS o ESPECIFICOS)
           - Tipo trabajo (TODOS, NUEVO, CAMBIO)
           - Regional (TODOS o ESPECIFICAS)
              - Concepto específico (si se proporciona parámetro)
              - Exclusión adicional en modo aleatorio para 14 y reconfiguraciones
        4. Aplicar ordenamiento según configuración (campo + dirección)
        5. Validación post-consulta de conceptos excluidos
        6. Reintentos con IDs excluidos si es necesario
        
        Args:
            concepto: Concepto específico solicitado (opcional)
            
        Returns:
            Oferta disponible o None
        """
        try:
            # 1. Obtener configuración GLOBAL
            config = self.get_configuracion_global_avanzada()
            
            # Si no hay configuración, usar valores por defecto
            if not config:
                logger.warning("⚠️ No hay configuración global, usando valores por defecto")
                config = type('obj', (object,), {
                    'campo_orden': 'created_at',
                    'direccion_orden': 'ASC',
                    'filtro_conceptos_tipo': 'TODOS',
                    'conceptos_seleccionados': '[]',
                    'filtro_tipo_trabajo': 'TODOS',
                    'filtro_regional_tipo': 'TODOS',
                    'regionales_seleccionadas': '[]'
                })()
            
            # Control de reintentos
            ids_excluidos = []
            intentos = 0
            
            while intentos < self.MAX_INTENTOS_BUSQUEDA:
                intentos += 1
                
                # 2. Query base
                query = self.db.query(EnlistmentManager).filter(
                    EnlistmentManager.estado_oferta == 'ABIERTO'
                )
                
                # Excluir IDs ya revisados
                if ids_excluidos:
                    query = query.filter(EnlistmentManager.id.notin_(ids_excluidos))
                
                # 3. Aplicar filtros GLOBALES
                query = self._aplicar_filtro_conceptos(query, config, concepto)
                query = self._aplicar_filtro_tipo_trabajo(query, config)
                query = self._aplicar_filtro_regional(query, config)
                
                # 4. Aplicar ordenamiento
                query = self._aplicar_ordenamiento(query, config)
                
                # 5. Obtener primera oferta
                oferta = query.first()
                
                if not oferta:
                    logger.warning(
                        f"⚠️ No hay ofertas disponibles según configuración GLOBAL "
                        f"(intento {intentos}/{self.MAX_INTENTOS_BUSQUEDA})"
                    )
                    return None
                
                # 6. Validación post-consulta
                concepto_actual = (oferta.campos_dinamicos.get('concepto', '') or '').strip().upper()
                
                if concepto_actual in CONCEPTOS_ANULACION:
                    logger.warning(
                        f"⚠️ Oferta {oferta.oferta} tiene concepto excluido '{concepto_actual}'. "
                        f"Reintentando... (intento {intentos})"
                    )
                    ids_excluidos.append(oferta.id)
                    continue

                if concepto is None and concepto_actual in CONCEPTOS_EXCLUIDOS_ALEATORIO:
                    logger.warning(
                        f"⚠️ Oferta {oferta.oferta} tiene concepto excluido para aleatorio '{concepto_actual}'. "
                        f"Reintentando... (intento {intentos})"
                    )
                    ids_excluidos.append(oferta.id)
                    continue
                
                if not concepto_actual:
                    logger.warning(
                        f"⚠️ Oferta {oferta.oferta} tiene concepto vacío. "
                        f"Reintentando... (intento {intentos})"
                    )
                    ids_excluidos.append(oferta.id)
                    continue
                
                # ✅ Oferta válida
                if intentos > 1:
                    logger.info(
                        f"✅ Oferta encontrada tras {intentos} intentos: "
                        f"{oferta.oferta} (concepto: {concepto_actual})"
                    )
                else:
                    logger.info(f"✅ Oferta disponible: {oferta.oferta} (concepto: {concepto_actual})")
                
                return oferta
            
            # Máximo de intentos alcanzado
            logger.error(
                f"❌ MÁXIMO DE INTENTOS ALCANZADO ({self.MAX_INTENTOS_BUSQUEDA}). "
                f"No se encontró oferta válida según configuración GLOBAL"
            )
            return None
            
        except Exception as e:
            logger.error(f"Error al obtener oferta disponible: {e}")
            return None

    def get_conceptos_with_count(self) -> List[Tuple[str, int]]:
        """
        Obtiene todos los conceptos y su cantidad de ofertas en estado ABIERTO.
        Excluye conceptos de anulación y los conceptos reservados para aleatorio.
        Retorna: Lista de tuplas (concepto, cantidad)
        """
        try:
            query = self.db.query(
                EnlistmentManager.campos_dinamicos['concepto'].astext.label('concepto'),
                func.count(EnlistmentManager.id).label('cantidad')
            ).filter(
                and_(
                    EnlistmentManager.estado_oferta == 'ABIERTO',
                    func.upper(func.trim(
                        EnlistmentManager.campos_dinamicos['concepto'].astext
                    )).notin_(CONCEPTOS_ANULACION + CONCEPTOS_EXCLUIDOS_ALEATORIO),
                    EnlistmentManager.campos_dinamicos['concepto'].astext.isnot(None),
                    EnlistmentManager.campos_dinamicos['concepto'].astext != ''
                )
            ).group_by(
                EnlistmentManager.campos_dinamicos['concepto'].astext
            ).order_by(
                EnlistmentManager.campos_dinamicos['concepto'].astext
            ).all()
            
            logger.info(f"Obtenidos {len(query)} conceptos distintos (excluidos: {CONCEPTOS_ANULACION})")
            return query
        except Exception as e:
            logger.error(f"Error al obtener conceptos con conteo: {e}")
            return []

    def get_oferta_by_numero(self, oferta: str) -> Optional[EnlistmentManager]:
        """Obtiene una oferta por su número"""
        try:
            return self.db.query(EnlistmentManager).filter(
                EnlistmentManager.oferta == oferta
            ).first()
        except Exception as e:
            logger.error(f"Error al obtener oferta {oferta}: {e}")
            return None

    def get_oferta_en_tramite_by_usuario(self, usuario_login: str) -> Optional[EnlistmentManager]:
        """Obtiene la oferta EN_TRAMITE asignada a un usuario"""
        try:
            return self.db.query(EnlistmentManager).filter(
                EnlistmentManager.estado_oferta == 'EN_TRAMITE',
                EnlistmentManager.usuario_asignado_login == usuario_login
            ).first()
        except Exception as e:
            logger.error(f"Error al obtener oferta en trámite del usuario {usuario_login}: {e}")
            return None

    def congelar_oferta(self, oferta_id: str, usuario_data: Dict[str, Any]) -> Optional[EnlistmentManager]:
        """
        Congela una oferta asignándola a un usuario.
        Cambia el estado a EN_TRAMITE y registra en el histórico.
        """
        try:
            oferta = self.db.query(EnlistmentManager).filter(
                EnlistmentManager.id == uuid.UUID(oferta_id)
            ).first()
            
            if not oferta:
                return None
            
            # Guardar estado anterior para el histórico
            estado_anterior = oferta.estado_oferta
            fecha_asignacion_nueva = get_bogota_now()
            
            # Aplicar cambios
            oferta.estado_oferta = 'EN_TRAMITE'
            oferta.usuario_asignado_login = usuario_data['login']
            oferta.usuario_asignado_nombre = usuario_data['nombre']
            oferta.usuario_asignado_profile_id = usuario_data['profile_id']
            oferta.fecha_asignacion = fecha_asignacion_nueva
            
            self.db.commit()
            self.db.refresh(oferta)
            
            # Registrar en histórico de enlistment_manager_history
            campos_modificados = {
                "estado_oferta": {"old": estado_anterior, "new": "EN_TRAMITE"},
                "usuario_asignado_login": {"old": None, "new": usuario_data['login']},
                "usuario_asignado_nombre": {"old": None, "new": usuario_data['nombre']},
                "fecha_asignacion": {"old": None, "new": fecha_asignacion_nueva.isoformat()}
            }
            self.enlistment_repo.create_manual_history_record(oferta, campos_modificados)
            
            logger.info(f"Oferta {oferta.oferta} congelada para {usuario_data['login']}")
            return oferta
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error al congelar oferta: {e}")
            return None

    def descongelar_oferta(self, oferta: str) -> Optional[EnlistmentManager]:
        """
        Descongela una oferta liberándola.
        Cambia el estado a ABIERTO, limpia datos de asignación y registra en el histórico.
        """
        try:
            oferta_obj = self.get_oferta_by_numero(oferta)
            if not oferta_obj:
                return None
            
            # Guardar datos anteriores para el histórico
            estado_anterior = oferta_obj.estado_oferta
            usuario_anterior = oferta_obj.usuario_asignado_login
            nombre_anterior = oferta_obj.usuario_asignado_nombre
            fecha_asignacion_anterior = oferta_obj.fecha_asignacion
            
            # Aplicar cambios
            oferta_obj.estado_oferta = 'ABIERTO'
            oferta_obj.usuario_asignado_login = None
            oferta_obj.usuario_asignado_nombre = None
            oferta_obj.usuario_asignado_profile_id = None
            oferta_obj.fecha_asignacion = None
            
            self.db.commit()
            self.db.refresh(oferta_obj)
            
            # Registrar en histórico de enlistment_manager_history
            campos_modificados = {
                "estado_oferta": {"old": estado_anterior, "new": "ABIERTO"},
                "usuario_asignado_login": {"old": usuario_anterior, "new": None},
                "usuario_asignado_nombre": {"old": nombre_anterior, "new": None},
                "fecha_asignacion": {"old": fecha_asignacion_anterior.isoformat() if fecha_asignacion_anterior else None, "new": None}
            }
            self.enlistment_repo.create_manual_history_record(oferta_obj, campos_modificados)
            
            logger.info(f"Oferta {oferta} descongelada")
            return oferta_obj
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error al descongelar oferta: {e}")
            return None

    def reasignar_oferta(self, oferta: str, nuevo_usuario_data: Dict[str, Any]) -> Optional[EnlistmentManager]:
        """Reasigna una oferta a otro usuario y registra en el histórico"""
        try:
            oferta_obj = self.get_oferta_by_numero(oferta)
            if not oferta_obj:
                return None
            
            # Guardar datos anteriores para el histórico
            usuario_anterior = oferta_obj.usuario_asignado_login
            nombre_anterior = oferta_obj.usuario_asignado_nombre
            fecha_asignacion_anterior = oferta_obj.fecha_asignacion
            estado_anterior = oferta_obj.estado_oferta
            fecha_asignacion_nueva = get_bogota_now()
            
            # Aplicar cambios
            oferta_obj.usuario_asignado_login = nuevo_usuario_data['login']
            oferta_obj.usuario_asignado_nombre = nuevo_usuario_data['nombre']
            oferta_obj.usuario_asignado_profile_id = nuevo_usuario_data['profile_id']
            oferta_obj.fecha_asignacion = fecha_asignacion_nueva
            oferta_obj.estado_oferta = 'EN_TRAMITE'
            
            self.db.commit()
            self.db.refresh(oferta_obj)
            
            # Registrar en histórico de enlistment_manager_history
            campos_modificados = {
                "usuario_asignado_login": {"old": usuario_anterior, "new": nuevo_usuario_data['login']},
                "usuario_asignado_nombre": {"old": nombre_anterior, "new": nuevo_usuario_data['nombre']},
                "estado_oferta": {"old": estado_anterior, "new": 'EN_TRAMITE'},
                "fecha_asignacion": {"old": fecha_asignacion_anterior.isoformat() if fecha_asignacion_anterior else None, "new": fecha_asignacion_nueva.isoformat()}
            }
            self.enlistment_repo.create_manual_history_record(oferta_obj, campos_modificados)
            
            logger.info(f"Oferta {oferta} reasignada a {nuevo_usuario_data['login']}")
            return oferta_obj
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error al reasignar oferta: {e}")
            return None

    def cerrar_oferta(self, oferta: str) -> Optional[EnlistmentManager]:
        """Cierra una oferta cambiando su estado a CERRADO y registra en el histórico"""
        try:
            oferta_obj = self.get_oferta_by_numero(oferta)
            if not oferta_obj:
                return None
            
            # Guardar estado anterior para el histórico
            estado_anterior = oferta_obj.estado_oferta
            fecha_gestion_nueva = get_bogota_now()
            
            # Aplicar cambios
            oferta_obj.estado_oferta = 'CERRADO'
            oferta_obj.fecha_gestion = fecha_gestion_nueva
            
            self.db.commit()
            self.db.refresh(oferta_obj)
            
            # Registrar en histórico de enlistment_manager_history
            campos_modificados = {
                "estado_oferta": {"old": estado_anterior, "new": "CERRADO"},
                "fecha_gestion": {"old": None, "new": fecha_gestion_nueva.isoformat()}
            }
            self.enlistment_repo.create_manual_history_record(oferta_obj, campos_modificados)
            
            logger.info(f"Oferta {oferta} cerrada")
            return oferta_obj
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error al cerrar oferta: {e}")
            return None

    def get_ofertas_en_tramite(self, page: int = 1, limit: int = 50) -> Tuple[List[EnlistmentManager], int]:
        """Obtiene todas las ofertas EN_TRAMITE con paginación"""
        try:
            offset = (page - 1) * limit
            
            query = self.db.query(EnlistmentManager).filter(
                EnlistmentManager.estado_oferta == 'EN_TRAMITE'
            )
            
            total = query.count()
            ofertas = query.order_by(desc(EnlistmentManager.fecha_asignacion)).offset(offset).limit(limit).all()
            
            return ofertas, total
        except Exception as e:
            logger.error(f"Error al obtener ofertas en trámite: {e}")
            return [], 0

    # ==========================================
    # DETALLE DE GESTIÓN
    # ==========================================

    def create_gestion_detalle(self, data: Dict[str, Any]) -> Optional[OfertaGestionDetalle]:
        """Crea un registro de detalle de gestión"""
        try:
            detalle = OfertaGestionDetalle(
                oferta=data['oferta'],
                accion_id=uuid.UUID(data['accion_id']),
                subaccion_id=uuid.UUID(data['subaccion_id']),
                observacion=data.get('observacion'),
                usuario_login=data['usuario_login'],
                usuario_nombre=data['usuario_nombre'],
                usuario_profile_id=data['usuario_profile_id'],
                fecha_gestion=get_bogota_now()
            )
            self.db.add(detalle)
            self.db.commit()
            self.db.refresh(detalle)
            logger.info(f"Detalle de gestión creado para oferta {data['oferta']}")
            return detalle
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error al crear detalle de gestión: {e}")
            return None

    def get_gestion_detalle_by_oferta(self, oferta: str) -> Optional[OfertaGestionDetalle]:
        """Obtiene el detalle de gestión de una oferta"""
        try:
            return self.db.query(OfertaGestionDetalle).filter(
                OfertaGestionDetalle.oferta == oferta
            ).first()
        except Exception as e:
            logger.error(f"Error al obtener detalle de gestión: {e}")
            return None

    # ==========================================
    # HISTÓRICO DE ESTADOS
    # ==========================================

    def create_historico_estado(self, data: Dict[str, Any]) -> Optional[OfertaHistoricoEstados]:
        """Crea un registro en el histórico de estados"""
        try:
            historico = OfertaHistoricoEstados(
                oferta=data['oferta'],
                accion_sistema=data['accion_sistema'],
                estado_anterior=data['estado_anterior'],
                estado_nuevo=data['estado_nuevo'],
                usuario_login=data['usuario_login'],
                usuario_nombre=data['usuario_nombre'],
                usuario_profile_id=data['usuario_profile_id'],
                asesor_asignado_login=data.get('asesor_asignado_login'),
                asesor_asignado_nombre=data.get('asesor_asignado_nombre'),
                motivo=data.get('motivo'),
                ip_address=data.get('ip_address'),
                fecha_accion=get_bogota_now()
            )
            self.db.add(historico)
            self.db.commit()
            self.db.refresh(historico)
            logger.info(f"Histórico registrado: {data['accion_sistema']} para oferta {data['oferta']}")
            return historico
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error al crear histórico: {e}")
            return None

    def get_historico_by_oferta(self, oferta: str) -> List[OfertaHistoricoEstados]:
        """Obtiene todo el histórico de una oferta"""
        try:
            return self.db.query(OfertaHistoricoEstados).filter(
                OfertaHistoricoEstados.oferta == oferta
            ).order_by(desc(OfertaHistoricoEstados.fecha_accion)).all()
        except Exception as e:
            logger.error(f"Error al obtener histórico: {e}")
            return []

    # ==========================================
    # CONFIGURACIÓN
    # ==========================================

    def get_configuracion_by_profile(self, profile_id: int) -> Optional[OfertaConfiguracion]:
        """Obtiene la configuración de un perfil"""
        try:
            return self.db.query(OfertaConfiguracion).filter(
                OfertaConfiguracion.profile_id == profile_id,
                OfertaConfiguracion.is_active == True
            ).first()
        except Exception as e:
            logger.error(f"Error al obtener configuración: {e}")
            return None

    def create_or_update_configuracion(self, data: Dict[str, Any]) -> Optional[OfertaConfiguracion]:
        """Crea o actualiza una configuración"""
        try:
            config = self.get_configuracion_by_profile(data['profile_id'])
            
            if config:
                # Actualizar
                config.orden_busqueda = data['orden_busqueda']
                config.descripcion = data.get('descripcion', config.descripcion)
                config.updated_by = data.get('updated_by')
            else:
                # Crear
                config = OfertaConfiguracion(
                    profile_id=data['profile_id'],
                    orden_busqueda=data['orden_busqueda'],
                    descripcion=data.get('descripcion'),
                    updated_by=data.get('updated_by')
                )
                self.db.add(config)
            
            self.db.commit()
            self.db.refresh(config)
            logger.info(f"Configuración guardada para profile_id {data['profile_id']}")
            return config
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error al guardar configuración: {e}")
            return None

    # ==========================================
    # REPORTES
    # ==========================================

    def get_productividad_usuario(
        self, 
        usuario_login: str, 
        fecha_desde: Optional[datetime] = None,
        fecha_hasta: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Obtiene estadísticas de productividad de un usuario"""
        try:
            query = self.db.query(OfertaGestionDetalle).filter(
                OfertaGestionDetalle.usuario_login == usuario_login
            )
            
            if fecha_desde:
                query = query.filter(OfertaGestionDetalle.fecha_gestion >= fecha_desde)
            if fecha_hasta:
                query = query.filter(OfertaGestionDetalle.fecha_gestion <= fecha_hasta)
            
            gestiones = query.all()
            
            if not gestiones:
                return {
                    'total_gestionadas': 0,
                    'por_accion': {},
                    'tiempo_promedio_minutos': None
                }
            
            # Contar por acción
            por_accion = {}
            for gestion in gestiones:
                accion = self.get_accion_by_id(str(gestion.accion_id))
                if accion:
                    nombre_accion = accion.nombre_accion
                    por_accion[nombre_accion] = por_accion.get(nombre_accion, 0) + 1
            
            # Calcular tiempo promedio (si hay datos de fecha_asignacion)
            tiempos = []
            for gestion in gestiones:
                oferta = self.get_oferta_by_numero(gestion.oferta)
                if oferta and oferta.fecha_asignacion and oferta.fecha_gestion:
                    tiempo = (oferta.fecha_gestion - oferta.fecha_asignacion).total_seconds() / 60
                    tiempos.append(tiempo)
            
            tiempo_promedio = sum(tiempos) / len(tiempos) if tiempos else None
            
            return {
                'total_gestionadas': len(gestiones),
                'por_accion': por_accion,
                'tiempo_promedio_minutos': tiempo_promedio
            }
        except Exception as e:
            logger.error(f"Error al obtener productividad: {e}")
            return {
                'total_gestionadas': 0,
                'por_accion': {},
                'tiempo_promedio_minutos': None
            }

    # ==========================================
    # CONCEPTOS ESPECIALES: MALO y RFS
    # ==========================================

    def cambiar_concepto_y_guardar_anterior(
        self,
        oferta: str,
        nuevo_concepto: str
    ) -> tuple[Optional[EnlistmentManager], Optional[str]]:
        """
        Cambia el concepto de una oferta y guarda el concepto anterior.
        
        Args:
            oferta: Número de oferta
            nuevo_concepto: Nuevo concepto a asignar (MALO, RFS, OFERTA PAUSADA)
            
        Returns:
            Tupla (oferta_actualizada, concepto_anterior) o (None, None) en caso de error
        """
        try:
            oferta_obj = self.get_oferta_by_numero(oferta)
            if not oferta_obj:
                return None, None
            
            # Obtener concepto actual
            concepto_actual = oferta_obj.campos_dinamicos.get('concepto', '')
            
            # Guardar concepto anterior si no existe
            if 'concepto_anterior' not in oferta_obj.campos_dinamicos:
                oferta_obj.campos_dinamicos['concepto_anterior'] = concepto_actual
            
            # Cambiar al nuevo concepto
            oferta_obj.campos_dinamicos['concepto'] = nuevo_concepto
            
            # Marcar el campo como modificado para que SQLAlchemy lo detecte
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(oferta_obj, 'campos_dinamicos')
            
            self.db.commit()
            self.db.refresh(oferta_obj)
            
            logger.info(f"Concepto cambiado para oferta {oferta}: {concepto_actual} → {nuevo_concepto}")
            return oferta_obj, concepto_actual
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error al cambiar concepto: {e}")
            return None, None

    def restaurar_concepto_anterior(self, oferta: str) -> Optional[EnlistmentManager]:
        """
        Restaura el concepto anterior de una oferta.
        
        Args:
            oferta: Número de oferta
            
        Returns:
            Oferta actualizada o None en caso de error
        """
        try:
            oferta_obj = self.get_oferta_by_numero(oferta)
            if not oferta_obj:
                return None
            
            # Obtener concepto anterior
            concepto_anterior = oferta_obj.campos_dinamicos.get('concepto_anterior')
            
            if not concepto_anterior:
                logger.warning(f"Oferta {oferta} no tiene concepto_anterior guardado")
                return None
            
            # Restaurar concepto
            concepto_actual = oferta_obj.campos_dinamicos.get('concepto')
            oferta_obj.campos_dinamicos['concepto'] = concepto_anterior
            
            # Limpiar concepto_anterior
            oferta_obj.campos_dinamicos.pop('concepto_anterior', None)
            
            # Marcar como modificado
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(oferta_obj, 'campos_dinamicos')
            
            self.db.commit()
            self.db.refresh(oferta_obj)
            
            logger.info(f"Concepto restaurado para oferta {oferta}: {concepto_actual} → {concepto_anterior}")
            return oferta_obj
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error al restaurar concepto anterior: {e}")
            return None

    def gestionar_oferta_concepto_especial(
        self,
        oferta: str,
        concepto: str,
        estado_nuevo: str,
        usuario_data: Dict[str, Any],
        accion_id: str,
        subaccion_id: str,
        observacion: Optional[str]
    ) -> tuple[Optional[EnlistmentManager], Optional[str]]:
        """
        Gestiona una oferta con concepto especial (MALO o RFS).
        
        Args:
            oferta: Número de oferta
            concepto: Concepto especial (MALO o RFS)
            estado_nuevo: Estado al que cambiará (usualmente CERRADO)
            usuario_data: Datos del usuario que gestiona
            accion_id: ID de la acción
            subaccion_id: ID de la subacción
            observacion: Observaciones opcionales
            
        Returns:
            Tupla (oferta_gestionada, mensaje_error)
        """
        try:
            oferta_obj = self.get_oferta_by_numero(oferta)
            
            if not oferta_obj:
                return None, "Oferta no encontrada"
            
            # Validar que esté EN_TRAMITE
            if oferta_obj.estado_oferta != 'EN_TRAMITE':
                return None, f"La oferta debe estar en estado EN_TRAMITE (actual: {oferta_obj.estado_oferta})"
            
            # Validar que esté asignada al usuario actual
            if oferta_obj.usuario_asignado_login != usuario_data['login']:
                return None, "Esta oferta no está asignada a ti"
            
            estado_anterior = oferta_obj.estado_oferta
            
            # Cambiar concepto y guardar anterior
            oferta_actualizada, concepto_anterior = self.cambiar_concepto_y_guardar_anterior(
                oferta, 
                concepto
            )
            
            if not oferta_actualizada:
                return None, "Error al cambiar concepto"
            
            # Cambiar estado
            oferta_actualizada.estado_oferta = estado_nuevo
            oferta_actualizada.fecha_gestion = get_bogota_now()
            
            self.db.commit()
            self.db.refresh(oferta_actualizada)
            
            # Crear detalle de gestión
            self.create_gestion_detalle({
                'oferta': oferta,
                'accion_id': accion_id,
                'subaccion_id': subaccion_id,
                'observacion': observacion,
                'usuario_login': usuario_data['login'],
                'usuario_nombre': usuario_data['nombre'],
                'usuario_profile_id': usuario_data['profile_id']
            })
            
            # Registrar en histórico de estados
            self.create_historico_estado({
                'oferta': oferta,
                'accion_sistema': 'GESTIONAR',
                'estado_anterior': estado_anterior,
                'estado_nuevo': estado_nuevo,
                'usuario_login': usuario_data['login'],
                'usuario_nombre': usuario_data['nombre'],
                'usuario_profile_id': usuario_data['profile_id'],
                'motivo': f"Concepto: {concepto}",
                'ip_address': usuario_data.get('ip_address')
            })
            
            # Registrar en histórico de enlistment
            campos_modificados = {
                "concepto": {"old": concepto_anterior, "new": concepto},
                "estado_oferta": {"old": estado_anterior, "new": estado_nuevo}
            }
            self.enlistment_repo.create_manual_history_record(
                oferta_actualizada, 
                campos_modificados,
                f"GESTION_{concepto}"
            )
            
            logger.info(f"Oferta {oferta} gestionada con concepto {concepto}")
            return oferta_actualizada, None
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error al gestionar oferta con concepto especial: {e}")
            return None, f"Error interno: {str(e)}"

    def liberar_oferta_concepto_especial(
        self,
        oferta: str,
        concepto_esperado: str,
        supervisor_data: Dict[str, Any],
        motivo: Optional[str] = None
    ) -> tuple[Optional[EnlistmentManager], Optional[str]]:
        """
        Libera una oferta en concepto especial (MALO o RFS).
        Solo para supervisores y superusers.
        
        Args:
            oferta: Número de oferta
            concepto_esperado: Concepto que se espera liberar (MALO o RFS)
            supervisor_data: Datos del supervisor
            motivo: Motivo de la liberación
            
        Returns:
            Tupla (oferta_liberada, mensaje_error)
        """
        try:
            oferta_obj = self.get_oferta_by_numero(oferta)
            
            if not oferta_obj:
                return None, "Oferta no encontrada"
            
            # Validar que esté CERRADO
            if oferta_obj.estado_oferta != 'CERRADO':
                return None, f"La oferta debe estar en estado CERRADO (actual: {oferta_obj.estado_oferta})"
            
            # Validar que esté en el concepto esperado
            concepto_actual = oferta_obj.campos_dinamicos.get('concepto', '')
            if concepto_actual != concepto_esperado:
                return None, f"La oferta no está en concepto {concepto_esperado} (actual: {concepto_actual})"
            
            estado_anterior = oferta_obj.estado_oferta
            
            # Restaurar concepto anterior
            oferta_actualizada = self.restaurar_concepto_anterior(oferta)
            
            if not oferta_actualizada:
                return None, "Error al restaurar concepto anterior"
            
            # Cambiar estado a ABIERTO
            oferta_actualizada.estado_oferta = 'ABIERTO'
            oferta_actualizada.usuario_asignado_login = None
            oferta_actualizada.usuario_asignado_nombre = None
            oferta_actualizada.usuario_asignado_profile_id = None
            oferta_actualizada.fecha_asignacion = None
            oferta_actualizada.fecha_gestion = None
            
            self.db.commit()
            self.db.refresh(oferta_actualizada)
            
            # Registrar en histórico
            self.create_historico_estado({
                'oferta': oferta,
                'accion_sistema': f'LIBERAR_{concepto_esperado}',
                'estado_anterior': estado_anterior,
                'estado_nuevo': 'ABIERTO',
                'usuario_login': supervisor_data['login'],
                'usuario_nombre': supervisor_data['nombre'],
                'usuario_profile_id': supervisor_data['profile_id'],
                'motivo': motivo or f"Liberación de concepto {concepto_esperado}",
                'ip_address': supervisor_data.get('ip_address')
            })
            
            # Registrar en histórico de enlistment
            campos_modificados = {
                "concepto": {"old": concepto_esperado, "new": oferta_actualizada.campos_dinamicos.get('concepto')},
                "estado_oferta": {"old": estado_anterior, "new": "ABIERTO"}
            }
            self.enlistment_repo.create_manual_history_record(
                oferta_actualizada,
                campos_modificados,
                f"LIBERACION_{concepto_esperado}"
            )
            
            logger.info(f"Oferta {oferta} liberada de concepto {concepto_esperado} por {supervisor_data['login']}")
            return oferta_actualizada, None
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error al liberar oferta de concepto especial: {e}")
            return None, f"Error interno: {str(e)}"

    # ==========================================
    # CONFIGURACIÓN GLOBAL AVANZADA
    # ==========================================

    def get_configuracion_global_avanzada(self) -> Optional[OfertaConfiguracionAvanzada]:
        """
        Obtiene la configuración GLOBAL activa.
        Solo debe existir UN registro activo.
        """
        try:
            return self.db.query(OfertaConfiguracionAvanzada).filter(
                OfertaConfiguracionAvanzada.is_active == True
            ).first()
        except Exception as e:
            logger.error(f"Error al obtener configuración global: {e}")
            return None

    def update_configuracion_global_avanzada(
        self, 
        data: Dict[str, Any]
    ) -> Optional[OfertaConfiguracionAvanzada]:
        """
        Actualiza la configuración GLOBAL.
        Si no existe, la crea.
        Registra en historial de auditoría.
        """
        try:
            import json
            config = self.get_configuracion_global_avanzada()
            
            if config:
                # UPDATE - Guardar estado anterior
                config_anterior = {
                    'nombre_config': config.nombre_config,
                    'campo_orden': config.campo_orden,
                    'direccion_orden': config.direccion_orden,
                    'filtro_conceptos_tipo': config.filtro_conceptos_tipo,
                    'conceptos_seleccionados': config.conceptos_seleccionados,
                    'filtro_tipo_trabajo': config.filtro_tipo_trabajo,
                    'filtro_regional_tipo': config.filtro_regional_tipo,
                    'regionales_seleccionadas': config.regionales_seleccionadas,
                    'descripcion': config.descripcion
                }
                
                # Aplicar cambios
                config.nombre_config = data.get('nombre_config', config.nombre_config)
                config.campo_orden = data.get('campo_orden', config.campo_orden)
                config.direccion_orden = data.get('direccion_orden', config.direccion_orden)
                config.filtro_conceptos_tipo = data.get('filtro_conceptos_tipo', config.filtro_conceptos_tipo)
                
                # Convertir lista a JSON string
                conceptos = data.get('conceptos_seleccionados', [])
                config.conceptos_seleccionados = json.dumps(conceptos) if isinstance(conceptos, list) else conceptos
                
                config.filtro_tipo_trabajo = data.get('filtro_tipo_trabajo', config.filtro_tipo_trabajo)
                config.filtro_regional_tipo = data.get('filtro_regional_tipo', config.filtro_regional_tipo)
                
                regionales = data.get('regionales_seleccionadas', [])
                config.regionales_seleccionadas = json.dumps(regionales) if isinstance(regionales, list) else regionales
                
                config.descripcion = data.get('descripcion', config.descripcion)
                config.updated_by = data.get('updated_by')
                
                self.db.commit()
                self.db.refresh(config)
                
                # Detectar cambios
                cambios = {}
                for key in config_anterior:
                    old_val = config_anterior[key]
                    new_val = getattr(config, key)
                    if old_val != new_val:
                        cambios[key] = {'old': old_val, 'new': new_val}
                
                # Registrar en historial
                self._crear_historial_configuracion_global(
                    config, 'UPDATE', 
                    data.get('updated_by'),
                    cambios,
                    data.get('ip_address')
                )
                
                logger.info(f"✅ Configuración global actualizada por {data.get('updated_by')}")
                
            else:
                # CREATE - Primera configuración
                conceptos = data.get('conceptos_seleccionados', [])
                regionales = data.get('regionales_seleccionadas', [])
                
                config = OfertaConfiguracionAvanzada(
                    nombre_config=data.get('nombre_config', 'Configuración Global'),
                    campo_orden=data.get('campo_orden', 'created_at'),
                    direccion_orden=data.get('direccion_orden', 'ASC'),
                    filtro_conceptos_tipo=data.get('filtro_conceptos_tipo', 'TODOS'),
                    conceptos_seleccionados=json.dumps(conceptos) if isinstance(conceptos, list) else conceptos,
                    filtro_tipo_trabajo=data.get('filtro_tipo_trabajo', 'TODOS'),
                    filtro_regional_tipo=data.get('filtro_regional_tipo', 'TODOS'),
                    regionales_seleccionadas=json.dumps(regionales) if isinstance(regionales, list) else regionales,
                    descripcion=data.get('descripcion'),
                    updated_by=data.get('updated_by')
                )
                self.db.add(config)
                self.db.commit()
                self.db.refresh(config)
                
                # Registrar en historial
                self._crear_historial_configuracion_global(
                    config, 'CREATE', 
                    data.get('updated_by'),
                    None,
                    data.get('ip_address')
                )
                
                logger.info(f"✅ Configuración global creada por {data.get('updated_by')}")
            
            return config
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ Error al guardar configuración global: {e}")
            return None

    def _crear_historial_configuracion_global(
        self,
        config: OfertaConfiguracionAvanzada,
        accion: str,
        changed_by: Optional[str],
        cambios_detalle: Optional[Dict],
        ip_address: Optional[str]
    ):
        """Crea registro en historial de configuración GLOBAL"""
        try:
            import json
            historial = OfertaConfiguracionAvanzadaHistory(
                configuracion_id=config.id,
                nombre_config=config.nombre_config,
                campo_orden=config.campo_orden,
                direccion_orden=config.direccion_orden,
                filtro_conceptos_tipo=config.filtro_conceptos_tipo,
                conceptos_seleccionados=config.conceptos_seleccionados,
                filtro_tipo_trabajo=config.filtro_tipo_trabajo,
                filtro_regional_tipo=config.filtro_regional_tipo,
                regionales_seleccionadas=config.regionales_seleccionadas,
                descripcion=config.descripcion,
                accion=accion,
                changed_by=changed_by,
                cambios_detalle=json.dumps(cambios_detalle) if cambios_detalle else None,
                ip_address=ip_address
            )
            self.db.add(historial)
            self.db.commit()
            logger.info(f"📝 Historial registrado: {accion} por {changed_by}")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error al crear historial de configuración: {e}")

    def get_historial_configuracion_global(self) -> List[OfertaConfiguracionAvanzadaHistory]:
        """Obtiene historial completo de cambios de configuración GLOBAL"""
        try:
            return self.db.query(OfertaConfiguracionAvanzadaHistory).order_by(
                desc(OfertaConfiguracionAvanzadaHistory.changed_at)
            ).all()
        except Exception as e:
            logger.error(f"Error al obtener historial: {e}")
            return []

    def get_conceptos_disponibles_sistema(self) -> List[Tuple[str, int]]:
        """
        Lista TODOS los conceptos disponibles en el sistema (para configuración).
        Excluye CONCEPTOS_ANULACION.
        No aplica filtros de configuración.
        
        Returns:
            Lista de tuplas (concepto, cantidad)
        """
        try:
            query = self.db.query(
                EnlistmentManager.campos_dinamicos['concepto'].astext.label('concepto'),
                func.count(EnlistmentManager.id).label('cantidad')
            ).filter(
                and_(
                    EnlistmentManager.estado_oferta == 'ABIERTO',
                    func.upper(func.trim(
                        EnlistmentManager.campos_dinamicos['concepto'].astext
                    )).notin_(CONCEPTOS_ANULACION),
                    EnlistmentManager.campos_dinamicos['concepto'].astext.isnot(None),
                    EnlistmentManager.campos_dinamicos['concepto'].astext != ''
                )
            ).group_by(
                EnlistmentManager.campos_dinamicos['concepto'].astext
            ).order_by(
                EnlistmentManager.campos_dinamicos['concepto'].astext
            ).all()
            
            logger.info(f"📊 Conceptos sistema: {len(query)}")
            return query
        except Exception as e:
            logger.error(f"Error al obtener conceptos sistema: {e}")
            return []

    def get_conceptos_disponibles_segun_config_global(self) -> List[Tuple[str, int]]:
        """
        Lista conceptos disponibles según configuración GLOBAL.
        
        Aplica TODOS los filtros configurados:
        - Filtro de conceptos (TODOS o ESPECIFICOS)
        - Filtro de tipo de trabajo (TODOS, NUEVO, CAMBIO)
        - Filtro de regional (TODOS o ESPECIFICAS)
        
        Returns:
            Lista de tuplas (concepto, cantidad) ordenadas por concepto
        """
        try:
            # Obtener configuración GLOBAL
            config = self.get_configuracion_global_avanzada()
            
            if not config:
                logger.warning("⚠️ No hay configuración GLOBAL, usando filtros por defecto")
                return self.get_conceptos_disponibles_sistema()
            
            # Query base: ofertas ABIERTAS
            query = self.db.query(
                EnlistmentManager.campos_dinamicos['concepto'].astext.label('concepto'),
                func.count(EnlistmentManager.id).label('cantidad')
            ).filter(
                EnlistmentManager.estado_oferta == 'ABIERTO'
            )
            
            # Aplicar TODOS los filtros de configuración
            query = self._aplicar_filtro_conceptos(query, config, concepto_especifico=None)
            query = self._aplicar_filtro_tipo_trabajo(query, config)
            query = self._aplicar_filtro_regional(query, config)
            
            # Agrupar y ordenar por concepto
            query = query.group_by(
                EnlistmentManager.campos_dinamicos['concepto'].astext
            ).order_by(
                EnlistmentManager.campos_dinamicos['concepto'].astext
            )
            
            resultado = query.all()
            
            logger.info(f"📊 Conceptos disponibles según config GLOBAL (con todos los filtros): {len(resultado)}")
            return resultado
            
        except Exception as e:
            logger.error(f"Error al obtener conceptos según config: {e}")
            return []

    def get_regionales_disponibles(self) -> List[str]:
        """
        Lista todas las regionales únicas en ofertas ABIERTAS.
        NULL se convierte en 'DEFAULT'.
        
        Returns:
            Lista de regionales ordenadas alfabéticamente
        """
        try:
            query = self.db.query(
                func.coalesce(
                    EnlistmentManager.campos_dinamicos['regional'].astext,
                    'DEFAULT'
                ).label('regional')
            ).filter(
                EnlistmentManager.estado_oferta == 'ABIERTO'
            ).distinct().order_by('regional')
            
            regionales = [r.regional for r in query.all()]
            logger.info(f"📊 Regionales disponibles: {len(regionales)}")
            return regionales
        except Exception as e:
            logger.error(f"Error al obtener regionales: {e}")
            return []

    def _aplicar_filtro_conceptos(
        self, 
        query, 
        config, 
        concepto_especifico: Optional[str] = None
    ):
        """Aplica filtro de conceptos según configuración GLOBAL.

        Si concepto_especifico viene informado, se respeta la solicitud manual
        sin aplicar exclusiones adicionales de aleatorio.
        """
        import json
        
        # Excluir conceptos de anulación (siempre)
        query = query.filter(
            func.upper(func.trim(
                EnlistmentManager.campos_dinamicos['concepto'].astext
            )).notin_(CONCEPTOS_ANULACION),
            EnlistmentManager.campos_dinamicos['concepto'].astext.isnot(None),
            EnlistmentManager.campos_dinamicos['concepto'].astext != ''
        )
        
        # Si se solicita concepto específico, tiene prioridad
        if concepto_especifico:
            query = query.filter(
                func.upper(func.trim(
                    EnlistmentManager.campos_dinamicos['concepto'].astext
                )) == concepto_especifico.strip().upper()
            )
            return query
        
        # Aplicar filtro de configuración GLOBAL
        if config.filtro_conceptos_tipo == 'ESPECIFICOS':
            conceptos_seleccionados = json.loads(config.conceptos_seleccionados) if isinstance(config.conceptos_seleccionados, str) else config.conceptos_seleccionados
            if conceptos_seleccionados:
                conceptos_upper = [c.strip().upper() for c in conceptos_seleccionados]
                query = query.filter(
                    func.upper(func.trim(
                        EnlistmentManager.campos_dinamicos['concepto'].astext
                    )).in_(conceptos_upper)
                )
                logger.debug(f"📋 Filtro conceptos ESPECIFICOS: {conceptos_upper}")
        
        return query

    def _aplicar_filtro_tipo_trabajo(self, query, config):
        """Aplica filtro de tipo trabajo según configuración GLOBAL"""
        
        if config.filtro_tipo_trabajo == 'TODOS':
            return query
        
        # Mapeo de tipo_trabajo a categoría
        if config.filtro_tipo_trabajo == 'NUEVO':
            # NULL o 'NA Nuevo'
            query = query.filter(
                or_(
                    EnlistmentManager.campos_dinamicos['tipo_trabajo'].astext.is_(None),
                    func.upper(func.trim(
                        EnlistmentManager.campos_dinamicos['tipo_trabajo'].astext
                    )).like('%NA NUEVO%')
                )
            )
            logger.debug("📋 Filtro tipo trabajo: NUEVO")
        elif config.filtro_tipo_trabajo == 'CAMBIO':
            # Cambio de domicilio, Modificación, Cambio suscriptor
            query = query.filter(
                or_(
                    func.upper(func.trim(
                        EnlistmentManager.campos_dinamicos['tipo_trabajo'].astext
                    )).like('%CAMBIO DE DOMICILIO%'),
                    func.upper(func.trim(
                        EnlistmentManager.campos_dinamicos['tipo_trabajo'].astext
                    )).like('%MODIFICACIÓN%'),
                    func.upper(func.trim(
                        EnlistmentManager.campos_dinamicos['tipo_trabajo'].astext
                    )).like('%CAMBIO SUSCRIPTOR%')
                )
            )
            logger.debug("📋 Filtro tipo trabajo: CAMBIO")
        
        return query

    def _aplicar_filtro_regional(self, query, config):
        """Aplica filtro de regional según configuración GLOBAL"""
        import json
        
        if config.filtro_regional_tipo == 'TODOS':
            return query
        
        if config.filtro_regional_tipo == 'ESPECIFICAS':
            regionales_seleccionadas = json.loads(config.regionales_seleccionadas) if isinstance(config.regionales_seleccionadas, str) else config.regionales_seleccionadas
            if regionales_seleccionadas:
                # Manejar NULL como 'DEFAULT'
                regionales = regionales_seleccionadas.copy()
                
                if 'DEFAULT' in regionales:
                    regionales.remove('DEFAULT')
                    # Incluir NULL o las regionales específicas
                    if regionales:
                        query = query.filter(
                            or_(
                                EnlistmentManager.campos_dinamicos['regional'].astext.is_(None),
                                func.upper(func.trim(
                                    EnlistmentManager.campos_dinamicos['regional'].astext
                                )).in_([r.strip().upper() for r in regionales])
                            )
                        )
                    else:
                        # Solo DEFAULT (NULL)
                        query = query.filter(
                            EnlistmentManager.campos_dinamicos['regional'].astext.is_(None)
                        )
                else:
                    # Solo regionales específicas
                    query = query.filter(
                        func.upper(func.trim(
                            EnlistmentManager.campos_dinamicos['regional'].astext
                        )).in_([r.strip().upper() for r in regionales])
                    )
                
                logger.debug(f"📋 Filtro regionales: {regionales_seleccionadas}")
        
        return query

    def _aplicar_ordenamiento(self, query, config):
        """Aplica ordenamiento según configuración GLOBAL"""
        
        if config.campo_orden == 'fecha_creado':
            # Ordenar por campos_dinamicos->>'fecha_creado'
            campo_orden = EnlistmentManager.campos_dinamicos['fecha_creado'].astext
        else:
            # Ordenar por created_at (defecto)
            campo_orden = EnlistmentManager.created_at
        
        if config.direccion_orden == 'DESC':
            query = query.order_by(desc(campo_orden))
            logger.debug(f"📋 Ordenamiento: {config.campo_orden} DESC")
        else:
            query = query.order_by(asc(campo_orden))
            logger.debug(f"📋 Ordenamiento: {config.campo_orden} ASC")
        
        return query
