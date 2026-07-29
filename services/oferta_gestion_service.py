import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from zoneinfo import ZoneInfo
from sqlalchemy.orm import Session
from app.repositories.oferta_gestion_repository import OfertaGestionRepository
from app.repositories.user_repository import UserRepository
from app.db.timezone_types import get_bogota_now

logger = logging.getLogger("oferta_gestion_service")


class OfertaGestionService:
    """
    Servicio para gestión de ofertas.
    Implementa toda la lógica de negocio y validaciones.
    """

    def __init__(self, db: Session):
        """Inicializa el service con la sesión de base de datos.
        
        Args:
            db: Sesión de SQLAlchemy inyectada por dependency
        """
        self.db = db
        self.repository = OfertaGestionRepository(db)
        self.user_repository = UserRepository(db)

    # ==========================================
    # CATÁLOGOS
    # ==========================================

    def get_all_acciones_con_subacciones(self) -> List[Dict[str, Any]]:
        """Obtiene todas las acciones con sus subacciones"""
        try:
            acciones = self.repository.get_all_acciones()
            resultado = []
            
            for accion in acciones:
                subacciones = self.repository.get_subacciones_by_accion(str(accion.id))
                resultado.append({
                    'id': str(accion.id),
                    'nombre': accion.nombre_accion,
                    'descripcion': accion.descripcion,
                    'is_active': accion.is_active,
                    'orden': accion.orden,
                    'subacciones': [
                        {
                            'id': str(sub.id),
                            'accion_id': str(sub.accion_id),
                            'nombre': sub.nombre_subaccion,
                            'is_active': sub.is_active,
                            'orden': sub.orden,
                            'created_at': sub.created_at,
                            'updated_at': sub.updated_at
                        }
                        for sub in subacciones
                    ]
                })
            
            return resultado
        except Exception as e:
            logger.error(f"Error al obtener acciones con subacciones: {e}")
            return []

    def create_accion(self, nombre: str, descripcion: Optional[str] = None, orden: int = 0) -> Optional[Dict[str, Any]]:
        """Crea una nueva acción"""
        try:
            accion = self.repository.create_accion({
                'nombre': nombre,
                'descripcion': descripcion,
                'orden': orden
            })
            
            if not accion:
                return None
            
            return {
                'id': str(accion.id),
                'nombre': accion.nombre_accion,
                'descripcion': accion.descripcion,
                'is_active': accion.is_active,
                'orden': accion.orden
            }
        except Exception as e:
            logger.error(f"Error al crear acción: {e}")
            return None

    def update_accion(self, accion_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Actualiza una acción"""
        try:
            # Mapear campos del request al modelo
            update_data = {}
            if 'nombre' in data:
                update_data['nombre_accion'] = data['nombre']
            if 'descripcion' in data:
                update_data['descripcion'] = data['descripcion']
            if 'orden' in data:
                update_data['orden'] = data['orden']
            if 'is_active' in data:
                update_data['is_active'] = data['is_active']
            
            accion = self.repository.update_accion(accion_id, update_data)
            
            if not accion:
                return None
            
            return {
                'id': str(accion.id),
                'nombre': accion.nombre_accion,
                'descripcion': accion.descripcion,
                'is_active': accion.is_active,
                'orden': accion.orden
            }
        except Exception as e:
            logger.error(f"Error al actualizar acción: {e}")
            return None

    def delete_accion(self, accion_id: str) -> bool:
        """Elimina (desactiva) una acción"""
        return self.repository.delete_accion(accion_id)

    def create_subaccion(self, accion_id: str, nombre: str, orden: int = 0) -> Optional[Dict[str, Any]]:
        """Crea una nueva subacción"""
        try:
            # Validar que la acción exista
            accion = self.repository.get_accion_by_id(accion_id)
            if not accion:
                logger.error(f"Acción {accion_id} no encontrada")
                return None
            
            subaccion = self.repository.create_subaccion({
                'accion_id': accion_id,
                'nombre': nombre,
                'orden': orden
            })
            
            if not subaccion:
                return None
            
            return {
                'id': str(subaccion.id),
                'accion_id': str(subaccion.accion_id),
                'nombre': subaccion.nombre_subaccion,
                'is_active': subaccion.is_active,
                'orden': subaccion.orden,
                'created_at': subaccion.created_at,
                'updated_at': subaccion.updated_at
            }
        except Exception as e:
            logger.error(f"Error al crear subacción: {e}")
            return None

    def update_subaccion(self, subaccion_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Actualiza una subacción"""
        try:
            # Mapear campos
            update_data = {}
            if 'nombre' in data:
                update_data['nombre_subaccion'] = data['nombre']
            if 'orden' in data:
                update_data['orden'] = data['orden']
            if 'is_active' in data:
                update_data['is_active'] = data['is_active']
            
            subaccion = self.repository.update_subaccion(subaccion_id, update_data)
            
            if not subaccion:
                return None
            
            return {
                'id': str(subaccion.id),
                'accion_id': str(subaccion.accion_id),
                'nombre': subaccion.nombre_subaccion,
                'is_active': subaccion.is_active,
                'orden': subaccion.orden,
                'created_at': subaccion.created_at,
                'updated_at': subaccion.updated_at
            }
        except Exception as e:
            logger.error(f"Error al actualizar subacción: {e}")
            return None

    def delete_subaccion(self, subaccion_id: str) -> bool:
        """Elimina (desactiva) una subacción"""
        return self.repository.delete_subaccion(subaccion_id)
    
    # ==========================================
    # CONCEPTOS DE OFERTAS
    # ==========================================
    
    def get_conceptos_with_count(self):
        """Obtiene todos los conceptos y la cantidad disponible en estado ABIERTO de enlistment_manager"""
        try:
            # Obtener datos del repositorio
            conceptos_data = self.repository.get_conceptos_with_count()
            
            # Transformar a formato de respuesta
            resultado = []
            for concepto, cantidad in conceptos_data:
                resultado.append({
                    'concepto': concepto,
                    'cantidad': cantidad
                })
            
            logger.info(f"Obtenidos {len(resultado)} conceptos distintos con ofertas en estado ABIERTO")
            return resultado
            
        except Exception as e:
            logger.error(f"Error al obtener conceptos con count: {e}")
            return []

    # ==========================================
    # GESTIÓN DE OFERTAS
    # ==========================================

    def congelar_oferta(self, usuario_data: Dict[str, Any], oferta_numero: Optional[str] = None, concepto: Optional[str] = None) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Congela una oferta para un usuario.
        - Si se proporciona oferta_numero: busca y congela esa oferta específica (ignora concepto)
        - Si NO se proporciona oferta_numero: busca según configuración GLOBAL (con concepto opcional)
        Retorna: (datos_oferta, mensaje_error)
        """
        try:
            usuario_login = usuario_data['login']
            profile_id = usuario_data['profile_id']
            
            # Validar que el usuario NO tenga ya una oferta EN_TRAMITE
            oferta_actual = self.repository.get_oferta_en_tramite_by_usuario(usuario_login)
            if oferta_actual:
                logger.warning(f"Usuario {usuario_login} ya tiene oferta en trámite: {oferta_actual.oferta}")
                return None, f"Ya tienes una oferta en trámite: {oferta_actual.oferta}"
            
            # Lógica de búsqueda según parámetros
            if oferta_numero:
                # Buscar oferta específica por número
                oferta = self.repository.get_oferta_by_numero(oferta_numero)
                
                if not oferta:
                    logger.warning(f"Oferta {oferta_numero} no encontrada")
                    return None, f"Oferta {oferta_numero} no encontrada"
                
                if oferta.estado_oferta != 'ABIERTO':
                    logger.warning(f"Oferta {oferta_numero} no está disponible (estado: {oferta.estado_oferta})")
                    return None, f"La oferta {oferta_numero} no está disponible (estado actual: {oferta.estado_oferta})"
                
                logger.info(f"Oferta específica {oferta_numero} encontrada y disponible para {usuario_login}")
            else:
                # Buscar oferta disponible según configuración GLOBAL (sin profile_id)
                oferta = self.repository.get_oferta_disponible(concepto=concepto)
                
                if not oferta:
                    if concepto:
                        logger.info(f"No hay ofertas disponibles del concepto '{concepto}' para {usuario_login}")
                        return None, f"No hay ofertas disponibles del concepto '{concepto}' según la configuración actual"
                    else:
                        logger.info(f"No hay ofertas disponibles para {usuario_login}")
                        return None, "No hay ofertas disponibles según la configuración actual"
            
            estado_anterior = oferta.estado_oferta
            
            # Congelar la oferta
            oferta_congelada = self.repository.congelar_oferta(str(oferta.id), usuario_data)
            
            if not oferta_congelada:
                return None, "Error al congelar la oferta"
            
            # Registrar en histórico
            self.repository.create_historico_estado({
                'oferta': oferta_congelada.oferta,
                'accion_sistema': 'CONGELAR',
                'estado_anterior': estado_anterior,
                'estado_nuevo': 'EN_TRAMITE',
                'usuario_login': usuario_login,
                'usuario_nombre': usuario_data['nombre'],
                'usuario_profile_id': profile_id,
                'ip_address': usuario_data.get('ip_address')
            })
            
            logger.info(f"Oferta {oferta_congelada.oferta} congelada para {usuario_login}")
            
            return {
                'oferta': oferta_congelada.oferta,
                'estado': oferta_congelada.estado_oferta,
                'usuario_asignado': oferta_congelada.usuario_asignado_login,
                'usuario_nombre': oferta_congelada.usuario_asignado_nombre,
                'fecha_asignacion': oferta_congelada.fecha_asignacion.astimezone(ZoneInfo("America/Bogota")),
                'campos_dinamicos': oferta_congelada.campos_dinamicos
            }, None
            
        except Exception as e:
            logger.error(f"Error al congelar oferta: {e}")
            return None, f"Error interno: {str(e)}"

    def get_mi_oferta(self, usuario_login: str) -> Optional[Dict[str, Any]]:
        """Obtiene la oferta actual del usuario"""
        try:
            oferta = self.repository.get_oferta_en_tramite_by_usuario(usuario_login)
            
            if not oferta:
                return None
            
            # Calcular tiempo transcurrido
            tiempo_transcurrido = 0
            if oferta.fecha_asignacion:
                delta = datetime.now().astimezone(ZoneInfo("America/Bogota")) - oferta.fecha_asignacion.astimezone(ZoneInfo("America/Bogota"))
                tiempo_transcurrido = int(delta.total_seconds() / 60)
            
            return {
                'oferta': oferta.oferta,
                'estado': oferta.estado_oferta,
                'fecha_asignacion': oferta.fecha_asignacion.astimezone(ZoneInfo("America/Bogota")),
                'tiempo_transcurrido_minutos': tiempo_transcurrido,
                'campos_dinamicos': oferta.campos_dinamicos
            }
        except Exception as e:
            logger.error(f"Error al obtener mi oferta: {e}")
            return None

    def gestionar_oferta(
        self, 
        oferta_numero: str,
        accion_id: str,
        subaccion_id: str,
        observacion: Optional[str],
        usuario_data: Dict[str, Any]
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Gestiona (cierra) una oferta con acción y subacción.
        Detecta automáticamente si es un concepto especial (MALO o RFS).
        Retorna: (datos_gestion, mensaje_error)
        """
        try:
            usuario_login = usuario_data['login']
            
            # Obtener la oferta
            oferta = self.repository.get_oferta_by_numero(oferta_numero)
            
            if not oferta:
                return None, "Oferta no encontrada"
            
            # Validar que esté EN_TRAMITE
            if oferta.estado_oferta != 'EN_TRAMITE':
                return None, f"La oferta debe estar en estado EN_TRAMITE (actual: {oferta.estado_oferta})"
            
            # Validar que esté asignada al usuario actual
            if oferta.usuario_asignado_login != usuario_login:
                return None, "Esta oferta no está asignada a ti"
            
            # Validar que la acción exista
            accion = self.repository.get_accion_by_id(accion_id)
            if not accion:
                return None, "Acción no encontrada"
            
            # Validar que la subacción exista
            subaccion = self.repository.get_subaccion_by_id(subaccion_id)
            if not subaccion:
                return None, "Subacción no encontrada"
            
            # Validar que la subacción pertenezca a la acción
            if not self.repository.validate_subaccion_belongs_to_accion(subaccion_id, accion_id):
                return None, "La subacción seleccionada no pertenece a la acción indicada"
            
            # ==========================================
            # DETECCIÓN DE CONCEPTOS ESPECIALES
            # ==========================================
            
            # Si es acción MALO, redirigir al método especializado
            if accion.nombre_accion == 'MALO':
                return self.gestionar_oferta_malo(
                    oferta_numero=oferta_numero,
                    accion_id=accion_id,
                    subaccion_id=subaccion_id,
                    observacion=observacion,
                    usuario_data=usuario_data
                )
            
            # Si es acción RFS, redirigir al método especializado
            if accion.nombre_accion == 'RFS':
                return self.gestionar_oferta_rfs(
                    oferta_numero=oferta_numero,
                    accion_id=accion_id,
                    subaccion_id=subaccion_id,
                    observacion=observacion,
                    usuario_data=usuario_data
                )
            
            # ==========================================
            # GESTIÓN NORMAL
            # ==========================================
            
            estado_anterior = oferta.estado_oferta
            
            # Cerrar la oferta
            oferta_cerrada = self.repository.cerrar_oferta(oferta_numero)
            
            if not oferta_cerrada:
                return None, "Error al cerrar la oferta"
            
            # Crear detalle de gestión
            self.repository.create_gestion_detalle({
                'oferta': oferta_numero,
                'accion_id': accion_id,
                'subaccion_id': subaccion_id,
                'observacion': observacion,
                'usuario_login': usuario_login,
                'usuario_nombre': usuario_data['nombre'],
                'usuario_profile_id': usuario_data['profile_id']
            })
            
            # Registrar en histórico
            self.repository.create_historico_estado({
                'oferta': oferta_numero,
                'accion_sistema': 'GESTIONAR',
                'estado_anterior': estado_anterior,
                'estado_nuevo': 'CERRADO',
                'usuario_login': usuario_login,
                'usuario_nombre': usuario_data['nombre'],
                'usuario_profile_id': usuario_data['profile_id'],
                'motivo': f"Acción: {accion.nombre_accion} - Subacción: {subaccion.nombre_subaccion}",
                'ip_address': usuario_data.get('ip_address')
            })
            
            logger.info(f"Oferta {oferta_numero} gestionada por {usuario_login}")
            
            return {
                'oferta': oferta_numero,
                'estado': 'CERRADO',
                'accion': accion.nombre_accion,
                'subaccion': subaccion.nombre_subaccion,
                'fecha_gestion': oferta_cerrada.fecha_gestion.astimezone(ZoneInfo("America/Bogota"))
            }, None
            
        except Exception as e:
            logger.error(f"Error al gestionar oferta: {e}")
            return None, f"Error interno: {str(e)}"

    def descongelar_oferta(
        self, 
        oferta_numero: str,
        motivo: Optional[str],
        supervisor_data: Dict[str, Any]
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Descongela una oferta (solo Supervisor/SuperUser).
        Retorna: (datos_resultado, mensaje_error)
        """
        try:
            # Obtener la oferta
            oferta = self.repository.get_oferta_by_numero(oferta_numero)
            
            if not oferta:
                return None, "Oferta no encontrada"
            
            # Validar que esté EN_TRAMITE
            if oferta.estado_oferta != 'EN_TRAMITE':
                return None, f"La oferta debe estar en estado EN_TRAMITE (actual: {oferta.estado_oferta})"
            
            asesor_anterior = oferta.usuario_asignado_login
            estado_anterior = oferta.estado_oferta
            
            # Descongelar
            oferta_descongelada = self.repository.descongelar_oferta(oferta_numero)
            
            if not oferta_descongelada:
                return None, "Error al descongelar la oferta"
            
            # Registrar en histórico
            self.repository.create_historico_estado({
                'oferta': oferta_numero,
                'accion_sistema': 'DESCONGELAR',
                'estado_anterior': estado_anterior,
                'estado_nuevo': 'ABIERTO',
                'usuario_login': supervisor_data['login'],
                'usuario_nombre': supervisor_data['nombre'],
                'usuario_profile_id': supervisor_data['profile_id'],
                'asesor_asignado_login': asesor_anterior,
                'motivo': motivo,
                'ip_address': supervisor_data.get('ip_address')
            })
            
            logger.info(f"Oferta {oferta_numero} descongelada por {supervisor_data['login']}")
            
            return {
                'oferta': oferta_numero,
                'estado': 'ABIERTO',
                'asesor_anterior': asesor_anterior,
                'mensaje': 'Oferta liberada correctamente'
            }, None
            
        except Exception as e:
            logger.error(f"Error al descongelar oferta: {e}")
            return None, f"Error interno: {str(e)}"

    def reasignar_oferta(
        self,
        oferta_numero: str,
        asesor_login: str,
        motivo: Optional[str],
        supervisor_data: Dict[str, Any]
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Reasigna una oferta a otro asesor (solo Supervisor/SuperUser).
        Retorna: (datos_resultado, mensaje_error)
        """
        try:
            # Obtener la oferta
            oferta = self.repository.get_oferta_by_numero(oferta_numero)
            
            if not oferta:
                return None, "Oferta no encontrada"
            
            # Validar que esté EN_TRAMITE o ABIERTO
            if oferta.estado_oferta != 'EN_TRAMITE' and oferta.estado_oferta != 'ABIERTO':
                return None, f"La oferta debe estar en estado EN_TRAMITE o ABIERTO (actual: {oferta.estado_oferta})"
            
            # Obtener datos del nuevo asesor
            nuevo_asesor = self.user_repository.get_by_username(asesor_login)
            
            if not nuevo_asesor:
                return None, f"Asesor {asesor_login} no encontrado"
            
            # Validar que sea usuario Regular
            if nuevo_asesor.profile_id != 4:
                return None, "Solo se puede reasignar a usuarios con perfil Regular"
            
            # Validar que el nuevo asesor NO tenga otra oferta EN_TRAMITE
            oferta_existente = self.repository.get_oferta_en_tramite_by_usuario(asesor_login)
            if oferta_existente:
                return None, f"El asesor {asesor_login} ya tiene una oferta en trámite: {oferta_existente.oferta}"
            
            asesor_anterior = oferta.usuario_asignado_login
            
            # Estado antes de reasignar
            oferta_estado_anterior = oferta.estado_oferta
            
            # Reasignar
            oferta_reasignada = self.repository.reasignar_oferta(oferta_numero, {
                'login': nuevo_asesor.login,
                'nombre': nuevo_asesor.full_name,
                'profile_id': nuevo_asesor.profile_id
            })
            
            if not oferta_reasignada:
                return None, "Error al reasignar la oferta"
            
            # Registrar en histórico
            self.repository.create_historico_estado({
                'oferta': oferta_numero,
                'accion_sistema': 'REASIGNAR',
                'estado_anterior': oferta_estado_anterior,
                'estado_nuevo': 'EN_TRAMITE',
                'usuario_login': supervisor_data['login'],
                'usuario_nombre': supervisor_data['nombre'],
                'usuario_profile_id': supervisor_data['profile_id'],
                'asesor_asignado_login': nuevo_asesor.login,
                'asesor_asignado_nombre': nuevo_asesor.full_name,
                'motivo': motivo,
                'ip_address': supervisor_data.get('ip_address')
            })
            
            logger.info(f"Oferta {oferta_numero} reasignada de {asesor_anterior} a {asesor_login}")
            
            return {
                'oferta': oferta_numero,
                'asesor_anterior': asesor_anterior,
                'asesor_nuevo': nuevo_asesor.login,
                'asesor_nuevo_nombre': nuevo_asesor.full_name,
                'reasignado_por': supervisor_data['login'],
                'mensaje': 'Oferta reasignada correctamente'
            }, None
            
        except Exception as e:
            logger.error(f"Error al reasignar oferta: {e}")
            return None, f"Error interno: {str(e)}"

    def get_ofertas_en_tramite(self, page: int = 1, limit: int = 50) -> Dict[str, Any]:
        """Obtiene todas las ofertas EN_TRAMITE (Dashboard Supervisor)"""
        try:
            ofertas, total = self.repository.get_ofertas_en_tramite(page, limit)
            
            data = []
            for oferta in ofertas:
                # Calcular tiempo transcurrido
                tiempo_transcurrido = 0
                if oferta.fecha_asignacion:
                    delta = get_bogota_now() - oferta.fecha_asignacion
                    tiempo_transcurrido = int(delta.total_seconds() / 60)
                
                data.append({
                    'oferta': oferta.oferta,
                    'usuario_asignado': oferta.usuario_asignado_login,
                    'usuario_nombre': oferta.usuario_asignado_nombre,
                    'fecha_asignacion': oferta.fecha_asignacion,
                    'tiempo_transcurrido_minutos': tiempo_transcurrido,
                    'campos_dinamicos': oferta.campos_dinamicos
                })
            
            total_pages = (total + limit - 1) // limit  # Ceiling division
            
            return {
                'data': data,
                'pagination': {
                    'page': page,
                    'limit': limit,
                    'total': total,
                    'total_pages': total_pages
                }
            }
        except Exception as e:
            logger.error(f"Error al obtener ofertas en trámite: {e}")
            return {
                'data': [],
                'pagination': {
                    'page': page,
                    'limit': limit,
                    'total': 0,
                    'total_pages': 0
                }
            }

    # ==========================================
    # HISTÓRICO Y REPORTES
    # ==========================================

    def get_historico_oferta(self, oferta: str) -> List[Dict[str, Any]]:
        """Obtiene el histórico completo de una oferta"""
        try:
            historicos = self.repository.get_historico_by_oferta(oferta)
            
            return [
                {
                    'id': str(h.id),
                    'accion': h.accion_sistema,
                    'estado_anterior': h.estado_anterior,
                    'estado_nuevo': h.estado_nuevo,
                    'usuario': h.usuario_login,
                    'usuario_nombre': h.usuario_nombre,
                    'asesor_asignado': h.asesor_asignado_login,
                    'asesor_asignado_nombre': h.asesor_asignado_nombre,
                    'motivo': h.motivo,
                    'fecha': h.fecha_accion
                }
                for h in historicos
            ]
        except Exception as e:
            logger.error(f"Error al obtener histórico: {e}")
            return []

    def get_gestion_detalle(self, oferta: str) -> Optional[Dict[str, Any]]:
        """Obtiene el detalle de gestión de una oferta"""
        try:
            detalle = self.repository.get_gestion_detalle_by_oferta(oferta)
            
            if not detalle:
                return None
            
            # Obtener nombres de acción y subacción
            accion = self.repository.get_accion_by_id(str(detalle.accion_id))
            subaccion = self.repository.get_subaccion_by_id(str(detalle.subaccion_id))
            
            return {
                'id': str(detalle.id),
                'oferta': detalle.oferta,
                'accion': accion.nombre_accion if accion else 'Desconocida',
                'subaccion': subaccion.nombre_subaccion if subaccion else 'Desconocida',
                'observacion': detalle.observacion,
                'usuario': detalle.usuario_login,
                'usuario_nombre': detalle.usuario_nombre,
                'fecha_gestion': detalle.fecha_gestion
            }
        except Exception as e:
            logger.error(f"Error al obtener detalle de gestión: {e}")
            return None

    def get_productividad_usuario(
        self,
        usuario_login: str,
        fecha_desde: Optional[datetime] = None,
        fecha_hasta: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Obtiene reporte de productividad de un usuario"""
        try:
            # Obtener datos del usuario
            usuario = self.user_repository.get_by_username(usuario_login)
            
            if not usuario:
                return {
                    'error': 'Usuario no encontrado'
                }
            
            stats = self.repository.get_productividad_usuario(usuario_login, fecha_desde, fecha_hasta)
            
            return {
                'usuario': usuario.login,
                'usuario_nombre': usuario.full_name,
                'total_gestionadas': stats['total_gestionadas'],
                'por_accion': stats['por_accion'],
                'tiempo_promedio_gestion_minutos': stats['tiempo_promedio_minutos']
            }
        except Exception as e:
            logger.error(f"Error al obtener productividad: {e}")
            return {
                'error': f'Error interno: {str(e)}'
            }

    # ==========================================
    # CONFIGURACIÓN
    # ==========================================

    def get_configuracion(self, profile_id: int) -> Optional[Dict[str, Any]]:
        """Obtiene la configuración de un perfil"""
        try:
            config = self.repository.get_configuracion_by_profile(profile_id)
            
            if not config:
                return None
            
            return {
                'id': str(config.id),
                'profile_id': config.profile_id,
                'orden_busqueda': config.orden_busqueda,
                'descripcion': config.descripcion,
                'is_active': config.is_active,
                'updated_by': config.updated_by,
                'updated_at': config.updated_at
            }
        except Exception as e:
            logger.error(f"Error al obtener configuración: {e}")
            return None

    def update_configuracion(
        self, 
        profile_id: int, 
        orden_busqueda: str,
        descripcion: Optional[str],
        updated_by: str
    ) -> Optional[Dict[str, Any]]:
        """Actualiza o crea la configuración de un perfil"""
        try:
            config = self.repository.create_or_update_configuracion({
                'profile_id': profile_id,
                'orden_busqueda': orden_busqueda,
                'descripcion': descripcion,
                'updated_by': updated_by
            })
            
            if not config:
                return None
            
            return {
                'id': str(config.id),
                'profile_id': config.profile_id,
                'orden_busqueda': config.orden_busqueda,
                'descripcion': config.descripcion,
                'is_active': config.is_active,
                'updated_by': config.updated_by,
                'updated_at': config.updated_at
            }
        except Exception as e:
            logger.error(f"Error al actualizar configuración: {e}")
            return None

    # ==========================================
    # CONFIGURACIÓN GLOBAL AVANZADA
    # ==========================================

    def get_configuracion_global_avanzada(self) -> Dict[str, Any]:
        """Obtiene la configuración GLOBAL activa"""
        try:
            import json
            config = self.repository.get_configuracion_global_avanzada()
            
            if not config:
                # Retornar configuración por defecto
                return {
                    'nombre_config': 'Configuración Global',
                    'campo_orden': 'created_at',
                    'direccion_orden': 'ASC',
                    'filtro_conceptos_tipo': 'TODOS',
                    'conceptos_seleccionados': [],
                    'filtro_tipo_trabajo': 'TODOS',
                    'filtro_regional_tipo': 'TODOS',
                    'regionales_seleccionadas': [],
                    'descripcion': None,
                    'configurado': False
                }
            
            # Parsear JSON strings a listas
            conceptos = json.loads(config.conceptos_seleccionados) if isinstance(config.conceptos_seleccionados, str) else config.conceptos_seleccionados
            regionales = json.loads(config.regionales_seleccionadas) if isinstance(config.regionales_seleccionadas, str) else config.regionales_seleccionadas
            
            # Calcular si está configurado (al menos un filtro no está en TODOS)
            configurado = (
                config.filtro_conceptos_tipo != 'TODOS' or
                config.filtro_tipo_trabajo != 'TODOS' or
                config.filtro_regional_tipo != 'TODOS'
            )
            
            return {
                'id': str(config.id),
                'nombre_config': config.nombre_config,
                'campo_orden': config.campo_orden,
                'direccion_orden': config.direccion_orden,
                'filtro_conceptos_tipo': config.filtro_conceptos_tipo,
                'conceptos_seleccionados': conceptos or [],
                'filtro_tipo_trabajo': config.filtro_tipo_trabajo,
                'filtro_regional_tipo': config.filtro_regional_tipo,
                'regionales_seleccionadas': regionales or [],
                'descripcion': config.descripcion,
                'is_active': config.is_active,
                'updated_by': config.updated_by,
                'updated_at': config.updated_at,
                'configurado': configurado
            }
        except Exception as e:
            logger.error(f"Error al obtener configuración global: {e}")
            return None

    def update_configuracion_global_avanzada(
        self,
        config_data: Dict[str, Any],
        updated_by: str,
        ip_address: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Actualiza la configuración GLOBAL"""
        try:
            # Validar conceptos si es ESPECIFICOS
            if config_data.get('filtro_conceptos_tipo') == 'ESPECIFICOS':
                conceptos = config_data.get('conceptos_seleccionados', [])
                if not conceptos:
                    logger.error("❌ Filtro ESPECIFICOS requiere al menos un concepto")
                    return None
                
                # Validar que conceptos existan en sistema
                conceptos_sistema = [c[0] for c in self.repository.get_conceptos_disponibles_sistema()]
                for concepto in conceptos:
                    if concepto not in conceptos_sistema:
                        logger.warning(f"⚠️ Concepto '{concepto}' no existe en sistema")
            
            # Validar regionales si es ESPECIFICAS
            if config_data.get('filtro_regional_tipo') == 'ESPECIFICAS':
                regionales = config_data.get('regionales_seleccionadas', [])
                if not regionales:
                    logger.error("❌ Filtro ESPECIFICAS requiere al menos una regional")
                    return None
            
            # Guardar configuración
            data = {
                'nombre_config': config_data.get('nombre_config', 'Configuración Global'),
                'campo_orden': config_data.get('campo_orden', 'created_at'),
                'direccion_orden': config_data.get('direccion_orden', 'ASC'),
                'filtro_conceptos_tipo': config_data.get('filtro_conceptos_tipo', 'TODOS'),
                'conceptos_seleccionados': config_data.get('conceptos_seleccionados', []),
                'filtro_tipo_trabajo': config_data.get('filtro_tipo_trabajo', 'TODOS'),
                'filtro_regional_tipo': config_data.get('filtro_regional_tipo', 'TODOS'),
                'regionales_seleccionadas': config_data.get('regionales_seleccionadas', []),
                'descripcion': config_data.get('descripcion'),
                'updated_by': updated_by,
                'ip_address': ip_address
            }
            
            config = self.repository.update_configuracion_global_avanzada(data)
            
            if not config:
                return None
            
            # Parsear JSON strings a listas para respuesta
            import json
            conceptos = json.loads(config.conceptos_seleccionados) if isinstance(config.conceptos_seleccionados, str) else config.conceptos_seleccionados
            regionales = json.loads(config.regionales_seleccionadas) if isinstance(config.regionales_seleccionadas, str) else config.regionales_seleccionadas
            
            # Calcular si está configurado (al menos un filtro no está en TODOS)
            configurado = (
                config.filtro_conceptos_tipo != 'TODOS' or
                config.filtro_tipo_trabajo != 'TODOS' or
                config.filtro_regional_tipo != 'TODOS'
            )
            
            return {
                'id': str(config.id),
                'nombre_config': config.nombre_config,
                'campo_orden': config.campo_orden,
                'direccion_orden': config.direccion_orden,
                'filtro_conceptos_tipo': config.filtro_conceptos_tipo,
                'conceptos_seleccionados': conceptos or [],
                'filtro_tipo_trabajo': config.filtro_tipo_trabajo,
                'filtro_regional_tipo': config.filtro_regional_tipo,
                'regionales_seleccionadas': regionales or [],
                'descripcion': config.descripcion,
                'is_active': config.is_active,
                'updated_by': config.updated_by,
                'updated_at': config.updated_at,
                'configurado': configurado
            }
        except Exception as e:
            logger.error(f"Error al actualizar configuración global: {e}")
            return None

    def get_historial_configuracion_global(self) -> List[Dict[str, Any]]:
        """Obtiene historial de cambios de configuración GLOBAL"""
        try:
            import json
            historial = self.repository.get_historial_configuracion_global()
            
            return [
                {
                    'id': str(h.id),
                    'accion': h.accion,
                    'nombre_config': h.nombre_config,
                    'campo_orden': h.campo_orden,
                    'direccion_orden': h.direccion_orden,
                    'filtro_conceptos_tipo': h.filtro_conceptos_tipo,
                    'conceptos_seleccionados': json.loads(h.conceptos_seleccionados) if h.conceptos_seleccionados else [],
                    'filtro_tipo_trabajo': h.filtro_tipo_trabajo,
                    'filtro_regional_tipo': h.filtro_regional_tipo,
                    'regionales_seleccionadas': json.loads(h.regionales_seleccionadas) if h.regionales_seleccionadas else [],
                    'changed_by': h.changed_by,
                    'changed_at': h.changed_at,
                    'cambios_detalle': json.loads(h.cambios_detalle) if h.cambios_detalle else None
                }
                for h in historial
            ]
        except Exception as e:
            logger.error(f"Error al obtener historial: {e}")
            return []

    def get_conceptos_disponibles_sistema(self) -> List[Dict[str, Any]]:
        """Lista TODOS los conceptos del sistema (para configuración)"""
        try:
            conceptos = self.repository.get_conceptos_disponibles_sistema()
            return [
                {
                    'concepto': c[0],
                    'cantidad': c[1]
                }
                for c in conceptos
            ]
        except Exception as e:
            logger.error(f"Error al obtener conceptos sistema: {e}")
            return []

    def get_conceptos_disponibles_usuario(self) -> List[Dict[str, Any]]:
        """
        Lista conceptos disponibles según configuración GLOBAL (para congelar).
        Ya no necesita parámetros porque la configuración es GLOBAL.
        """
        try:
            conceptos = self.repository.get_conceptos_disponibles_segun_config_global()
            return [
                {
                    'concepto': c[0],
                    'cantidad': c[1]
                }
                for c in conceptos
            ]
        except Exception as e:
            logger.error(f"Error al obtener conceptos usuario: {e}")
            return []

    def get_regionales_disponibles(self) -> List[str]:
        """Lista regionales disponibles"""
        try:
            return self.repository.get_regionales_disponibles()
        except Exception as e:
            logger.error(f"Error al obtener regionales: {e}")
            return []

    # ==========================================
    # CONCEPTOS ESPECIALES: MALO Y RFS
    # ==========================================

    def gestionar_oferta_malo(
        self,
        oferta_numero: str,
        accion_id: str,
        subaccion_id: str,
        observacion: Optional[str],
        usuario_data: Dict[str, Any]
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Gestiona una oferta con concepto MALO.
        Cierra la oferta y guarda el concepto anterior.
        
        Args:
            oferta_numero: Número de oferta
            accion_id: ID de la acción MALO
            subaccion_id: ID de la subacción MALO
            observacion: Observaciones opcionales
            usuario_data: Datos del usuario
            
        Returns:
            Tupla (datos_gestion, mensaje_error)
        """
        try:
            # Validar que la acción sea realmente MALO
            accion = self.repository.get_accion_by_id(accion_id)
            if not accion or accion.nombre_accion != 'MALO':
                return None, "La acción debe ser 'MALO'"
            
            # Gestionar con concepto especial
            oferta_gestionada, error = self.repository.gestionar_oferta_concepto_especial(
                oferta=oferta_numero,
                concepto='MALO',
                estado_nuevo='CERRADO',
                usuario_data=usuario_data,
                accion_id=accion_id,
                subaccion_id=subaccion_id,
                observacion=observacion
            )
            
            if error:
                return None, error
            
            if not oferta_gestionada:
                return None, "Error al gestionar oferta como MALO"
            
            concepto_anterior = oferta_gestionada.campos_dinamicos.get('concepto_anterior', '')
            
            logger.info(f"Oferta {oferta_numero} gestionada como MALO por {usuario_data['login']}")
            
            return {
                'oferta': oferta_numero,
                'concepto': 'MALO',
                'concepto_anterior': concepto_anterior,
                'estado': 'CERRADO',
                'fecha_gestion': oferta_gestionada.fecha_gestion.astimezone(ZoneInfo("America/Bogota"))
            }, None
            
        except Exception as e:
            logger.error(f"Error al gestionar oferta como MALO: {e}")
            return None, f"Error interno: {str(e)}"

    def gestionar_oferta_rfs(
        self,
        oferta_numero: str,
        accion_id: str,
        subaccion_id: str,
        observacion: Optional[str],
        usuario_data: Dict[str, Any]
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Gestiona una oferta con concepto RFS.
        Cierra la oferta y guarda el concepto anterior.
        
        Args:
            oferta_numero: Número de oferta
            accion_id: ID de la acción RFS
            subaccion_id: ID de la subacción RFS
            observacion: Observaciones opcionales
            usuario_data: Datos del usuario
            
        Returns:
            Tupla (datos_gestion, mensaje_error)
        """
        try:
            # Validar que la acción sea realmente RFS
            accion = self.repository.get_accion_by_id(accion_id)
            if not accion or accion.nombre_accion != 'RFS':
                return None, "La acción debe ser 'RFS'"
            
            # Gestionar con concepto especial
            oferta_gestionada, error = self.repository.gestionar_oferta_concepto_especial(
                oferta=oferta_numero,
                concepto='RFS',
                estado_nuevo='CERRADO',
                usuario_data=usuario_data,
                accion_id=accion_id,
                subaccion_id=subaccion_id,
                observacion=observacion
            )
            
            if error:
                return None, error
            
            if not oferta_gestionada:
                return None, "Error al gestionar oferta como RFS"
            
            concepto_anterior = oferta_gestionada.campos_dinamicos.get('concepto_anterior', '')
            
            logger.info(f"Oferta {oferta_numero} gestionada como RFS por {usuario_data['login']}")
            
            return {
                'oferta': oferta_numero,
                'concepto': 'RFS',
                'concepto_anterior': concepto_anterior,
                'estado': 'CERRADO',
                'fecha_gestion': oferta_gestionada.fecha_gestion.astimezone(ZoneInfo("America/Bogota"))
            }, None
            
        except Exception as e:
            logger.error(f"Error al gestionar oferta como RFS: {e}")
            return None, f"Error interno: {str(e)}"

    def liberar_oferta_malo(
        self,
        oferta_numero: str,
        supervisor_data: Dict[str, Any],
        motivo: Optional[str] = None
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Libera una oferta en concepto MALO (solo supervisores/superusers).
        Restaura el concepto anterior y cambia a estado ABIERTO.
        
        Args:
            oferta_numero: Número de oferta
            supervisor_data: Datos del supervisor
            motivo: Motivo de la liberación
            
        Returns:
            Tupla (datos_liberacion, mensaje_error)
        """
        try:
            profile_id = supervisor_data['profile_id']
            
            # Validar perfil
            if profile_id not in [1, 2]:
                return None, "Solo supervisores y superusers pueden liberar ofertas MALO"
            
            # Liberar oferta
            oferta_liberada, error = self.repository.liberar_oferta_concepto_especial(
                oferta=oferta_numero,
                concepto_esperado='MALO',
                supervisor_data=supervisor_data,
                motivo=motivo
            )
            
            if error:
                return None, error
            
            if not oferta_liberada:
                return None, "Error al liberar oferta MALO"
            
            concepto_restaurado = oferta_liberada.campos_dinamicos.get('concepto', '')
            
            logger.info(f"Oferta {oferta_numero} liberada de MALO por {supervisor_data['login']}")
            
            return {
                'oferta': oferta_numero,
                'concepto_anterior': 'MALO',
                'concepto_restaurado': concepto_restaurado,
                'estado': 'ABIERTO',
                'liberada_por': supervisor_data['login'],
                'fecha_liberacion': get_bogota_now().astimezone(ZoneInfo("America/Bogota"))
            }, None
            
        except Exception as e:
            logger.error(f"Error al liberar oferta MALO: {e}")
            return None, f"Error interno: {str(e)}"

    def liberar_oferta_rfs(
        self,
        oferta_numero: str,
        supervisor_data: Dict[str, Any],
        motivo: Optional[str] = None
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Libera una oferta en concepto RFS (solo supervisores/superusers).
        Restaura el concepto anterior y cambia a estado ABIERTO.
        
        Args:
            oferta_numero: Número de oferta
            supervisor_data: Datos del supervisor
            motivo: Motivo de la liberación
            
        Returns:
            Tupla (datos_liberacion, mensaje_error)
        """
        try:
            profile_id = supervisor_data['profile_id']
            
            # Validar perfil
            if profile_id not in [1, 2]:
                return None, "Solo supervisores y superusers pueden liberar ofertas RFS"
            
            # Liberar oferta
            oferta_liberada, error = self.repository.liberar_oferta_concepto_especial(
                oferta=oferta_numero,
                concepto_esperado='RFS',
                supervisor_data=supervisor_data,
                motivo=motivo
            )
            
            if error:
                return None, error
            
            if not oferta_liberada:
                return None, "Error al liberar oferta RFS"
            
            concepto_restaurado = oferta_liberada.campos_dinamicos.get('concepto', '')
            
            logger.info(f"Oferta {oferta_numero} liberada de RFS por {supervisor_data['login']}")
            
            return {
                'oferta': oferta_numero,
                'concepto_anterior': 'RFS',
                'concepto_restaurado': concepto_restaurado,
                'estado': 'ABIERTO',
                'liberada_por': supervisor_data['login'],
                'fecha_liberacion': get_bogota_now().astimezone(ZoneInfo("America/Bogota"))
            }, None
            
        except Exception as e:
            logger.error(f"Error al liberar oferta RFS: {e}")
            return None, f"Error interno: {str(e)}"
