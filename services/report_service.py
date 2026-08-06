"""
Service para reportes.
Contiene la lógica de negocio y transformación de datos.
"""

import logging
import calendar
import csv
import io
from typing import Dict, Any, List, Optional, Union, Tuple
from datetime import date, timedelta, datetime
from collections import defaultdict
from sqlalchemy.orm import Session
from app.repositories.report_repository import ReportRepository

logger = logging.getLogger("report_service")


class ReportService:
    """Service exclusivo para reportes"""

    def __init__(self, db: Session):
        """Inicializa el service con la sesión de base de datos.
        
        Args:
            db: Sesión de SQLAlchemy inyectada por dependency
        """
        self.db = db
        self.repository = ReportRepository(db)

    # ==========================================
    # REPORTE 1: Gestiones por Hora/Asesor
    # ==========================================

    def get_managed_by_hour_today(self) -> Dict[str, Any]:
        """
        Procesa y estructura las gestiones por hora del día actual.
        Incluye efectividad y promedio de conversión por asesor.
        Retorna estructura lista para frontend.
        """
        try:
            # Query 1: Gestiones por hora
            results = self.repository.get_managed_by_hour_today()
            
            # Query 2: Efectividad por usuario
            effectiveness_results = self.repository.get_effectiveness_by_user_today()
            
            # Estructurar datos por usuario
            users_data = {}
            total_offers = 0

            for row in results:
                user_login = row.usuario_login
                user_name = row.usuario_nombre
                hour = str(int(row.hour))
                quantity = row.quantity

                if user_login not in users_data:
                    users_data[user_login] = {
                        'user_login': user_login,
                        'user_name': user_name,
                        'hours': {str(h): 0 for h in range(6, 22)},  # 6 AM - 9 PM
                        'total_user': 0,
                        'passed_to_order': 0,
                        'effectiveness_percentage': 0.0,
                        'average_ratio': None
                    }

                users_data[user_login]['hours'][hour] = quantity
                users_data[user_login]['total_user'] += quantity
                total_offers += quantity

            # Agregar datos de efectividad
            for row in effectiveness_results:
                user_login = row.usuario_login
                if user_login in users_data:
                    users_data[user_login]['passed_to_order'] = int(row.pasaron_a_pedido or 0)
                    users_data[user_login]['effectiveness_percentage'] = float(row.efectividad_porcentaje or 0.0)
                    users_data[user_login]['average_ratio'] = float(row.promedio) if row.promedio is not None else None

            return {
                'date': date.today(),
                'total_offers': total_offers,
                'data': list(users_data.values())
            }

        except Exception as e:
            logger.error(f"Error en service gestiones por hora: {e}")
            raise

    # ==========================================
    # REPORTE 2: Productividad Diaria por Asesor
    # ==========================================

    def get_daily_productivity_by_advisor(
        self,
        date_from: date,
        date_to: date
    ) -> Dict[str, Any]:
        """
        Procesa y estructura la productividad diaria por asesor.
        """
        try:
            results = self.repository.get_daily_productivity_by_advisor(
                date_from, date_to
            )

            # Agrupar por usuario
            users_data = {}
            total_managed = 0

            for row in results:
                user_login = row.usuario_login

                if user_login not in users_data:
                    users_data[user_login] = {
                        'user_login': user_login,
                        'user_name': row.usuario_nombre,
                        'user_profile_id': row.usuario_profile_id,
                        'total_managed': 0,
                        'managed_by_day': {}  # Usar dict temporal para fácil actualización
                    }

                # Usar dict para fácil actualización
                users_data[user_login]['managed_by_day'][row.date] = row.quantity
                users_data[user_login]['total_managed'] += row.quantity
                total_managed += row.quantity

            # Generar TODAS las fechas del rango
            all_dates = []
            current_date = date_from
            while current_date <= date_to:
                all_dates.append(current_date)
                current_date += timedelta(days=1)

            # Calcular promedios y completar managed_by_day con todas las fechas
            days_range = (date_to - date_from).days + 1
            for user_data in users_data.values():
                user_data['daily_average'] = round(
                    user_data['total_managed'] / days_range, 2
                )
                
                # Convertir dict a lista con TODAS las fechas (ya ordenadas ASC)
                managed_by_day_list = []
                for target_date in all_dates:
                    managed_by_day_list.append({
                        'date': target_date,
                        'quantity': user_data['managed_by_day'].get(target_date, 0)
                    })
                
                user_data['managed_by_day'] = managed_by_day_list

            return {
                'date_from': date_from,
                'date_to': date_to,
                'total_managed': total_managed,
                'data': list(users_data.values())
            }

        except Exception as e:
            logger.error(f"Error en service productividad diaria: {e}")
            raise

    # ==========================================
    # REPORTE 3: Histórico Ingresos vs Gestiones
    # ==========================================

    def get_historical_income_vs_managed(
        self,
        business_unit: str,
        date_from: date,
        date_to: date,
        concept_group: str = 'ALL'
    ) -> Dict[str, Any]:
        """
        Procesa el histórico comparativo de ingresos vs gestiones.
        Valida rango máximo de 2 meses.
        
        Args:
            business_unit: Filtro por UEN
            date_from: Fecha inicio
            date_to: Fecha fin
            concept_group: Filtro por agrupación (ANULAR/RECONFIGURACION/ASIGNACION/ALL)
        """
        try:
            # Validar rango máximo de 2 meses
            days_diff = (date_to - date_from).days
            if days_diff > 60:
                raise ValueError("El rango de fechas no puede superar los 2 meses (60 días)")

            income, managed = self.repository.get_historical_income_vs_managed(
                business_unit, date_from, date_to, concept_group
            )

            # Convertir a diccionarios para fácil acceso
            income_dict = {row.date: row.quantity for row in income}
            managed_dict = {row.date: row.quantity for row in managed}

            # Generar TODAS las fechas del rango (incluyendo días sin datos)
            all_dates = []
            current_date = date_from
            while current_date <= date_to:
                all_dates.append(current_date)
                current_date += timedelta(days=1)
            
            data = []
            total_income = 0
            total_managed = 0

            for target_date in all_dates:
                inc = income_dict.get(target_date, 0)
                man = managed_dict.get(target_date, 0)
                
                data.append({
                    'date': target_date,
                    'income': inc,
                    'managed': man
                })
                
                total_income += inc
                total_managed += man

            return {
                'business_unit': business_unit,
                'date_from': date_from,
                'date_to': date_to,
                'total_income': total_income,
                'total_managed': total_managed,
                'data': data
            }

        except Exception as e:
            logger.error(f"Error en service histórico ingresos vs gestiones: {e}")
            raise

    # ==========================================
    # REPORTE 4: Ingresos por Intervalo de Hora
    # ==========================================

    def get_income_by_hour_interval(
        self,
        date_from: date,
        date_to: date,
        concept_group: str = 'ALL'
    ) -> Dict[str, Any]:
        """
        Procesa la distribución de ingresos por hora.
        - Si es un solo día: conteo real
        - Si es rango: promedio por hora
        Retorna todas las horas (0-23) con cantidad 0 si no hay datos.
        Valida rango máximo de 30 días.
        
        Args:
            date_from: Fecha inicio
            date_to: Fecha fin
            concept_group: Filtro por agrupación (ANULAR/RECONFIGURACION/ASIGNACION/ALL)
        """
        try:
            # Validar rango máximo de 30 días
            days_diff = (date_to - date_from).days
            if days_diff > 30:
                raise ValueError("El rango de fechas no puede superar los 30 días")

            results = self.repository.get_income_by_hour_interval(date_from, date_to, concept_group)

            # Inicializar todas las horas con 0.0
            hours_data = {h: 0.0 for h in range(24)}
            
            # Rellenar con datos reales
            total_income = 0.0
            for row in results:
                hour = int(row.hour)
                quantity = float(row.quantity)
                hours_data[hour] = quantity
                total_income += quantity

            # Convertir a lista para response
            data = [{'hour': h, 'quantity': hours_data[h]} for h in range(24)]

            # Determinar si es promedio (más de un día)
            is_average = date_from != date_to

            return {
                'date_from': date_from,
                'date_to': date_to,
                'is_average': is_average,
                'total_income': round(total_income, 2),
                'data': data
            }

        except Exception as e:
            logger.error(f"Error en service ingresos por hora: {e}")
            raise

    # ==========================================
    # REPORTE 5: Ingresos y Gestiones Diario
    # ==========================================

    def get_daily_income_managed(
        self,
        data_type: str,
        date_from: date,
        date_to: date,
        concept_group: str = 'ALL'
    ) -> Dict[str, Any]:
        """
        Procesa ingresos y/o gestiones diarios según el tipo solicitado.
        
        Args:
            data_type: Tipo de datos (INCOME/MANAGED/BOTH)
            date_from: Fecha inicio
            date_to: Fecha fin
            concept_group: Filtro por agrupación (ANULAR/RECONFIGURACION/ASIGNACION/ALL)
        """
        try:
            income, managed = self.repository.get_daily_income_managed(
                data_type, date_from, date_to, concept_group
            )

            # Convertir a diccionarios
            income_dict = {row.date: row.quantity for row in income}
            managed_dict = {row.date: row.quantity for row in managed}

            # Generar todas las fechas del rango
            all_dates = []
            current_date = date_from
            while current_date <= date_to:
                all_dates.append(current_date)
                current_date += timedelta(days=1)

            data = []
            for target_date in all_dates:
                record = {'date': target_date}
                
                if data_type in ['INCOME', 'BOTH']:
                    record['income'] = income_dict.get(target_date, 0)
                
                if data_type in ['MANAGED', 'BOTH']:
                    record['managed'] = managed_dict.get(target_date, 0)
                
                data.append(record)

            return {
                'data_type': data_type,
                'date_from': date_from,
                'date_to': date_to,
                'data': data
            }

        except Exception as e:
            logger.error(f"Error en service ingresos/gestiones diario: {e}")
            raise

    # ==========================================
    # REPORTE 6: Ingresos por Concepto
    # ==========================================

    def get_income_by_concept_month(
        self,
        month: str,
        concept: Optional[str] = None,
        concept_group: str = 'ALL'
    ) -> Dict[str, Any]:
        """
        Procesa ingresos diarios agrupados por concepto.
        
        Args:
            month: Formato YYYY-MM
            concept: Filtro opcional por concepto individual
            concept_group: Filtro por agrupación (ANULAR/RECONFIGURACION/ASIGNACION/ALL)
        """
        try:
            # Validar formato de mes
            if len(month.split('-')) != 2:
                raise ValueError("Formato de mes inválido. Use YYYY-MM")

            results = self.repository.get_income_by_concept_month(month, concept, concept_group)
            available_concepts = self.repository.get_available_concepts(month)

            # Calcular rango completo del mes
            year, month_num = map(int, month.split('-'))
            last_day = calendar.monthrange(year, month_num)[1]

            # Determinar qué conceptos mostrar según el filtro
            if concept:
                # Si se filtró por concepto específico, mostrar solo ese
                concepts_to_show = [concept]
            else:
                # Si no hay filtro, mostrar todos los conceptos disponibles
                concepts_to_show = available_concepts

            # Inicializar estructura: todos los días con conceptos filtrados en 0
            dates_data = {}
            for day in range(1, last_day + 1):
                target_date = date(year, month_num, day)
                # Inicializar solo los conceptos que se deben mostrar
                dates_data[target_date] = {concept_name: 0 for concept_name in concepts_to_show}

            # Sobrescribir con datos reales
            total_income = 0
            for row in results:
                target_date = row.date
                concept_value = row.concept
                quantity = row.quantity
                
                # Solo actualizar si la fecha está en el rango del mes
                # Y si el concepto está en los que se deben mostrar
                if target_date in dates_data and concept_value in dates_data[target_date]:
                    dates_data[target_date][concept_value] = quantity
                    total_income += quantity

            # Convertir a lista ordenada
            data = []
            for target_date in sorted(dates_data.keys()):
                data.append({
                    'date': target_date,
                    'concepts': dates_data[target_date]
                })

            return {
                'month': month,
                'concept_filter': concept,
                'total_income': total_income,
                'available_concepts': sorted(available_concepts),
                'data': data
            }

        except Exception as e:
            logger.error(f"Error en service ingresos por concepto: {e}")
            raise

    # ==========================================
    # REPORTE 7: Ofertas Disponibles por Concepto
    # ==========================================

    def get_available_offers_by_concept(
        self,
        date_from: Optional[date],
        date_to: Optional[date],
        date_field: str,
        export_format: str
    ) -> Union[Dict, Tuple[bytes, str]]:
        """
        Procesa ofertas disponibles por concepto e intervalo de tiempo.
        Retorna JSON o archivo CSV/XLS según export_format.
        """
        try:
            # Obtener datos del repository
            results = self.repository.get_available_offers_by_concept(
                date_from, date_to, date_field
            )
            
            if not results:
                # Si no hay resultados, retornar estructura vacía
                empty_intervals = {
                    "0_30m": 0, "31_60m": 0, "1_2h": 0, "3_5h": 0,
                    "5_7h": 0, "7_12h": 0, "12_24h": 0, "24_48h": 0, "more_48h": 0
                }
                
                if export_format == "JSON":
                    return {
                        'date_field': date_field,
                        'date_from': date_from,
                        'date_to': date_to,
                        'total_offers': 0,
                        'data': [],
                        'totals': {
                            'concept': 'TOTALES',
                            'total': 0,
                            'intervals': empty_intervals
                        }
                    }
                else:  # CSV
                    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                    return (b"", f"ofertas_disponibles_{timestamp}.csv")
            
            # Estructurar datos por concepto
            concepts_data = defaultdict(lambda: {
                '0_30m': 0, '31_60m': 0, '1_2h': 0, '3_5h': 0,
                '5_7h': 0, '7_12h': 0, '12_24h': 0, '24_48h': 0, 'more_48h': 0
            })
            
            detail_data = []  # Para exportación
            
            for row in results:
                concepto = row.concepto
                oferta = row.oferta
                fecha_ref = row.fecha_referencia
                minutos = row.minutos_transcurridos
                
                # Clasificar en intervalo
                interval = self._classify_interval(minutos)
                concepts_data[concepto][interval] += 1
                
                # Guardar detalle para exportación
                detail_data.append({
                    'concepto': concepto,
                    'oferta': oferta,
                    'fecha_creado': fecha_ref,
                    'minutos_transcurridos': round(minutos, 2),
                    'intervalo': interval
                })
            
            # Calcular totales generales
            totals = {
                '0_30m': 0, '31_60m': 0, '1_2h': 0, '3_5h': 0,
                '5_7h': 0, '7_12h': 0, '12_24h': 0, '24_48h': 0, 'more_48h': 0
            }
            
            total_offers = 0
            data = []
            
            for concepto in sorted(concepts_data.keys()):
                intervals = concepts_data[concepto]
                concept_total = sum(intervals.values())
                total_offers += concept_total
                
                # Acumular totales
                for interval_key in totals.keys():
                    totals[interval_key] += intervals[interval_key]
                
                data.append({
                    'concept': concepto,
                    'total': concept_total,
                    'intervals': intervals
                })
            
            # Preparar response según formato
            if export_format == "JSON":
                return {
                    'date_field': date_field,
                    'date_from': date_from,
                    'date_to': date_to,
                    'total_offers': total_offers,
                    'data': data,
                    'totals': {
                        'concept': 'TOTALES',
                        'total': total_offers,
                        'intervals': totals
                    }
                }
            else:  # CSV
                csv_content = self._generate_csv(detail_data)
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                filename = f"ofertas_disponibles_{timestamp}.csv"
                return (csv_content, filename)
                
        except Exception as e:
            logger.error(f"Error en service ofertas disponibles por concepto: {e}")
            raise

    def _classify_interval(self, minutes: float) -> str:
        """Clasifica tiempo transcurrido en intervalos"""
        if minutes <= 30:
            return "0_30m"
        elif minutes <= 60:
            return "31_60m"
        elif minutes <= 120:
            return "1_2h"
        elif minutes <= 300:  # 5 horas
            return "3_5h"
        elif minutes <= 420:  # 7 horas
            return "5_7h"
        elif minutes <= 720:  # 12 horas
            return "7_12h"
        elif minutes <= 1440:  # 24 horas
            return "12_24h"
        elif minutes <= 2880:  # 48 horas
            return "24_48h"
        else:
            return "more_48h"

    def _generate_csv(self, detail_data: List[Dict]) -> str:
        """Genera contenido CSV con detalle de ofertas"""
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Headers
        writer.writerow(['Concepto', 'Oferta', 'Fecha Creado', 'Tiempo Transcurrido (min)', 'Intervalo'])
        
        # Mapeo de intervalos para display
        interval_display = {
            '0_30m': '0-30m',
            '31_60m': '31-60m',
            '1_2h': '1-2h',
            '3_5h': '3-5h',
            '5_7h': '5-7h',
            '7_12h': '7-12h',
            '12_24h': '12-24h',
            '24_48h': '24-48h',
            'more_48h': 'Más de 48h'
        }
        
        # Datos
        for row in detail_data:
            writer.writerow([
                row['concepto'],
                row['oferta'],
                row['fecha_creado'].strftime('%Y-%m-%d %H:%M:%S') if hasattr(row['fecha_creado'], 'strftime') else str(row['fecha_creado']),
                row['minutos_transcurridos'],
                interval_display.get(row['intervalo'], row['intervalo'])
            ])
        
        return output.getvalue()

    # ==========================================
    # REPORTE 8: Exportación CSV Cancelaciones
    # ==========================================

    def generate_cancellations_csv(self, days_back: int = 3) -> str:
        """
        Genera CSV de ofertas canceladas (ANULA, ANULA-C, ANULA-D, ANULA-N).
        
        Args:
            days_back: Días hacia atrás desde hoy
        
        Retorna: String CSV codificado en UTF-8
        """
        try:
            # Mapeos de concepto a valores de salida
            motivo_map = {
                'ANULA': 'Garantia en el ingreso',
                'ANULA-C': 'Garantia en el ingreso',
                'ANULA-D': 'Motivo tecnico',
                'ANULA-N': 'Garantía en el Ingreso'
            }
            
            observaciones_map = {
                'ANULA': 'Inconsistencia en el flujo',
                'ANULA-C': 'Inconsistencia en el flujo',
                'ANULA-D': 'Anulado por disponibilidad tecnica',
                'ANULA-N': 'Sintaxis incorrecta o Municipio no activo'
            }
            
            # Obtener datos del repository
            results = self.repository.get_cancellations_for_export(days_back)
            
            # Fecha de registro (fecha actual)
            fe_registro = datetime.now().strftime('%d/%m/%Y')
            
            # Construir CSV
            output = io.StringIO()
            writer = csv.writer(output, delimiter=',', quoting=csv.QUOTE_MINIMAL)
            
            # Headers (12 columnas según especificación)
            writer.writerow([
                'Oferta Economica',
                'Motivo_cancelacion',
                'ORIGEN',
                'OBSERVACIONES',
                'FE_REGISTRO',
                'Reference',
                'Gestion',
                'Ultima_hora_modificacion',
                'oferta_economica',
                'num_pedido',
                'observacion_rpa',
                'Priority'
            ])
            
            # Datos
            for row in results:
                oferta = row.oferta
                concepto = row.concepto
                motivo = motivo_map.get(concepto, '')
                observaciones = observaciones_map.get(concepto, '')
                
                writer.writerow([
                    oferta,              # Oferta Economica
                    motivo,              # Motivo_cancelacion
                    'Premisas',          # ORIGEN
                    observaciones,       # OBSERVACIONES
                    fe_registro,         # FE_REGISTRO
                    oferta,              # Reference
                    '',                  # Gestion
                    '',                  # Ultima_hora_modificacion
                    '',                  # oferta_economica
                    '',                  # num_pedido
                    '',                  # observacion_rpa
                    'Normal'             # Priority
                ])
            
            logger.info(f"CSV de cancelaciones generado: {len(results)} registros")
            return output.getvalue()
            
        except Exception as e:
            logger.error(f"Error al generar CSV de cancelaciones: {e}")
            raise

    # ==========================================
    # REPORTE 9: Liquidación
    # ==========================================

    def get_liquidation_report(
        self,
        date_from: date,
        date_to: date,
        page: int = 1,
        page_size: int = 100
    ) -> Dict[str, Any]:
        """
        Obtiene reporte de liquidación con paginación.
        
        Args:
            date_from: Fecha inicio
            date_to: Fecha fin
            page: Número de página (para JSON)
            page_size: Tamaño de página (para JSON)
        
        Retorna: Diccionario con datos paginados
        """
        try:
            # Calcular offset
            offset = (page - 1) * page_size
            
            # Obtener datos paginados
            rows, total_count = self.repository.get_liquidation_report(
                date_from=date_from,
                date_to=date_to,
                limit=page_size,
                offset=offset
            )
            
            # Calcular total de páginas
            total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 0
            
            # Convertir rows a diccionarios
            data = []
            for row in rows:
                data.append({
                    'oferta': row.oferta,
                    'usuario_login': row.usuario_login,
                    'usuario_nombre': row.usuario_nombre,
                    'concepto': row.concepto,
                    'producto': row.producto,
                    'uen': row.uen,
                    'regional': row.regional,
                    'documento': row.documento,
                    'pedido_id': row.pedido_id,
                    'tecnologia': row.tecnologia,
                    'garantia': row.garantia,
                    'departamento': row.departamento,
                    'tipo_scoring': row.tipo_scoring,
                    'tipo_trabajo': row.tipo_trabajo,
                    'fecha_creado': row.fecha_creado,
                    'descripcion': row.descripcion,
                    'direccion': row.direccion,
                    'latitud': row.latitud,
                    'longitud': row.longitud,
                    'estado_direccion': row.estado_direccion,
                    'estado_oferta': row.estado_oferta,
                    'estado_pendiente': row.estado_pendiente,
                    'estado_scoring': row.estado_scoring,
                    'fecha_estado': row.fecha_estado,
                    'fecha_pendiente': row.fecha_pendiente,
                    'megagold': row.megagold,
                    'municipio': row.municipio,
                    'pedido_crm': row.pedido_crm,
                    'usuario_pendiente': row.usuario_pendiente,
                    'fecha_ingreso_gestor': row.fecha_ingreso_gestor,
                    'fecha_asignacion': row.fecha_asignacion,
                    'fecha_gestion': row.fecha_gestion,
                    'nombre_accion': row.nombre_accion,
                    'nombre_subaccion': row.nombre_subaccion,
                    'observacion': row.observacion,
                    'concepto_grupo': row.concepto_grupo,
                    'validacion_garantia': row.validacion_garantia
                })
            
            return {
                'date_from': date_from,
                'date_to': date_to,
                'total_records': total_count,
                'page': page,
                'page_size': page_size,
                'total_pages': total_pages,
                'data': data
            }
            
        except Exception as e:
            logger.error(f"Error en service liquidación: {e}")
            raise

    def generate_liquidation_csv(
        self,
        date_from: date,
        date_to: date
    ) -> str:
        """
        Genera CSV completo de liquidación (sin paginación).
        
        Args:
            date_from: Fecha inicio
            date_to: Fecha fin
        
        Retorna: String CSV
        """
        try:
            # Obtener todos los registros (sin paginación)
            rows, _ = self.repository.get_liquidation_report(
                date_from=date_from,
                date_to=date_to,
                limit=None,
                offset=None
            )
            
            # Construir CSV
            output = io.StringIO()
            writer = csv.writer(output, delimiter=',', quoting=csv.QUOTE_MINIMAL)
            
            # Headers (32 columnas)
            writer.writerow([
                'Oferta',
                'Usuario Login',
                'Usuario Nombre',
                'Concepto',
                'Producto',
                'UEN',
                'Regional',
                'Documento',
                'Pedido ID',
                'Tecnologia',
                'Garantia',
                'Departamento',
                'Tipo Scoring',
                'Tipo Trabajo',
                'Fecha Creado',
                'Descripcion',
                'Direccion',
                'Latitud',
                'Longitud',
                'Estado Direccion',
                'Estado Oferta',
                'Estado Pendiente',
                'Estado Scoring',
                'Fecha Estado',
                'Fecha Pendiente',
                'Megagold',
                'Municipio',
                'Pedido CRM',
                'Usuario Pendiente',
                'Fecha Asignacion',
                'Fecha Gestion',
                'Nombre Accion',
                'Nombre Subaccion',
                'Observacion',
                'Concepto Grupo',
                'Validacion Garantia'
            ])
            
            # Datos
            for row in rows:
                writer.writerow([
                    row.oferta,
                    row.usuario_login,
                    row.usuario_nombre,
                    row.concepto or '',
                    row.producto or '',
                    row.uen or '',
                    row.regional or '',
                    row.documento or '',
                    row.pedido_id or '',
                    row.tecnologia or '',
                    row.garantia or '',
                    row.departamento or '',
                    row.tipo_scoring or '',
                    row.tipo_trabajo or '',
                    row.fecha_creado or '',
                    row.descripcion or '',
                    row.direccion or '',
                    row.latitud or '',
                    row.longitud or '',
                    row.estado_direccion or '',
                    row.estado_oferta,
                    row.estado_pendiente or '',
                    row.estado_scoring or '',
                    row.fecha_estado or '',
                    row.fecha_pendiente or '',
                    row.megagold or '',
                    row.municipio or '',
                    row.pedido_crm or '',
                    row.usuario_pendiente or '',
                    row.fecha_ingreso_gestor.strftime('%Y-%m-%d %H:%M:%S') if row.fecha_ingreso_gestor else '',
                    row.fecha_asignacion.strftime('%Y-%m-%d %H:%M:%S') if row.fecha_asignacion else '',
                    row.fecha_gestion.strftime('%Y-%m-%d %H:%M:%S') if row.fecha_gestion else '',
                    row.nombre_accion or '',
                    row.nombre_subaccion or '',
                    row.observacion or '',
                    row.concepto_grupo or '',
                    row.validacion_garantia
                ])
            
            logger.info(f"CSV de liquidación generado: {len(rows)} registros")
            return output.getvalue()
            
        except Exception as e:
            logger.error(f"Error al generar CSV de liquidación: {e}")
            raise

    # ==========================================
    # REPORTES EMTELCO
    # ==========================================
    
    def get_history_activation_gestor_v1(
        self,
        date_from: date,
        date_to: date,
    ) -> Dict[str, Any]:
        """
        Obtiene reporte de historial de activacion gestor v1.
        
        Args:
            date_from: Fecha inicio
            date_to: Fecha fin

        Retorna: Diccionario con datos
        """
        try:
            
            # Obtener datos paginados
            rows, _ = self.repository.get_history_activation_gestor_v1(
                date_from=date_from,
                date_to=date_to,
            )

            # Convertir rows a diccionarios
            data = []
            for row in rows:
                data.append({
                    'login_gestion': row.login_gestion,
                    'pedido': row.Pedido,
                    'tarea': row.Tarea,
                    'hora_ingreso': row.Hora_Ingreso,
                    'hora_inicio': row.Hora_Inicio,
                    'hora_fin': row.Hora_Fin,
                    'fuente': row.fuente,
                    'accion': row.Accion,
                    'sub_accion': row.Sub_Accion,
                })
            
            return {
                'type': 'success',
                'message': {
                    'historicActivation': data,                    
                }
            }
            
        except Exception as e:
            logger.error(f"Error en service liquidación: {e}")
            raise

    def get_enlistment_manager_emt(
        self,
        date_from: date,
        date_to: date,
    ) -> Dict[str, Any]:
        """
        Obtiene reporte de historial de activacion gestor v1.
        
        Args:
            date_from: Fecha inicio
            date_to: Fecha fin

        Retorna: Diccionario con datos
        """
        try:
            
            rows_liquidation, _ = self.repository.get_liquidation_report(
                date_from=date_from,
                date_to=date_to,
                limit=None,
                offset=None
            )
                
            # Datos
            data_liq = []
            for row in rows_liquidation:
                data_liq.append({
                    'oferta': row.oferta,
                    'usuario_login': row.usuario_login,
                    'usuario_nombre': row.usuario_nombre,
                    'concepto': row.concepto,
                    'producto': row.producto,
                    'uen': row.uen,
                    'regional': row.regional,
                    'documento': row.documento,
                    'pedido_id': row.pedido_id,
                    'tecnologia': row.tecnologia,
                    'garantia': row.garantia,
                    'departamento': row.departamento,
                    'tipo_scoring': row.tipo_scoring,
                    'tipo_trabajo': row.tipo_trabajo,
                    'fecha_creado': row.fecha_creado,
                    'descripcion': row.descripcion,
                    'estado_direccion': row.estado_direccion,
                    'estado_oferta': row.estado_oferta,
                    'estado_pendiente': row.estado_pendiente,
                    'estado_scoring': row.estado_scoring,
                    'fecha_estado': row.fecha_estado,
                    'fecha_pendiente': row.fecha_pendiente,
                    'megagold': row.megagold,
                    'municipio': row.municipio,
                    'pedido_crm': row.pedido_crm,
                    'usuario_pendiente': row.usuario_pendiente,
                    'fecha_ingreso_gestor': row.fecha_ingreso_gestor,
                    'fecha_asignacion': row.fecha_asignacion,
                    'fecha_gestion': row.fecha_gestion,
                    'nombre_accion': row.nombre_accion,
                    'nombre_subaccion': row.nombre_subaccion,
                    'observacion': row.observacion,
                    'concepto_grupo': row.concepto_grupo,
                    'validacion_garantia': row.validacion_garantia
                })
            
            return {
                'type': 'success',
                'message': {
                    'enlistmentManager': data_liq,
                }
            }
            
        except Exception as e:
            logger.error(f"Error en service liquidación: {e}")
            raise
