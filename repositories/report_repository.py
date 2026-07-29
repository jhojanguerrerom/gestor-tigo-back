"""
Repository para reportes y métricas.
Maneja todas las queries de reportería de forma independiente.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, extract, text, Numeric, case
from sqlalchemy.dialects.postgresql import JSONB
from app.models.oferta_gestion_model import OfertaGestionDetalle, OfertaAccionCatalogo
from app.models.enlistment_manager_model import EnlistmentManagerHistory, EnlistmentManager
from app.db.postgres import SessionLocalPG
from app.db.timezone_types import get_bogota_now

logger = logging.getLogger("report_repository")


# ==========================================
# CONSTANTES: Agrupación de conceptos
# ==========================================
CONCEPTS_ANULAR = ['ANULA', 'ANULA-C', 'ANULA-D']
CONCEPTS_RECONFIGURACION = ['Premisas Extendidas', '14', 'RECONFIGURACION BOT']
CONCEPTS_ASIGNACION = [
    'Cobertura', 'Conservar Numero', 'PETEC', 'PRESI', 'PSIEB', 'PUMED',
    'Reconfigurar por cobertura', 'Verificar Disponibilidad'
]


class ReportRepository:
    """Repository exclusivo para reportes"""

    def __init__(self, db: Session):
        """Inicializa el repository con la sesión de base de datos.
        
        Args:
            db: Sesión de SQLAlchemy inyectada por dependency
        """
        self.db = db

    # ==========================================
    # REPORTE 1: Gestiones por Hora/Asesor
    # ==========================================

    def get_managed_by_hour_today(self) -> List[Dict[str, Any]]:
        """
        Obtiene la cantidad de ofertas gestionadas por hora y asesor del día actual.
        Rango horario: 6:00 AM - 9:00 PM (21:00)
        """
        try:
            today = get_bogota_now().date()

            # Usar func.date_part para extraer la hora en timezone de Colombia
            # Esto asegura resultados consistentes con campos timezone-aware
            query = self.db.query(
                OfertaGestionDetalle.usuario_login,
                OfertaGestionDetalle.usuario_nombre,
                func.date_part('hour', func.timezone('America/Bogota', OfertaGestionDetalle.fecha_gestion)).label('hour'),
                func.count(OfertaGestionDetalle.id).label('quantity')
            ).filter(
                and_(
                    func.date(func.timezone('America/Bogota', OfertaGestionDetalle.fecha_gestion)) == today,
                    func.date_part('hour', func.timezone('America/Bogota', OfertaGestionDetalle.fecha_gestion)) >= 6,
                    func.date_part('hour', func.timezone('America/Bogota', OfertaGestionDetalle.fecha_gestion)) <= 21
                )
            ).group_by(
                OfertaGestionDetalle.usuario_login,
                OfertaGestionDetalle.usuario_nombre,
                func.date_part('hour', func.timezone('America/Bogota', OfertaGestionDetalle.fecha_gestion))
            ).order_by(
                OfertaGestionDetalle.usuario_login,
                func.date_part('hour', func.timezone('America/Bogota', OfertaGestionDetalle.fecha_gestion))
            ).all()

            logger.info(f"Gestiones por hora obtenidas: {len(query)} registros")
            return query

        except Exception as e:
            logger.error(f"Error al obtener gestiones por hora: {e}")
            return []

    def get_effectiveness_by_user_today(self) -> List[Dict[str, Any]]:
        """
        Obtiene efectividad y promedio de conversión por usuario del día actual.
        Calcula: total gestionadas, pasaron a pedido, efectividad %, promedio.
        """
        try:
            today = get_bogota_now().date()

            query = self.db.query(
                OfertaGestionDetalle.usuario_login,
                OfertaGestionDetalle.usuario_nombre,
                func.count(OfertaGestionDetalle.id).label('total_gestionadas'),
                func.sum(
                    case(
                        (OfertaAccionCatalogo.nombre_accion.in_(['Asignado', 'Reconfigurar']), 1),
                        else_=0
                    )
                ).label('pasaron_a_pedido'),
                func.round(
                    (func.sum(
                        case(
                            (OfertaAccionCatalogo.nombre_accion.in_(['Asignado', 'Reconfigurar']), 1),
                            else_=0
                        )
                    ).cast(Numeric) / func.count(OfertaGestionDetalle.id)) * 100,
                    2
                ).label('efectividad_porcentaje'),
                func.round(
                    func.count(OfertaGestionDetalle.id).cast(Numeric) / 
                    func.nullif(
                        func.sum(
                            case(
                                (OfertaAccionCatalogo.nombre_accion.in_(['Asignado', 'Reconfigurar']), 1),
                                else_=0
                            )
                        ),
                        0
                    ),
                    2
                ).label('promedio')
            ).join(
                OfertaAccionCatalogo,
                OfertaGestionDetalle.accion_id == OfertaAccionCatalogo.id
            ).filter(
                func.date(func.timezone('America/Bogota', OfertaGestionDetalle.fecha_gestion)) == today
            ).group_by(
                OfertaGestionDetalle.usuario_login,
                OfertaGestionDetalle.usuario_nombre
            ).all()

            logger.info(f"Efectividad por usuario obtenida: {len(query)} registros")
            if len(query) > 0:
                logger.debug(f"Ejemplo de efectividad: {query[0]}")
            return query

        except Exception as e:
            logger.error(f"Error al obtener efectividad por usuario: {e}")
            return []

    # ==========================================
    # REPORTE 2: Productividad Diaria por Asesor
    # ==========================================

    def get_daily_productivity_by_advisor(
        self, 
        date_from: date, 
        date_to: date
    ) -> List[Dict[str, Any]]:
        """
        Obtiene la productividad diaria de cada asesor en un rango de fechas.
        Retorna: usuario, nombre, profile_id, y gestiones por día.
        """
        try:
            start = datetime.combine(date_from, datetime.min.time())
            end = datetime.combine(date_to, datetime.max.time())

            query = self.db.query(
                OfertaGestionDetalle.usuario_login,
                OfertaGestionDetalle.usuario_nombre,
                OfertaGestionDetalle.usuario_profile_id,
                func.date(func.timezone('America/Bogota', OfertaGestionDetalle.fecha_gestion)).label('date'),
                func.count(OfertaGestionDetalle.id).label('quantity')
            ).filter(
                and_(
                    func.timezone('America/Bogota', OfertaGestionDetalle.fecha_gestion) >= start,
                    func.timezone('America/Bogota', OfertaGestionDetalle.fecha_gestion) <= end
                )
            ).group_by(
                OfertaGestionDetalle.usuario_login,
                OfertaGestionDetalle.usuario_nombre,
                OfertaGestionDetalle.usuario_profile_id,
                func.date(func.timezone('America/Bogota', OfertaGestionDetalle.fecha_gestion))
            ).order_by(
                func.count(OfertaGestionDetalle.id).desc()
            ).all()

            logger.info(f"Productividad diaria obtenida: {len(query)} registros")
            return query

        except Exception as e:
            logger.error(f"Error al obtener productividad diaria: {e}")
            return []

    # ==========================================
    # REPORTE 3: Histórico Ingresos vs Gestiones
    # ==========================================

    def get_historical_income_vs_managed(
        self,
        business_unit: str,
        date_from: date,
        date_to: date,
        concept_group: str = 'ALL'
    ) -> Tuple[List[Tuple], List[Tuple]]:
        """
        Obtiene el histórico de ingresos vs gestiones.
        Retorna: (income_by_day, managed_by_day)
        
        IMPORTANTE: Usa enlistment_manager_history con tipo_operacion='INSERT'
        para contar TODAS las ofertas ingresadas, sin importar su estado actual.
        
        Args:
            business_unit: Filtro por UEN (RESIDENCIAL/EMPRESARIAL/ALL)
            date_from: Fecha inicio
            date_to: Fecha fin
            concept_group: Filtro por agrupación (ANULAR/RECONFIGURACION/ASIGNACION/ALL)
        """
        try:
            start = datetime.combine(date_from, datetime.min.time())
            end = datetime.combine(date_to, datetime.max.time())

            # ============================================
            # Query para INGRESOS (usando history con INSERT)
            # ============================================
            query_income = self.db.query(
                func.date(func.timezone('America/Bogota', EnlistmentManagerHistory.create_date_automation)).label('date'),
                func.count(EnlistmentManagerHistory.id).label('quantity')
            ).filter(
                and_(
                    EnlistmentManagerHistory.tipo_operacion == 'INSERT',
                    func.timezone('America/Bogota', EnlistmentManagerHistory.create_date_automation) >= start,
                    func.timezone('America/Bogota', EnlistmentManagerHistory.create_date_automation) <= end
                )
            )

            # Aplicar filtro de UEN si no es ALL (case-insensitive)
            if business_unit != 'ALL':
                query_income = query_income.filter(
                    func.upper(EnlistmentManagerHistory.campos_dinamicos['uen'].astext) == business_unit.upper()
                )
            
            # Aplicar filtro de agrupación de conceptos para INGRESOS
            if concept_group == 'ANULAR':
                query_income = query_income.filter(
                    EnlistmentManagerHistory.campos_dinamicos['concepto'].astext.in_(CONCEPTS_ANULAR)
                )
            elif concept_group == 'RECONFIGURACION':
                query_income = query_income.filter(
                    EnlistmentManagerHistory.campos_dinamicos['concepto'].astext.in_(CONCEPTS_RECONFIGURACION)
                )
            elif concept_group == 'ASIGNACION':
                query_income = query_income.filter(
                    EnlistmentManagerHistory.campos_dinamicos['concepto'].astext.in_(CONCEPTS_ASIGNACION)
                )

            income = query_income.group_by(
                func.date(func.timezone('America/Bogota', EnlistmentManagerHistory.create_date_automation))
            ).all()

            # ============================================
            # Query para GESTIONES (CON JOIN para filtrar por concepto)
            # ============================================
            query_managed = self.db.query(
                func.date(func.timezone('America/Bogota', OfertaGestionDetalle.fecha_gestion)).label('date'),
                func.count(OfertaGestionDetalle.id).label('quantity')
            ).join(
                EnlistmentManager,
                OfertaGestionDetalle.oferta == EnlistmentManager.oferta
            ).filter(
                and_(
                    func.timezone('America/Bogota', OfertaGestionDetalle.fecha_gestion) >= start,
                    func.timezone('America/Bogota', OfertaGestionDetalle.fecha_gestion) <= end
                )
            )
            
            # Aplicar filtro de UEN si no es ALL (case-insensitive)
            if business_unit != 'ALL':
                query_managed = query_managed.filter(
                    func.upper(EnlistmentManager.campos_dinamicos['uen'].astext) == business_unit.upper()
                )
            
            # Aplicar filtro de agrupación de conceptos para GESTIONES
            if concept_group == 'ANULAR':
                query_managed = query_managed.filter(
                    EnlistmentManager.campos_dinamicos['concepto'].astext.in_(CONCEPTS_ANULAR)
                )
            elif concept_group == 'RECONFIGURACION':
                query_managed = query_managed.filter(
                    EnlistmentManager.campos_dinamicos['concepto'].astext.in_(CONCEPTS_RECONFIGURACION)
                )
            elif concept_group == 'ASIGNACION':
                query_managed = query_managed.filter(
                    EnlistmentManager.campos_dinamicos['concepto'].astext.in_(CONCEPTS_ASIGNACION)
                )
            
            managed = query_managed.group_by(
                func.date(func.timezone('America/Bogota', OfertaGestionDetalle.fecha_gestion))
            ).all()

            logger.info(f"Histórico obtenido - Ingresos: {len(income)}, Gestiones: {len(managed)}, Grupo: {concept_group}")
            return (income, managed)

        except Exception as e:
            logger.error(f"Error al obtener histórico ingresos vs gestiones: {e}")
            return ([], [])

    # ==========================================
    # REPORTE 4: Ingresos por Intervalo de Hora
    # ==========================================

    def get_income_by_hour_interval(
        self, 
        date_from: date,
        date_to: date,
        concept_group: str = 'ALL'
    ) -> List[Tuple]:
        """
        Obtiene la distribución de ingresos por hora.
        - Si es un solo día (date_from == date_to): conteo real por hora
        - Si es rango de días: promedio de ingresos por hora (redondeado a 2 decimales)
        
        Usa enlistment_manager_history con tipo_operacion='INSERT'.
        
        Args:
            date_from: Fecha inicio
            date_to: Fecha fin
            concept_group: Filtro por agrupación (ANULAR/RECONFIGURACION/ASIGNACION/ALL)
        """
        try:
            start = datetime.combine(date_from, datetime.min.time())
            end = datetime.combine(date_to, datetime.max.time())

            # Query base para subquery
            subquery_base = self.db.query(
                func.date(func.timezone('America/Bogota', EnlistmentManagerHistory.create_date_automation)).label('date'),
                func.date_part('hour', func.timezone('America/Bogota', EnlistmentManagerHistory.create_date_automation)).label('hour'),
                func.count(EnlistmentManagerHistory.id).label('quantity')
            ).filter(
                and_(
                    EnlistmentManagerHistory.tipo_operacion == 'INSERT',
                    func.timezone('America/Bogota', EnlistmentManagerHistory.create_date_automation) >= start,
                    func.timezone('America/Bogota', EnlistmentManagerHistory.create_date_automation) <= end
                )
            )
            
            # Aplicar filtro de agrupación de conceptos
            if concept_group == 'ANULAR':
                subquery_base = subquery_base.filter(
                    EnlistmentManagerHistory.campos_dinamicos['concepto'].astext.in_(CONCEPTS_ANULAR)
                )
            elif concept_group == 'RECONFIGURACION':
                subquery_base = subquery_base.filter(
                    EnlistmentManagerHistory.campos_dinamicos['concepto'].astext.in_(CONCEPTS_RECONFIGURACION)
                )
            elif concept_group == 'ASIGNACION':
                subquery_base = subquery_base.filter(
                    EnlistmentManagerHistory.campos_dinamicos['concepto'].astext.in_(CONCEPTS_ASIGNACION)
                )
            
            # Subquery: agrupa por fecha + hora para obtener cantidad por día/hora
            subquery = subquery_base.group_by(
                func.date(func.timezone('America/Bogota', EnlistmentManagerHistory.create_date_automation)),
                func.date_part('hour', func.timezone('America/Bogota', EnlistmentManagerHistory.create_date_automation))
            ).subquery()

            # Query principal: promedio por hora (redondeado a 2 decimales)
            query = self.db.query(
                subquery.c.hour,
                func.round(func.avg(subquery.c.quantity), 2).label('quantity')
            ).group_by(
                subquery.c.hour
            ).order_by(
                subquery.c.hour
            ).all()

            logger.info(f"Ingresos por hora obtenidos: {len(query)} intervalos (rango: {date_from} a {date_to})")
            return query

        except Exception as e:
            logger.error(f"Error al obtener ingresos por hora: {e}")
            return []

    # ==========================================
    # REPORTE 5: Ingresos y Gestiones Diario
    # ==========================================

    def get_daily_income_managed(
        self,
        data_type: str,
        date_from: date,
        date_to: date,
        concept_group: str = 'ALL'
    ) -> Tuple[List[Tuple], List[Tuple]]:
        """
        Obtiene ingresos y/o gestiones por día según el tipo solicitado.
        data_type: INCOME | MANAGED | BOTH
        Retorna: (income_by_day, managed_by_day)
        
        Args:
            data_type: Tipo de datos (INCOME/MANAGED/BOTH)
            date_from: Fecha inicio
            date_to: Fecha fin
            concept_group: Filtro por agrupación (ANULAR/RECONFIGURACION/ASIGNACION/ALL)
        """
        try:
            start = datetime.combine(date_from, datetime.min.time())
            end = datetime.combine(date_to, datetime.max.time())

            income = []
            managed = []

            # Obtener INGRESOS si se solicita
            if data_type in ['INCOME', 'BOTH']:
                query_income = self.db.query(
                    func.date(func.timezone('America/Bogota', EnlistmentManagerHistory.create_date_automation)).label('date'),
                    func.count(EnlistmentManagerHistory.id).label('quantity')
                ).filter(
                    and_(
                        EnlistmentManagerHistory.tipo_operacion == 'INSERT',
                        func.timezone('America/Bogota', EnlistmentManagerHistory.create_date_automation) >= start,
                        func.timezone('America/Bogota', EnlistmentManagerHistory.create_date_automation) <= end
                    )
                )
                
                # Aplicar filtro de agrupación de conceptos
                if concept_group == 'ANULAR':
                    query_income = query_income.filter(
                        EnlistmentManagerHistory.campos_dinamicos['concepto'].astext.in_(CONCEPTS_ANULAR)
                    )
                elif concept_group == 'RECONFIGURACION':
                    query_income = query_income.filter(
                        EnlistmentManagerHistory.campos_dinamicos['concepto'].astext.in_(CONCEPTS_RECONFIGURACION)
                    )
                elif concept_group == 'ASIGNACION':
                    query_income = query_income.filter(
                        EnlistmentManagerHistory.campos_dinamicos['concepto'].astext.in_(CONCEPTS_ASIGNACION)
                    )
                
                income = query_income.group_by(
                    func.date(func.timezone('America/Bogota', EnlistmentManagerHistory.create_date_automation))
                ).all()

            # Obtener GESTIONES si se solicita
            if data_type in ['MANAGED', 'BOTH']:
                query_managed = self.db.query(
                    func.date(func.timezone('America/Bogota', OfertaGestionDetalle.fecha_gestion)).label('date'),
                    func.count(OfertaGestionDetalle.id).label('quantity')
                ).join(
                    EnlistmentManager,
                    OfertaGestionDetalle.oferta == EnlistmentManager.oferta
                ).filter(
                    and_(
                        func.timezone('America/Bogota', OfertaGestionDetalle.fecha_gestion) >= start,
                        func.timezone('America/Bogota', OfertaGestionDetalle.fecha_gestion) <= end
                    )
                )
                
                # Aplicar filtro de agrupación de conceptos
                if concept_group == 'ANULAR':
                    query_managed = query_managed.filter(
                        EnlistmentManager.campos_dinamicos['concepto'].astext.in_(CONCEPTS_ANULAR)
                    )
                elif concept_group == 'RECONFIGURACION':
                    query_managed = query_managed.filter(
                        EnlistmentManager.campos_dinamicos['concepto'].astext.in_(CONCEPTS_RECONFIGURACION)
                    )
                elif concept_group == 'ASIGNACION':
                    query_managed = query_managed.filter(
                        EnlistmentManager.campos_dinamicos['concepto'].astext.in_(CONCEPTS_ASIGNACION)
                    )
                
                managed = query_managed.group_by(
                    func.date(func.timezone('America/Bogota', OfertaGestionDetalle.fecha_gestion))
                ).all()

            logger.info(f"Ingresos/Gestiones diario - Ingresos: {len(income)}, Gestiones: {len(managed)}")
            return (income, managed)

        except Exception as e:
            logger.error(f"Error al obtener ingresos/gestiones diario: {e}")
            return ([], [])

    # ==========================================
    # REPORTE 6: Ingresos por Concepto
    # ==========================================

    def get_income_by_concept_month(
        self,
        month: str,
        concept: Optional[str] = None,
        concept_group: str = 'ALL'
    ) -> List[Tuple]:
        """
        Obtiene ingresos diarios agrupados por concepto dentro de un mes.
        
        Args:
            month: formato 'YYYY-MM'
            concept: filtro opcional para concepto específico
            concept_group: Filtro por agrupación (ANULAR/RECONFIGURACION/ASIGNACION/ALL)
        
        Retorna: [(date, concept, quantity), ...]
        """
        try:
            # Parsear mes
            year, month_num = map(int, month.split('-'))
            start = datetime(year, month_num, 1)
            
            # Calcular último día del mes
            if month_num == 12:
                end = datetime(year + 1, 1, 1) - timedelta(seconds=1)
            else:
                end = datetime(year, month_num + 1, 1) - timedelta(seconds=1)

            query = self.db.query(
                func.date(func.timezone('America/Bogota', EnlistmentManagerHistory.create_date_automation)).label('date'),
                EnlistmentManagerHistory.campos_dinamicos['concepto'].astext.label('concept'),
                func.count(EnlistmentManagerHistory.id).label('quantity')
            ).filter(
                and_(
                    EnlistmentManagerHistory.tipo_operacion == 'INSERT',
                    func.timezone('America/Bogota', EnlistmentManagerHistory.create_date_automation) >= start,
                    func.timezone('America/Bogota', EnlistmentManagerHistory.create_date_automation) <= end,
                    EnlistmentManagerHistory.campos_dinamicos['concepto'].astext.isnot(None)
                )
            )

            # Aplicar filtro de concepto individual si se proporciona
            if concept:
                query = query.filter(
                    EnlistmentManagerHistory.campos_dinamicos['concepto'].astext == concept
                )
            
            # Aplicar filtro de agrupación de conceptos
            if concept_group == 'ANULAR':
                query = query.filter(
                    EnlistmentManagerHistory.campos_dinamicos['concepto'].astext.in_(CONCEPTS_ANULAR)
                )
            elif concept_group == 'RECONFIGURACION':
                query = query.filter(
                    EnlistmentManagerHistory.campos_dinamicos['concepto'].astext.in_(CONCEPTS_RECONFIGURACION)
                )
            elif concept_group == 'ASIGNACION':
                query = query.filter(
                    EnlistmentManagerHistory.campos_dinamicos['concepto'].astext.in_(CONCEPTS_ASIGNACION)
                )

            result = query.group_by(
                func.date(func.timezone('America/Bogota', EnlistmentManagerHistory.create_date_automation)),
                EnlistmentManagerHistory.campos_dinamicos['concepto'].astext
            ).order_by(
                func.date(func.timezone('America/Bogota', EnlistmentManagerHistory.create_date_automation)),
                EnlistmentManagerHistory.campos_dinamicos['concepto'].astext
            ).all()

            logger.info(f"Ingresos por concepto obtenidos: {len(result)} registros")
            return result

        except Exception as e:
            logger.error(f"Error al obtener ingresos por concepto: {e}")
            return []

    def get_available_concepts(self, month: str) -> List[str]:
        """Obtiene la lista de conceptos únicos en un mes"""
        try:
            year, month_num = map(int, month.split('-'))
            start = datetime(year, month_num, 1)
            if month_num == 12:
                end = datetime(year + 1, 1, 1) - timedelta(seconds=1)
            else:
                end = datetime(year, month_num + 1, 1) - timedelta(seconds=1)

            concepts = self.db.query(
                EnlistmentManagerHistory.campos_dinamicos['concepto'].astext
            ).filter(
                and_(
                    EnlistmentManagerHistory.tipo_operacion == 'INSERT',
                    func.timezone('America/Bogota', EnlistmentManagerHistory.create_date_automation) >= start,
                    func.timezone('America/Bogota', EnlistmentManagerHistory.create_date_automation) <= end,
                    EnlistmentManagerHistory.campos_dinamicos['concepto'].astext.isnot(None)
                )
            ).distinct().all()

            return [c[0] for c in concepts if c[0]]

        except Exception as e:
            logger.error(f"Error al obtener conceptos disponibles: {e}")
            return []

    # ==========================================
    # REPORTE 7: Ofertas Disponibles por Concepto
    # ==========================================

    def get_available_offers_by_concept(
        self,
        date_from: Optional[date],
        date_to: Optional[date],
        date_field: str
    ) -> List[Tuple]:
        """
        Obtiene ofertas en estado ABIERTO con cálculo de tiempo transcurrido.
        
        Args:
            date_from: Fecha desde para filtrar
            date_to: Fecha hasta para filtrar
            date_field: 'CRM' o 'GESTOR' - define qué fecha usar
        
        Retorna: [(concepto, oferta, fecha_referencia, minutos_transcurridos), ...]
        """
        try:
            from app.models.enlistment_manager_model import EnlistmentManager
            
            # Construir la expresión de fecha según el campo seleccionado
            if date_field == 'CRM':
                # Convertir string ISO a timestamp: "2026-05-11T07:09:16" -> timestamp
                fecha_expr = func.to_timestamp(
                    EnlistmentManager.campos_dinamicos['fecha_creado'].astext,
                    'YYYY-MM-DD"T"HH24:MI:SS'
                )
            else:  # GESTOR
                fecha_expr = EnlistmentManager.created_at
            
            # Calcular minutos transcurridos
            minutos_expr = func.extract(
                'epoch',
                func.timezone('America/Bogota', func.now()) - fecha_expr
            ) / 60
            
            # Construir query
            query = self.db.query(
                EnlistmentManager.campos_dinamicos['concepto'].astext.label('concepto'),
                EnlistmentManager.oferta.label('oferta'),
                fecha_expr.label('fecha_referencia'),
                minutos_expr.label('minutos_transcurridos')
            ).filter(
                and_(
                    EnlistmentManager.estado_oferta == 'ABIERTO',
                    EnlistmentManager.campos_dinamicos['concepto'].astext.isnot(None)
                )
            )
            
            # Aplicar filtros de fecha si se proporcionan
            if date_from:
                query = query.filter(func.date(fecha_expr) >= date_from)
            if date_to:
                query = query.filter(func.date(fecha_expr) <= date_to)
            
            # Ordenar por concepto y minutos
            query = query.order_by(
                EnlistmentManager.campos_dinamicos['concepto'].astext,
                minutos_expr
            )
            
            results = query.all()
            logger.info(f"Ofertas disponibles obtenidas: {len(results)} registros")
            return results
            
        except Exception as e:
            logger.error(f"Error al obtener ofertas disponibles por concepto: {e}")
            return []

    # ==========================================
    # REPORTE 8: Exportación CSV Cancelaciones
    # ==========================================

    def get_cancellations_for_export(
        self,
        days_back: int = 3
    ) -> List[Tuple]:
        """
        Obtiene ofertas con conceptos de cancelación (ANULA, ANULA-C, ANULA-D)
        para exportación en formato CSV.
        
        Args:
            days_back: Número de días hacia atrás desde hoy
        
        Retorna: [(oferta, concepto, updated_at), ...]
        """
        try:
            cutoff_date = get_bogota_now() - timedelta(days=days_back)
            now = get_bogota_now()

            query = self.db.query(
                EnlistmentManager.oferta,
                EnlistmentManager.campos_dinamicos['concepto'].astext.label('concepto'),
                EnlistmentManager.updated_at
            ).filter(
                and_(
                    EnlistmentManager.updated_at >= cutoff_date,
                    EnlistmentManager.updated_at <= now,
                    EnlistmentManager.estado_oferta == 'ABIERTO',
                    EnlistmentManager.campos_dinamicos['concepto'].astext.in_(['ANULA', 'ANULA-C', 'ANULA-D'])
                )
            ).order_by(
                EnlistmentManager.updated_at.asc()
            ).all()

            logger.info(f"Cancelaciones para export obtenidas: {len(query)} registros")
            return query

        except Exception as e:
            logger.error(f"Error al obtener cancelaciones para export: {e}")
            return []

    # ==========================================
    # REPORTE 9: Liquidación
    # ==========================================

    def get_liquidation_report(
        self,
        date_from: date,
        date_to: date,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> Tuple[List[Any], int]:
        """
        Obtiene reporte de liquidación usando Raw SQL.
        Retorna ofertas cerradas con validación de garantía.
        
        Args:
            date_from: Fecha inicio del periodo
            date_to: Fecha fin del periodo
            limit: Límite de registros (para paginación)
            offset: Offset para paginación
        
        Retorna: (lista_resultados, total_count)
        """
        try:
            # Convertir dates a timestamps
            start_timestamp = datetime.combine(date_from, datetime.min.time())
            end_timestamp = datetime.combine(date_to, datetime.max.time())
            
            # Query base con CTEs (Raw SQL)
            sql_query = text("""
                WITH estados AS (
                    SELECT
                        ohe.oferta,
                        ohe.usuario_login,
                        ohe.usuario_nombre,
                        ohe.fecha_accion AS fecha_asignacion,
                        LEAD(ohe.fecha_accion) OVER (PARTITION BY ohe.oferta ORDER BY ohe.fecha_accion) AS fecha_gestion,
                        LEAD(ohe.estado_nuevo) OVER (PARTITION BY ohe.oferta ORDER BY ohe.fecha_accion) AS siguiente_estado
                    FROM oferta_historico_estados ohe
                    WHERE ohe.fecha_accion >= :start_date AND ohe.fecha_accion < :end_date
                ),
                cierres AS (
                    SELECT
                        oferta,
                        usuario_login,
                        usuario_nombre,
                        fecha_asignacion,
                        fecha_gestion
                    FROM estados
                    WHERE siguiente_estado = 'CERRADO' AND fecha_gestion IS NOT NULL
                ),
                gestiones_match AS (
                    SELECT
                        c.oferta,
                        c.usuario_login,
                        c.usuario_nombre,
                        c.fecha_asignacion,
                        c.fecha_gestion,
                        oac.nombre_accion,
                        osc.nombre_subaccion,
                        ogd.observacion,
                        ogd.fecha_gestion AS fecha_gestion_detalle,
                        ABS(EXTRACT(EPOCH FROM (c.fecha_gestion - ogd.fecha_gestion))) * 1000 AS diferencia_ms,
                        ROW_NUMBER() OVER (PARTITION BY c.oferta, c.fecha_gestion ORDER BY ABS(EXTRACT(EPOCH FROM (c.fecha_gestion - ogd.fecha_gestion)))) AS rn
                    FROM cierres c
                    LEFT JOIN oferta_gestion_detalle ogd ON ogd.oferta = c.oferta 
                        AND ogd.fecha_gestion BETWEEN c.fecha_gestion - INTERVAL '1 second' AND c.fecha_gestion + INTERVAL '1 second'
                    LEFT JOIN oferta_accion_catalogo oac ON oac.id = ogd.accion_id
                    LEFT JOIN oferta_subaccion_catalogo osc ON osc.id = ogd.subaccion_id
                ),
                resultado AS (
                    SELECT
                        em.oferta,
                        gm.usuario_login,
                        gm.usuario_nombre,
                        cd.concepto,
                        cd.producto,
                        cd.uen,
                        cd.regional,
                        cd.documento,
                        cd.pedido_id,
                        cd.tecnologia,
                        cd.garantia,
                        cd.departamento,
                        cd.tipo_scoring,
                        cd.tipo_trabajo,
                        cd.fecha_creado,
                        cd.descripcion,
                        cd.estado_direccion,
                        em.estado_oferta,
                        cd.estado_pendiente,
                        cd.estado_scoring,
                        cd.fecha_estado,
                        cd.fecha_pendiente,
                        cd.megagold,
                        cd.municipio,
                        cd.pedido_crm,
                        cd.usuario_pendiente,
                        gm.fecha_asignacion,
                        gm.fecha_gestion,
                        gm.nombre_accion,
                        gm.nombre_subaccion,
                        gm.observacion,
                        case
                            when cd.concepto IN('ANULA', 'ANULA-C', 'ANULA-D') then 'ANULAR'
                            when cd.concepto IN('Premisas Extendidas', '14', 'RECONFIGURACION BOT') then 'RECONFIGURACION'
                            when cd.concepto IN('Cobertura', 'Conservar Numero', 'PETEC', 'PRESI', 'PSIEB', 'PUMED', 'Reconfigurar por cobertura', 'Verificar Disponibilidad','Pendiente Provisión') then 'ASIGNACION'
                            else null
                        end as concepto_grupo
                    FROM gestiones_match gm
                    INNER JOIN enlistment_manager em ON em.oferta = gm.oferta
                    CROSS JOIN LATERAL jsonb_to_record(em.campos_dinamicos) AS cd(
                        concepto text,
                        departamento text,
                        descripcion text,
                        documento text,
                        estado_direccion text,
                        estado_pendiente text,
                        estado_scoring text,
                        fecha_creado text,
                        fecha_estado text,
                        fecha_pendiente text,
                        garantia text,
                        megagold text,
                        municipio text,
                        pedido_crm text,
                        pedido_id text,
                        producto text,
                        regional text,
                        tecnologia text,
                        tipo_scoring text,
                        tipo_trabajo text,
                        uen text,
                        usuario_pendiente text
                    )
                    WHERE gm.rn = 1
                )
                SELECT
                    r.*,
                    CASE
                        WHEN COUNT(*) OVER (PARTITION BY r.oferta) = 1 THEN 'NO GARANTIA'
                        WHEN ROW_NUMBER() OVER (
                                PARTITION BY r.oferta
                                ORDER BY r.fecha_gestion DESC
                             ) = 1 THEN 'NO GARANTIA'
                        ELSE 'SI GARANTIA'
                    END AS validacion_garantia
                FROM resultado r
                ORDER BY r.oferta, r.fecha_gestion DESC
            """)
            
            # Ejecutar query para datos
            params = {
                'start_date': start_timestamp,
                'end_date': end_timestamp
            }
            
            result = self.db.execute(sql_query, params)
            all_rows = result.fetchall()
            
            total_count = len(all_rows)
            
            # Aplicar paginación si se especifica
            if limit is not None and offset is not None:
                paginated_rows = all_rows[offset:offset + limit]
            else:
                paginated_rows = all_rows
            
            logger.info(f"Liquidación obtenida: {len(paginated_rows)} de {total_count} registros")
            return paginated_rows, total_count

        except Exception as e:
            logger.error(f"Error al obtener reporte de liquidación: {e}")
            raise

    # ==========================================
    # REPORTES EMTELCO
    # ==========================================
    def get_history_activation_gestor_v1(
        self,
        date_from: date,
        date_to: date,
    ) -> Tuple[List[Any], int]:
        """
        Obtiene reporte de historico de activación usando Raw SQL.
        
        Args:
            date_from: Fecha inicio del periodo
            date_to: Fecha fin del periodo
        
        Retorna: (lista_resultados, total_count)
        """
        try:
            # Convertir dates a timestamps
            start_timestamp = datetime.combine(date_from, datetime.min.time())
            end_timestamp = datetime.combine(date_to, datetime.max.time())
            
            # Query base con CTEs (Raw SQL)
            sql_query = text("""
                SELECT 
                DISTINCT ASESOR AS login_gestion, 
                PEDIDO AS Pedido, 
                OBSERVACION AS Tarea, 
                STR_TO_DATE(fecha_gestion, '%Y-%m-%d %H:%i:%s') AS Hora_Ingreso, 
                STR_TO_DATE(fecha_inicio, '%Y-%m-%d %H:%i:%s') AS Hora_Inicio, 
                STR_TO_DATE(fecha_fin, '%Y-%m-%d %H:%i:%s') AS Hora_Fin, 
                aplicativo AS fuente, 
                producto AS Accion, 
                transaccion AS Sub_Accion
                FROM portalbd.gestor_historico_activacion
                WHERE FECHA_GESTION BETWEEN :start_date AND :end_date AND PEDIDO IS NOT NULL AND TRIM(PEDIDO) != ''
                ORDER BY FECHA_GESTION ASC;
            """)
            
            # Ejecutar query para datos
            params = {
                'start_date': start_timestamp,
                'end_date': end_timestamp
            }
            
            result = self.db.execute(sql_query, params)
            all_rows = result.fetchall()
            
            total_count = len(all_rows)
            
            # Aplicar paginación si se especifica
            paginated_rows = all_rows
            
            logger.info(f"Historico activacion obtenida: {len(paginated_rows)} de {total_count} registros")
            return paginated_rows, total_count

        except Exception as e:
            logger.error(f"Error al obtener reporte de liquidación: {e}")
            raise

