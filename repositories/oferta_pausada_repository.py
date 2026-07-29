"""
Repositorio para gestión de ofertas pausadas.

Este repositorio maneja todas las operaciones relacionadas con el concepto especial
"OFERTA PAUSADA", incluyendo:
- Configuración de tiempos y límites
- Pausar/reanudar ofertas
- Validaciones de tiempo y cantidad
- Tracking histórico de pausas
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from app.models.oferta_gestion_model import (
    OfertaConfiguracionPausada,
    OfertaPausadaTracking
)
from app.models.enlistment_manager_model import EnlistmentManager
from app.db.postgres import SessionLocalPG
from app.db.timezone_types import get_bogota_now
import uuid

logger = logging.getLogger("oferta_pausada_repository")


class OfertaPausadaRepository:
    """Repository para operaciones de ofertas pausadas"""

    def __init__(self, db: Session):
        """Inicializa el repository con la sesión de base de datos.
        
        Args:
            db: Sesión de SQLAlchemy inyectada por dependency
        """
        self.db = db

    # ==========================================
    # CONFIGURACIÓN
    # ==========================================

    def get_configuracion_pausada(self) -> Optional[OfertaConfiguracionPausada]:
        """
        Obtiene la configuración activa de ofertas pausadas.
        
        Returns:
            Configuración activa o None si no existe
        """
        try:
            return self.db.query(OfertaConfiguracionPausada).filter(
                OfertaConfiguracionPausada.is_active == True
            ).first()
        except Exception as e:
            logger.error(f"Error al obtener configuración pausada: {e}")
            return None

    def update_configuracion_pausada(
        self, 
        tiempo_minimo: Optional[int] = None,
        max_ofertas: Optional[int] = None,
        updated_by: str = None
    ) -> Optional[OfertaConfiguracionPausada]:
        """
        Actualiza la configuración de ofertas pausadas.
        
        Args:
            tiempo_minimo: Tiempo mínimo en minutos antes de poder pausar
            max_ofertas: Cantidad máxima de ofertas pausadas por asesor
            updated_by: Usuario que realiza la actualización
            
        Returns:
            Configuración actualizada o None en caso de error
        """
        try:
            config = self.get_configuracion_pausada()
            
            if not config:
                # Crear configuración si no existe
                config = OfertaConfiguracionPausada(
                    tiempo_minimo_pausa_minutos=tiempo_minimo or 7,
                    max_ofertas_pausadas_por_asesor=max_ofertas or 3,
                    is_active=True,
                    updated_by=updated_by
                )
                self.db.add(config)
            else:
                # Actualizar configuración existente
                if tiempo_minimo is not None:
                    config.tiempo_minimo_pausa_minutos = tiempo_minimo
                if max_ofertas is not None:
                    config.max_ofertas_pausadas_por_asesor = max_ofertas
                if updated_by:
                    config.updated_by = updated_by
            
            self.db.commit()
            self.db.refresh(config)
            logger.info(f"Configuración pausada actualizada por {updated_by}")
            return config
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error al actualizar configuración pausada: {e}")
            return None

    # ==========================================
    # VALIDACIONES
    # ==========================================

    def validar_tiempo_minimo_transcurrido(
        self, 
        fecha_asignacion: datetime,
        tiempo_minimo_minutos: int
    ) -> bool:
        """
        Valida si ha transcurrido el tiempo mínimo desde la asignación.
        
        Args:
            fecha_asignacion: Fecha en que se asignó la oferta
            tiempo_minimo_minutos: Tiempo mínimo requerido en minutos
            
        Returns:
            True si ha transcurrido el tiempo mínimo, False en caso contrario
        """
        try:
            ahora = get_bogota_now()
            tiempo_transcurrido = (ahora - fecha_asignacion).total_seconds() / 60
            
            resultado = tiempo_transcurrido >= tiempo_minimo_minutos
            logger.debug(f"Tiempo transcurrido: {tiempo_transcurrido:.2f} min, Mínimo: {tiempo_minimo_minutos} min, Válido: {resultado}")
            
            return resultado
            
        except Exception as e:
            logger.error(f"Error al validar tiempo mínimo: {e}")
            return False

    def contar_ofertas_pausadas_usuario(self, usuario_login: str) -> int:
        """
        Cuenta cuántas ofertas tiene pausadas actualmente un usuario.
        
        Args:
            usuario_login: Login del usuario
            
        Returns:
            Cantidad de ofertas pausadas actualmente
        """
        try:
            count = self.db.query(OfertaPausadaTracking).filter(
                OfertaPausadaTracking.usuario_login == usuario_login,
                OfertaPausadaTracking.fecha_reanudacion.is_(None)  # Solo las que están pausadas actualmente
            ).count()
            
            logger.debug(f"Usuario {usuario_login} tiene {count} ofertas pausadas")
            return count
            
        except Exception as e:
            logger.error(f"Error al contar ofertas pausadas: {e}")
            return 0

    def validar_puede_pausar(
        self, 
        usuario_login: str, 
        fecha_asignacion: datetime
    ) -> tuple[bool, Optional[str]]:
        """
        Valida si un usuario puede pausar una oferta.
        
        Args:
            usuario_login: Login del usuario
            fecha_asignacion: Fecha de asignación de la oferta
            
        Returns:
            Tupla (puede_pausar, mensaje_error)
        """
        try:
            # Obtener configuración
            config = self.get_configuracion_pausada()
            if not config:
                return False, "No existe configuración de pausas"
            
            # Validar tiempo mínimo
            if not self.validar_tiempo_minimo_transcurrido(
                fecha_asignacion, 
                config.tiempo_minimo_pausa_minutos
            ):
                return False, f"Debes trabajar la oferta al menos {config.tiempo_minimo_pausa_minutos} minutos antes de pausarla"
            
            # Validar cantidad máxima
            cantidad_pausadas = self.contar_ofertas_pausadas_usuario(usuario_login)
            if cantidad_pausadas >= config.max_ofertas_pausadas_por_asesor:
                return False, f"Ya tienes {cantidad_pausadas} ofertas pausadas. Máximo permitido: {config.max_ofertas_pausadas_por_asesor}"
            
            return True, None
            
        except Exception as e:
            logger.error(f"Error al validar si puede pausar: {e}")
            return False, f"Error al validar: {str(e)}"

    # ==========================================
    # TRACKING DE PAUSAS
    # ==========================================

    def create_tracking_pausa(self, data: Dict[str, Any]) -> Optional[OfertaPausadaTracking]:
        """
        Crea un registro de tracking cuando se pausa una oferta.
        
        Args:
            data: Datos del tracking (oferta, usuario_login, concepto_anterior, etc.)
            
        Returns:
            Registro de tracking creado o None en caso de error
        """
        try:
            tracking = OfertaPausadaTracking(
                oferta=data['oferta'],
                usuario_login=data['usuario_login'],
                concepto_anterior=data.get('concepto_anterior'),
                fecha_pausa=get_bogota_now(),
                pausada_por=data.get('pausada_por', 'asesor'),
                reanudada_por=None,
                tipo_reanudacion=None,
                motivo_liberacion=None
            )
            
            self.db.add(tracking)
            self.db.commit()
            self.db.refresh(tracking)
            
            logger.info(f"Tracking de pausa creado para oferta {data['oferta']}")
            return tracking
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error al crear tracking de pausa: {e}")
            return None

    def actualizar_tracking_reanudacion(
        self,
        oferta: str,
        usuario_login: str,
        reanudada_por: str,
        tipo_reanudacion: str,
        motivo_liberacion: Optional[str] = None
    ) -> bool:
        """
        Actualiza el tracking cuando se reanuda una oferta.
        
        Args:
            oferta: Número de oferta
            usuario_login: Usuario que tiene la oferta pausada
            reanudada_por: Usuario que reanuda (puede ser el mismo o supervisor)
            tipo_reanudacion: 'manual_asesor', 'liberada_supervisor', 'liberada_superuser'
            motivo_liberacion: Motivo de liberación (opcional)
            
        Returns:
            True si se actualizó correctamente, False en caso contrario
        """
        try:
            # Buscar el tracking activo (sin fecha de reanudación)
            tracking = self.db.query(OfertaPausadaTracking).filter(
                OfertaPausadaTracking.oferta == oferta,
                OfertaPausadaTracking.usuario_login == usuario_login,
                OfertaPausadaTracking.fecha_reanudacion.is_(None)
            ).first()
            
            if not tracking:
                logger.warning(f"No se encontró tracking activo para oferta {oferta}")
                return False
            
            # Actualizar datos de reanudación
            tracking.fecha_reanudacion = get_bogota_now()
            tracking.reanudada_por = reanudada_por
            tracking.tipo_reanudacion = tipo_reanudacion
            tracking.motivo_liberacion = motivo_liberacion
            
            self.db.commit()
            logger.info(f"Tracking actualizado - Oferta {oferta} reanudada por {reanudada_por}")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error al actualizar tracking de reanudación: {e}")
            return False

    def get_ofertas_pausadas_usuario(self, usuario_login: str) -> List[Dict[str, Any]]:
        """
        Obtiene todas las ofertas pausadas actualmente de un usuario.
        
        Args:
            usuario_login: Login del usuario
            
        Returns:
            Lista de ofertas pausadas con sus detalles
        """
        try:
            trackings = self.db.query(OfertaPausadaTracking).filter(
                OfertaPausadaTracking.usuario_login == usuario_login,
                OfertaPausadaTracking.fecha_reanudacion.is_(None)
            ).order_by(desc(OfertaPausadaTracking.fecha_pausa)).all()
            
            resultado = []
            for tracking in trackings:
                # Calcular tiempo pausado
                tiempo_pausado_minutos = int(
                    (get_bogota_now() - tracking.fecha_pausa).total_seconds() / 60
                )
                
                resultado.append({
                    'oferta': tracking.oferta,
                    'concepto_anterior': tracking.concepto_anterior,
                    'fecha_pausa': tracking.fecha_pausa,
                    'tiempo_pausado_minutos': tiempo_pausado_minutos
                })
            
            return resultado
            
        except Exception as e:
            logger.error(f"Error al obtener ofertas pausadas del usuario: {e}")
            return []

    def get_historico_pausas_oferta(self, oferta: str) -> List[OfertaPausadaTracking]:
        """
        Obtiene el histórico completo de pausas de una oferta.
        
        Args:
            oferta: Número de oferta
            
        Returns:
            Lista de registros de tracking
        """
        try:
            return self.db.query(OfertaPausadaTracking).filter(
                OfertaPausadaTracking.oferta == oferta
            ).order_by(desc(OfertaPausadaTracking.fecha_pausa)).all()
        except Exception as e:
            logger.error(f"Error al obtener histórico de pausas: {e}")
            return []
