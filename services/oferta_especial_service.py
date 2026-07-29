"""
Servicio de negocio para listado de ofertas especiales.

Este servicio implementa la lógica de negocio para consultar ofertas con conceptos
especiales: PAUSADAS, MALO, RFS.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from app.repositories.oferta_especial_repository import OfertaEspecialRepository

logger = logging.getLogger("oferta_especial_service")


class OfertaEspecialService:
    """
    Servicio para listado de ofertas especiales.
    Implementa lógica de negocio y transformaciones.
    """

    def __init__(self, db: Session):
        """
        Inicializa el service con la sesión de base de datos.
        
        Args:
            db: Sesión de SQLAlchemy inyectada por dependency
        """
        self.db = db
        self.repository = OfertaEspecialRepository(db)

    def listar_ofertas_pausadas(
        self,
        uen: Optional[str] = None,
        usuario_login: Optional[str] = None,
        fecha_desde: Optional[datetime] = None,
        fecha_hasta: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
        order_by: str = 'fecha_pausa',
        order_direction: str = 'DESC'
    ) -> Dict[str, Any]:
        """
        Lista ofertas pausadas con paginación y filtros.
        
        Args:
            uen: Filtro por UEN
            usuario_login: Filtro por asesor
            fecha_desde: Fecha desde
            fecha_hasta: Fecha hasta
            limit: Límite de registros
            offset: Desplazamiento
            order_by: Campo ordenamiento
            order_direction: Dirección ordenamiento
            
        Returns:
            Dict con data, total, limit, offset
        """
        try:
            # Validar limit
            if limit > 500:
                limit = 500
            
            # Obtener datos del repository
            ofertas, total = self.repository.listar_ofertas_pausadas(
                uen=uen,
                usuario_login=usuario_login,
                fecha_desde=fecha_desde,
                fecha_hasta=fecha_hasta,
                limit=limit,
                offset=offset,
                order_by=order_by,
                order_direction=order_direction
            )

            return {
                'total': total,
                'limit': limit,
                'offset': offset,
                'data': ofertas
            }

        except Exception as e:
            logger.error(f"Error en service listar ofertas pausadas: {e}")
            raise

    def listar_ofertas_malo(
        self,
        uen: Optional[str] = None,
        usuario_login: Optional[str] = None,
        fecha_desde: Optional[datetime] = None,
        fecha_hasta: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
        order_by: str = 'fecha_gestion',
        order_direction: str = 'DESC'
    ) -> Dict[str, Any]:
        """
        Lista ofertas MALO con paginación y filtros.
        
        Args:
            uen: Filtro por UEN
            usuario_login: Filtro por asesor
            fecha_desde: Fecha desde
            fecha_hasta: Fecha hasta
            limit: Límite de registros
            offset: Desplazamiento
            order_by: Campo ordenamiento
            order_direction: Dirección ordenamiento
            
        Returns:
            Dict con data, total, limit, offset
        """
        try:
            # Validar limit
            if limit > 500:
                limit = 500
            
            # Obtener datos del repository
            ofertas, total = self.repository.listar_ofertas_malo(
                uen=uen,
                usuario_login=usuario_login,
                fecha_desde=fecha_desde,
                fecha_hasta=fecha_hasta,
                limit=limit,
                offset=offset,
                order_by=order_by,
                order_direction=order_direction
            )

            return {
                'total': total,
                'limit': limit,
                'offset': offset,
                'data': ofertas
            }

        except Exception as e:
            logger.error(f"Error en service listar ofertas MALO: {e}")
            raise

    def listar_ofertas_rfs(
        self,
        uen: Optional[str] = None,
        usuario_login: Optional[str] = None,
        fecha_desde: Optional[datetime] = None,
        fecha_hasta: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
        order_by: str = 'fecha_gestion',
        order_direction: str = 'DESC'
    ) -> Dict[str, Any]:
        """
        Lista ofertas RFS con paginación y filtros.
        
        Args:
            uen: Filtro por UEN
            usuario_login: Filtro por asesor
            fecha_desde: Fecha desde
            fecha_hasta: Fecha hasta
            limit: Límite de registros
            offset: Desplazamiento
            order_by: Campo ordenamiento
            order_direction: Dirección ordenamiento
            
        Returns:
            Dict con data, total, limit, offset
        """
        try:
            # Validar limit
            if limit > 500:
                limit = 500
            
            # Obtener datos del repository
            ofertas, total = self.repository.listar_ofertas_rfs(
                uen=uen,
                usuario_login=usuario_login,
                fecha_desde=fecha_desde,
                fecha_hasta=fecha_hasta,
                limit=limit,
                offset=offset,
                order_by=order_by,
                order_direction=order_direction
            )

            return {
                'total': total,
                'limit': limit,
                'offset': offset,
                'data': ofertas
            }

        except Exception as e:
            logger.error(f"Error en service listar ofertas RFS: {e}")
            raise

    def get_resumen_dashboard(self) -> Dict[str, Any]:
        """
        Obtiene resumen consolidado de ofertas especiales para dashboard.
        
        Returns:
            Dict con resumen de pausadas, malo, rfs y totales
        """
        try:
            resumen = self.repository.get_resumen_ofertas_especiales()
            
            return {
                'pausadas': {
                    'total': resumen['pausadas'],
                    'tipo': 'OFERTA PAUSADA',
                    'estado': 'EN_TRAMITE_PAUSADO'
                },
                'malo': {
                    'total': resumen['malo'],
                    'tipo': 'MALO',
                    'estado': 'CERRADO'
                },
                'rfs': {
                    'total': resumen['rfs'],
                    'tipo': 'RFS',
                    'estado': 'CERRADO'
                },
                'total_general': resumen['total_general']
            }

        except Exception as e:
            logger.error(f"Error en service resumen dashboard: {e}")
            raise

