"""
Servicio de negocio para gestión de ofertas pausadas.

Este servicio implementa toda la lógica de negocio relacionada con el concepto especial
"OFERTA PAUSADA", incluyendo validaciones, pausas, reanudaciones y configuración.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from zoneinfo import ZoneInfo
from sqlalchemy.orm import Session
from app.repositories.oferta_pausada_repository import OfertaPausadaRepository
from app.repositories.oferta_gestion_repository import OfertaGestionRepository
from app.db.timezone_types import get_bogota_now

logger = logging.getLogger("oferta_pausada_service")


class OfertaPausadaService:
    """
    Servicio para gestión de ofertas pausadas.
    Implementa toda la lógica de negocio y validaciones.
    """

    def __init__(self, db: Session):
        """Inicializa el service con la sesión de base de datos.
        
        Args:
            db: Sesión de SQLAlchemy inyectada por dependency
        """
        self.db = db
        self.repository = OfertaPausadaRepository(db)
        self.oferta_repository = OfertaGestionRepository(db)

    # ==========================================
    # CONFIGURACIÓN
    # ==========================================

    def get_configuracion(self) -> Optional[Dict[str, Any]]:
        """
        Obtiene la configuración actual de ofertas pausadas.
        
        Returns:
            Dict con la configuración o None
        """
        try:
            config = self.repository.get_configuracion_pausada()
            
            if not config:
                return None
            
            return {
                'tiempo_minimo_pausa_minutos': config.tiempo_minimo_pausa_minutos,
                'max_ofertas_pausadas_por_asesor': config.max_ofertas_pausadas_por_asesor,
                'updated_by': config.updated_by,
                'updated_at': config.updated_at.astimezone(ZoneInfo("America/Bogota")) if config.updated_at else None
            }
        except Exception as e:
            logger.error(f"Error al obtener configuración: {e}")
            return None

    def actualizar_configuracion(
        self,
        tiempo_minimo: Optional[int],
        max_ofertas: Optional[int],
        updated_by: str
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Actualiza la configuración de ofertas pausadas.
        Solo para SuperUser y Supervisor.
        
        Args:
            tiempo_minimo: Tiempo mínimo en minutos
            max_ofertas: Cantidad máxima de ofertas pausadas
            updated_by: Usuario que actualiza
            
        Returns:
            Tupla (configuración_actualizada, mensaje_error)
        """
        try:
            # Validaciones
            if tiempo_minimo is not None and tiempo_minimo < 0:
                return None, "El tiempo mínimo debe ser mayor o igual a 0"
            
            if max_ofertas is not None and max_ofertas < 1:
                return None, "La cantidad máxima debe ser al menos 1"
            
            # Actualizar
            config = self.repository.update_configuracion_pausada(
                tiempo_minimo=tiempo_minimo,
                max_ofertas=max_ofertas,
                updated_by=updated_by
            )
            
            if not config:
                return None, "Error al actualizar configuración"
            
            logger.info(f"Configuración actualizada por {updated_by}")
            
            return {
                'tiempo_minimo_pausa_minutos': config.tiempo_minimo_pausa_minutos,
                'max_ofertas_pausadas_por_asesor': config.max_ofertas_pausadas_por_asesor,
                'updated_by': config.updated_by,
                'updated_at': config.updated_at.astimezone(ZoneInfo("America/Bogota"))
            }, None
            
        except Exception as e:
            logger.error(f"Error al actualizar configuración: {e}")
            return None, f"Error interno: {str(e)}"

    # ==========================================
    # PAUSAR OFERTA
    # ==========================================

    def pausar_oferta(
        self,
        oferta_numero: str,
        usuario_data: Dict[str, Any]
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Pausa una oferta que está en trámite.
        
        Validaciones:
        - Oferta debe estar EN_TRAMITE
        - Oferta debe estar asignada al usuario
        - Debe haber transcurrido el tiempo mínimo
        - Usuario no debe exceder el máximo de ofertas pausadas
        
        Args:
            oferta_numero: Número de oferta a pausar
            usuario_data: Datos del usuario (login, nombre, profile_id)
            
        Returns:
            Tupla (datos_pausa, mensaje_error)
        """
        try:
            usuario_login = usuario_data['login']
            
            # Obtener oferta
            oferta = self.oferta_repository.get_oferta_by_numero(oferta_numero)
            
            if not oferta:
                return None, "Oferta no encontrada"
            
            # Validar que esté EN_TRAMITE
            if oferta.estado_oferta != 'EN_TRAMITE':
                return None, f"La oferta debe estar en estado EN_TRAMITE (actual: {oferta.estado_oferta})"
            
            # Validar que esté asignada al usuario
            if oferta.usuario_asignado_login != usuario_login:
                return None, "Esta oferta no está asignada a ti"
            
            # Validar que no esté ya en concepto OFERTA PAUSADA
            concepto_actual = oferta.campos_dinamicos.get('concepto', '')
            if concepto_actual == 'OFERTA PAUSADA':
                return None, "Esta oferta ya está pausada"
            
            # Validar tiempo mínimo y cantidad máxima
            puede_pausar, mensaje_error = self.repository.validar_puede_pausar(
                usuario_login,
                oferta.fecha_asignacion
            )
            
            if not puede_pausar:
                return None, mensaje_error
            
            estado_anterior = oferta.estado_oferta
            
            # Cambiar concepto y guardar anterior
            oferta_actualizada, concepto_anterior = self.oferta_repository.cambiar_concepto_y_guardar_anterior(
                oferta_numero,
                'OFERTA PAUSADA'
            )
            
            if not oferta_actualizada:
                return None, "Error al cambiar concepto"
            
            # Cambiar estado a EN_TRAMITE_PAUSADO
            oferta_actualizada.estado_oferta = 'EN_TRAMITE_PAUSADO'
            self.oferta_repository.db.commit()
            self.oferta_repository.db.refresh(oferta_actualizada)
            
            # Crear tracking de pausa
            tracking = self.repository.create_tracking_pausa({
                'oferta': oferta_numero,
                'usuario_login': usuario_login,
                'concepto_anterior': concepto_anterior,
                'pausada_por': 'asesor'
            })
            
            if not tracking:
                return None, "Error al crear tracking de pausa"
            
            # Registrar en histórico de estados
            self.oferta_repository.create_historico_estado({
                'oferta': oferta_numero,
                'accion_sistema': 'PAUSAR',
                'estado_anterior': estado_anterior,
                'estado_nuevo': 'EN_TRAMITE_PAUSADO',
                'usuario_login': usuario_login,
                'usuario_nombre': usuario_data['nombre'],
                'usuario_profile_id': usuario_data['profile_id'],
                'motivo': 'Oferta pausada temporalmente',
                'ip_address': usuario_data.get('ip_address')
            })
            
            # Registrar en histórico de enlistment
            campos_modificados = {
                "concepto": {"old": concepto_anterior, "new": "OFERTA PAUSADA"},
                "estado_oferta": {"old": estado_anterior, "new": "EN_TRAMITE_PAUSADO"}
            }
            self.oferta_repository.enlistment_repo.create_manual_history_record(
                oferta_actualizada,
                campos_modificados,
                "PAUSAR_OFERTA"
            )
            
            logger.info(f"Oferta {oferta_numero} pausada por {usuario_login}")
            
            return {
                'oferta': oferta_numero,
                'concepto_anterior': concepto_anterior,
                'concepto_nuevo': 'OFERTA PAUSADA',
                'estado': 'EN_TRAMITE_PAUSADO',
                'fecha_pausa': tracking.fecha_pausa.astimezone(ZoneInfo("America/Bogota"))
            }, None
            
        except Exception as e:
            logger.error(f"Error al pausar oferta: {e}")
            return None, f"Error interno: {str(e)}"

    # ==========================================
    # REANUDAR OFERTA
    # ==========================================

    def reanudar_oferta(
        self,
        oferta_numero: str,
        usuario_data: Dict[str, Any]
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Reanuda una oferta pausada (acción del asesor).
        
        Args:
            oferta_numero: Número de oferta a reanudar
            usuario_data: Datos del usuario
            
        Returns:
            Tupla (datos_reanudacion, mensaje_error)
        """
        try:
            usuario_login = usuario_data['login']
            
            # Obtener oferta
            oferta = self.oferta_repository.get_oferta_by_numero(oferta_numero)
            
            if not oferta:
                return None, "Oferta no encontrada"
            
            # Validar que esté EN_TRAMITE_PAUSADO
            if oferta.estado_oferta != 'EN_TRAMITE_PAUSADO':
                return None, f"La oferta debe estar pausada (estado actual: {oferta.estado_oferta})"
            
            # Validar que esté asignada al usuario
            if oferta.usuario_asignado_login != usuario_login:
                return None, "Esta oferta no está asignada a ti"
            
            # Validar que esté en concepto OFERTA PAUSADA
            concepto_actual = oferta.campos_dinamicos.get('concepto', '')
            if concepto_actual != 'OFERTA PAUSADA':
                return None, f"La oferta no está en concepto OFERTA PAUSADA (actual: {concepto_actual})"
            
            # Validar que el usuario NO tenga otra oferta EN_TRAMITE
            oferta_en_tramite = self.oferta_repository.get_oferta_en_tramite_by_usuario(usuario_login)
            if oferta_en_tramite:
                return None, f"Tienes una oferta en trámite ({oferta_en_tramite.oferta}). Debes terminarla antes de reanudar otra"
            
            estado_anterior = oferta.estado_oferta
            
            # Restaurar concepto anterior
            oferta_actualizada = self.oferta_repository.restaurar_concepto_anterior(oferta_numero)
            
            if not oferta_actualizada:
                return None, "Error al restaurar concepto anterior"
            
            # Cambiar estado a EN_TRAMITE
            oferta_actualizada.estado_oferta = 'EN_TRAMITE'
            self.oferta_repository.db.commit()
            self.oferta_repository.db.refresh(oferta_actualizada)
            
            concepto_restaurado = oferta_actualizada.campos_dinamicos.get('concepto', '')
            
            # Actualizar tracking
            self.repository.actualizar_tracking_reanudacion(
                oferta_numero,
                usuario_login,
                usuario_login,
                'manual_asesor'
            )
            
            # Registrar en histórico
            self.oferta_repository.create_historico_estado({
                'oferta': oferta_numero,
                'accion_sistema': 'REANUDAR',
                'estado_anterior': estado_anterior,
                'estado_nuevo': 'EN_TRAMITE',
                'usuario_login': usuario_login,
                'usuario_nombre': usuario_data['nombre'],
                'usuario_profile_id': usuario_data['profile_id'],
                'motivo': 'Oferta reanudada por asesor',
                'ip_address': usuario_data.get('ip_address')
            })
            
            # Registrar en histórico de enlistment
            campos_modificados = {
                "concepto": {"old": "OFERTA PAUSADA", "new": concepto_restaurado},
                "estado_oferta": {"old": estado_anterior, "new": "EN_TRAMITE"}
            }
            self.oferta_repository.enlistment_repo.create_manual_history_record(
                oferta_actualizada,
                campos_modificados,
                "REANUDAR_OFERTA"
            )
            
            logger.info(f"Oferta {oferta_numero} reanudada por {usuario_login}")
            
            return {
                'oferta': oferta_numero,
                'concepto_restaurado': concepto_restaurado,
                'estado': 'EN_TRAMITE',
                'fecha_reanudacion': get_bogota_now().astimezone(ZoneInfo("America/Bogota"))
            }, None
            
        except Exception as e:
            logger.error(f"Error al reanudar oferta: {e}")
            return None, f"Error interno: {str(e)}"

    # ==========================================
    # LIBERAR OFERTA (SUPERVISOR)
    # ==========================================

    def liberar_oferta_pausada(
        self,
        oferta_numero: str,
        supervisor_data: Dict[str, Any],
        motivo: Optional[str] = None
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Libera una oferta pausada (acción de supervisor/superuser).
        La oferta vuelve a estado ABIERTO.
        
        Args:
            oferta_numero: Número de oferta
            supervisor_data: Datos del supervisor
            motivo: Motivo de liberación
            
        Returns:
            Tupla (datos_liberacion, mensaje_error)
        """
        try:
            supervisor_login = supervisor_data['login']
            profile_id = supervisor_data['profile_id']
            
            # Validar perfil (Supervisor=3 o SuperUser=1)
            if profile_id not in [1, 3]:
                return None, "Solo supervisores y superusers pueden liberar ofertas pausadas"
            
            # Obtener oferta
            oferta = self.oferta_repository.get_oferta_by_numero(oferta_numero)
            
            if not oferta:
                return None, "Oferta no encontrada"
            
            # Validar que esté EN_TRAMITE_PAUSADO
            if oferta.estado_oferta != 'EN_TRAMITE_PAUSADO':
                return None, f"La oferta debe estar pausada (estado actual: {oferta.estado_oferta})"
            
            # Validar que esté en concepto OFERTA PAUSADA
            concepto_actual = oferta.campos_dinamicos.get('concepto', '')
            if concepto_actual != 'OFERTA PAUSADA':
                return None, f"La oferta no está en concepto OFERTA PAUSADA (actual: {concepto_actual})"
            
            usuario_asignado = oferta.usuario_asignado_login
            estado_anterior = oferta.estado_oferta
            
            # Restaurar concepto anterior
            oferta_actualizada = self.oferta_repository.restaurar_concepto_anterior(oferta_numero)
            
            if not oferta_actualizada:
                return None, "Error al restaurar concepto anterior"
            
            # Cambiar estado a ABIERTO y limpiar asignación
            oferta_actualizada.estado_oferta = 'ABIERTO'
            oferta_actualizada.usuario_asignado_login = None
            oferta_actualizada.usuario_asignado_nombre = None
            oferta_actualizada.usuario_asignado_profile_id = None
            oferta_actualizada.fecha_asignacion = None
            
            self.oferta_repository.db.commit()
            self.oferta_repository.db.refresh(oferta_actualizada)
            
            concepto_restaurado = oferta_actualizada.campos_dinamicos.get('concepto', '')
            
            # Actualizar tracking
            tipo_reanudacion = 'liberada_superuser' if profile_id == 1 else 'liberada_supervisor'
            self.repository.actualizar_tracking_reanudacion(
                oferta_numero,
                usuario_asignado,
                supervisor_login,
                tipo_reanudacion,
                motivo
            )
            
            # Registrar en histórico
            self.oferta_repository.create_historico_estado({
                'oferta': oferta_numero,
                'accion_sistema': 'LIBERAR_PAUSADA',
                'estado_anterior': estado_anterior,
                'estado_nuevo': 'ABIERTO',
                'usuario_login': supervisor_login,
                'usuario_nombre': supervisor_data['nombre'],
                'usuario_profile_id': profile_id,
                'asesor_asignado_login': usuario_asignado,
                'motivo': motivo or 'Liberada por supervisor',
                'ip_address': supervisor_data.get('ip_address')
            })
            
            # Registrar en histórico de enlistment
            campos_modificados = {
                "concepto": {"old": "OFERTA PAUSADA", "new": concepto_restaurado},
                "estado_oferta": {"old": estado_anterior, "new": "ABIERTO"},
                "usuario_asignado_login": {"old": usuario_asignado, "new": None}
            }
            self.oferta_repository.enlistment_repo.create_manual_history_record(
                oferta_actualizada,
                campos_modificados,
                "LIBERAR_PAUSADA"
            )
            
            logger.info(f"Oferta {oferta_numero} liberada de pausa por {supervisor_login}")
            
            return {
                'oferta': oferta_numero,
                'concepto_restaurado': concepto_restaurado,
                'estado': 'ABIERTO',
                'usuario_anterior': usuario_asignado,
                'liberada_por': supervisor_login,
                'fecha_liberacion': get_bogota_now().astimezone(ZoneInfo("America/Bogota"))
            }, None
            
        except Exception as e:
            logger.error(f"Error al liberar oferta pausada: {e}")
            return None, f"Error interno: {str(e)}"

    # ==========================================
    # CONSULTAS
    # ==========================================

    def get_mis_ofertas_pausadas(self, usuario_login: str) -> List[Dict[str, Any]]:
        """
        Obtiene la lista de ofertas pausadas del usuario.
        
        Args:
            usuario_login: Login del usuario
            
        Returns:
            Lista de ofertas pausadas
        """
        try:
            return self.repository.get_ofertas_pausadas_usuario(usuario_login)
        except Exception as e:
            logger.error(f"Error al obtener ofertas pausadas: {e}")
            return []
