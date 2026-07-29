"""
Repositorio para listado de ofertas especiales (PAUSADAS, MALO, RFS).

Este repositorio maneja las consultas para visualizar ofertas con conceptos especiales
que requieren atención de supervisores o superadmins.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc, and_, or_, func
from app.models.oferta_gestion_model import OfertaGestionDetalle, OfertaAccionCatalogo, OfertaSubaccionCatalogo
from app.models.oferta_gestion_model import OfertaPausadaTracking
from app.models.enlistment_manager_model import EnlistmentManager
from app.db.timezone_types import get_bogota_now

logger = logging.getLogger("oferta_especial_repository")


class OfertaEspecialRepository:
    """Repository para consultas de ofertas especiales"""

    def __init__(self, db: Session):
        """
        Inicializa el repository con la sesión de base de datos.
        
        Args:
            db: Sesión de SQLAlchemy inyectada por dependency
        """
        self.db = db

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
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Lista todas las ofertas pausadas actualmente.
        
        Args:
            uen: Filtro por UEN (opcional)
            usuario_login: Filtro por asesor (opcional)
            fecha_desde: Filtro fecha desde (opcional)
            fecha_hasta: Filtro fecha hasta (opcional)
            limit: Cantidad de registros
            offset: Desplazamiento para paginación
            order_by: Campo de ordenamiento
            order_direction: Dirección (ASC/DESC)
            
        Returns:
            Tupla (lista_ofertas, total_count)
        """
        try:
            # Query base con JOIN
            query = self.db.query(
                EnlistmentManager,
                OfertaPausadaTracking
            ).join(
                OfertaPausadaTracking,
                EnlistmentManager.oferta == OfertaPausadaTracking.oferta
            ).filter(
                and_(
                    EnlistmentManager.estado_oferta == 'EN_TRAMITE_PAUSADO',
                    EnlistmentManager.campos_dinamicos['concepto'].astext == 'OFERTA PAUSADA',
                    OfertaPausadaTracking.fecha_reanudacion.is_(None)  # Solo pausadas actualmente
                )
            )

            # Aplicar filtros opcionales
            if uen and uen != 'ALL':
                query = query.filter(
                    func.upper(EnlistmentManager.campos_dinamicos['uen'].astext) == uen.upper()
                )
            
            if usuario_login:
                query = query.filter(
                    EnlistmentManager.usuario_asignado_login == usuario_login
                )
            
            if fecha_desde:
                query = query.filter(OfertaPausadaTracking.fecha_pausa >= fecha_desde)
            
            if fecha_hasta:
                query = query.filter(OfertaPausadaTracking.fecha_pausa <= fecha_hasta)

            # Contar total antes de paginación
            total_count = query.count()

            # Ordenamiento
            order_col = OfertaPausadaTracking.fecha_pausa
            if order_by == 'oferta':
                order_col = EnlistmentManager.oferta
            
            if order_direction.upper() == 'DESC':
                query = query.order_by(desc(order_col))
            else:
                query = query.order_by(asc(order_col))

            # Paginación
            query = query.limit(limit).offset(offset)

            # Ejecutar query
            results = query.all()

            # Transformar resultados
            ofertas = []
            ahora = get_bogota_now()
            
            for oferta_obj, tracking in results:
                tiempo_pausada = (ahora - tracking.fecha_pausa).total_seconds() / 60  # minutos
                
                ofertas.append({
                    'oferta': oferta_obj.oferta,
                    'concepto_anterior': tracking.concepto_anterior or '',
                    'estado': oferta_obj.estado_oferta,
                    'usuario_asignado': {
                        'login': oferta_obj.usuario_asignado_login,
                        'nombre': oferta_obj.usuario_asignado_nombre,
                        'profile_id': oferta_obj.usuario_asignado_profile_id
                    },
                    'fecha_pausa': tracking.fecha_pausa,
                    'tiempo_pausada_minutos': round(tiempo_pausada, 2),
                    'pausada_por': tracking.pausada_por,
                    'campos_oferta': oferta_obj.campos_dinamicos
                })

            logger.info(f"Ofertas pausadas listadas: {len(ofertas)} de {total_count} total")
            return ofertas, total_count

        except Exception as e:
            logger.error(f"Error al listar ofertas pausadas: {e}")
            return [], 0

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
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Lista todas las ofertas marcadas como MALO.
        
        Args:
            uen: Filtro por UEN (opcional)
            usuario_login: Filtro por asesor que marcó (opcional)
            fecha_desde: Filtro fecha desde (opcional)
            fecha_hasta: Filtro fecha hasta (opcional)
            limit: Cantidad de registros
            offset: Desplazamiento para paginación
            order_by: Campo de ordenamiento
            order_direction: Dirección (ASC/DESC)
            
        Returns:
            Tupla (lista_ofertas, total_count)
        """
        try:
            # Subquery para obtener la última gestión de cada oferta
            subquery = self.db.query(
                OfertaGestionDetalle.oferta,
                func.max(OfertaGestionDetalle.fecha_gestion).label('max_fecha')
            ).group_by(OfertaGestionDetalle.oferta).subquery()

            # Query base con JOINs
            query = self.db.query(
                EnlistmentManager,
                OfertaGestionDetalle,
                OfertaAccionCatalogo,
                OfertaSubaccionCatalogo
            ).join(
                OfertaGestionDetalle,
                EnlistmentManager.oferta == OfertaGestionDetalle.oferta
            ).join(
                subquery,
                and_(
                    OfertaGestionDetalle.oferta == subquery.c.oferta,
                    OfertaGestionDetalle.fecha_gestion == subquery.c.max_fecha
                )
            ).join(
                OfertaAccionCatalogo,
                OfertaGestionDetalle.accion_id == OfertaAccionCatalogo.id
            ).join(
                OfertaSubaccionCatalogo,
                OfertaGestionDetalle.subaccion_id == OfertaSubaccionCatalogo.id
            ).filter(
                and_(
                    EnlistmentManager.estado_oferta == 'CERRADO',
                    EnlistmentManager.campos_dinamicos['concepto'].astext == 'MALO'
                )
            )

            # Aplicar filtros opcionales
            if uen and uen != 'ALL':
                query = query.filter(
                    func.upper(EnlistmentManager.campos_dinamicos['uen'].astext) == uen.upper()
                )
            
            if usuario_login:
                query = query.filter(OfertaGestionDetalle.usuario_login == usuario_login)
            
            if fecha_desde:
                query = query.filter(OfertaGestionDetalle.fecha_gestion >= fecha_desde)
            
            if fecha_hasta:
                query = query.filter(OfertaGestionDetalle.fecha_gestion <= fecha_hasta)

            # Contar total antes de paginación
            total_count = query.count()

            # Ordenamiento
            order_col = OfertaGestionDetalle.fecha_gestion
            if order_by == 'oferta':
                order_col = EnlistmentManager.oferta
            
            if order_direction.upper() == 'DESC':
                query = query.order_by(desc(order_col))
            else:
                query = query.order_by(asc(order_col))

            # Paginación
            query = query.limit(limit).offset(offset)

            # Ejecutar query
            results = query.all()

            # Transformar resultados
            ofertas = []
            ahora = get_bogota_now()
            
            for oferta_obj, gestion, accion, subaccion in results:
                dias_cerrada = (ahora - gestion.fecha_gestion).days
                
                ofertas.append({
                    'oferta': oferta_obj.oferta,
                    'concepto': 'MALO',
                    'concepto_anterior': oferta_obj.campos_dinamicos.get('concepto_anterior', ''),
                    'estado': oferta_obj.estado_oferta,
                    'usuario_que_marco': {
                        'login': gestion.usuario_login,
                        'nombre': gestion.usuario_nombre,
                        'profile_id': gestion.usuario_profile_id
                    },
                    'fecha_gestion': gestion.fecha_gestion,
                    'dias_cerrada': dias_cerrada,
                    'gestion': {
                        'accion': accion.nombre_accion,
                        'subaccion': subaccion.nombre_subaccion,
                        'observacion': gestion.observacion or ''
                    },
                    'campos_oferta': oferta_obj.campos_dinamicos
                })

            logger.info(f"Ofertas MALO listadas: {len(ofertas)} de {total_count} total")
            return ofertas, total_count

        except Exception as e:
            logger.error(f"Error al listar ofertas MALO: {e}")
            return [], 0

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
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Lista todas las ofertas marcadas como RFS (Ready For Service).
        
        Args:
            uen: Filtro por UEN (opcional)
            usuario_login: Filtro por asesor que marcó (opcional)
            fecha_desde: Filtro fecha desde (opcional)
            fecha_hasta: Filtro fecha hasta (opcional)
            limit: Cantidad de registros
            offset: Desplazamiento para paginación
            order_by: Campo de ordenamiento
            order_direction: Dirección (ASC/DESC)
            
        Returns:
            Tupla (lista_ofertas, total_count)
        """
        try:
            # Subquery para obtener la última gestión de cada oferta
            subquery = self.db.query(
                OfertaGestionDetalle.oferta,
                func.max(OfertaGestionDetalle.fecha_gestion).label('max_fecha')
            ).group_by(OfertaGestionDetalle.oferta).subquery()

            # Query base con JOINs (idéntico a MALO pero filtrando por 'RFS')
            query = self.db.query(
                EnlistmentManager,
                OfertaGestionDetalle,
                OfertaAccionCatalogo,
                OfertaSubaccionCatalogo
            ).join(
                OfertaGestionDetalle,
                EnlistmentManager.oferta == OfertaGestionDetalle.oferta
            ).join(
                subquery,
                and_(
                    OfertaGestionDetalle.oferta == subquery.c.oferta,
                    OfertaGestionDetalle.fecha_gestion == subquery.c.max_fecha
                )
            ).join(
                OfertaAccionCatalogo,
                OfertaGestionDetalle.accion_id == OfertaAccionCatalogo.id
            ).join(
                OfertaSubaccionCatalogo,
                OfertaGestionDetalle.subaccion_id == OfertaSubaccionCatalogo.id
            ).filter(
                and_(
                    EnlistmentManager.estado_oferta == 'CERRADO',
                    EnlistmentManager.campos_dinamicos['concepto'].astext == 'RFS'
                )
            )

            # Aplicar filtros opcionales
            if uen and uen != 'ALL':
                query = query.filter(
                    func.upper(EnlistmentManager.campos_dinamicos['uen'].astext) == uen.upper()
                )
            
            if usuario_login:
                query = query.filter(OfertaGestionDetalle.usuario_login == usuario_login)
            
            if fecha_desde:
                query = query.filter(OfertaGestionDetalle.fecha_gestion >= fecha_desde)
            
            if fecha_hasta:
                query = query.filter(OfertaGestionDetalle.fecha_gestion <= fecha_hasta)

            # Contar total antes de paginación
            total_count = query.count()

            # Ordenamiento
            order_col = OfertaGestionDetalle.fecha_gestion
            if order_by == 'oferta':
                order_col = EnlistmentManager.oferta
            
            if order_direction.upper() == 'DESC':
                query = query.order_by(desc(order_col))
            else:
                query = query.order_by(asc(order_col))

            # Paginación
            query = query.limit(limit).offset(offset)

            # Ejecutar query
            results = query.all()

            # Transformar resultados
            ofertas = []
            ahora = get_bogota_now()
            
            for oferta_obj, gestion, accion, subaccion in results:
                dias_cerrada = (ahora - gestion.fecha_gestion).days
                
                ofertas.append({
                    'oferta': oferta_obj.oferta,
                    'concepto': 'RFS',
                    'concepto_anterior': oferta_obj.campos_dinamicos.get('concepto_anterior', ''),
                    'estado': oferta_obj.estado_oferta,
                    'usuario_que_marco': {
                        'login': gestion.usuario_login,
                        'nombre': gestion.usuario_nombre,
                        'profile_id': gestion.usuario_profile_id
                    },
                    'fecha_gestion': gestion.fecha_gestion,
                    'dias_cerrada': dias_cerrada,
                    'gestion': {
                        'accion': accion.nombre_accion,
                        'subaccion': subaccion.nombre_subaccion,
                        'observacion': gestion.observacion or ''
                    },
                    'campos_oferta': oferta_obj.campos_dinamicos
                })

            logger.info(f"Ofertas RFS listadas: {len(ofertas)} de {total_count} total")
            return ofertas, total_count

        except Exception as e:
            logger.error(f"Error al listar ofertas RFS: {e}")
            return [], 0

    def get_resumen_ofertas_especiales(self) -> Dict[str, Any]:
        """
        Obtiene un resumen consolidado de todas las ofertas especiales.
        
        Returns:
            Dict con contadores de cada tipo
        """
        try:
            # Contar pausadas
            count_pausadas = self.db.query(EnlistmentManager).filter(
                and_(
                    EnlistmentManager.estado_oferta == 'EN_TRAMITE_PAUSADO',
                    EnlistmentManager.campos_dinamicos['concepto'].astext == 'OFERTA PAUSADA'
                )
            ).count()

            # Contar MALO
            count_malo = self.db.query(EnlistmentManager).filter(
                and_(
                    EnlistmentManager.estado_oferta == 'CERRADO',
                    EnlistmentManager.campos_dinamicos['concepto'].astext == 'MALO'
                )
            ).count()

            # Contar RFS
            count_rfs = self.db.query(EnlistmentManager).filter(
                and_(
                    EnlistmentManager.estado_oferta == 'CERRADO',
                    EnlistmentManager.campos_dinamicos['concepto'].astext == 'RFS'
                )
            ).count()

            resumen = {
                'pausadas': count_pausadas,
                'malo': count_malo,
                'rfs': count_rfs,
                'total_general': count_pausadas + count_malo + count_rfs
            }

            logger.info(f"Resumen ofertas especiales: {resumen}")
            return resumen

        except Exception as e:
            logger.error(f"Error al obtener resumen ofertas especiales: {e}")
            return {
                'pausadas': 0,
                'malo': 0,
                'rfs': 0,
                'total_general': 0
            }

