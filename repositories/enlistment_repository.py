import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, date
from sqlalchemy.orm import Session
from sqlalchemy import text, desc, func, and_, or_
from sqlalchemy.dialects.postgresql import insert
from app.db.timezone_types import get_bogota_now
from app.models.enlistment_manager_model import (
    EnlistmentManager, 
    EnlistmentManagerHistory, 
    EnlistmentManagerControl,
    EstadoCarga,
    TipoOperacion
)
from app.db.postgres import SessionLocalPG
import uuid

logger = logging.getLogger("enlistment_repository")


class EnlistmentRepository:
    """Repository para operaciones de Enlistment Manager en PostgreSQL"""

    def __init__(self, db: Session):
        """Inicializa el repository con la sesión de base de datos.
        
        Args:
            db: Sesión de SQLAlchemy inyectada por dependency
        """
        self.db = db

    # ==========================================
    # OPERACIONES ENLISTMENT_MANAGER
    # ==========================================

    def get_by_oferta(self, oferta: str) -> Optional[EnlistmentManager]:
        """
        Obtiene un registro por número de oferta.
        
        Args:
            oferta: Número de oferta a buscar
            
        Returns:
            Registro encontrado o None
        """
        try:
            return self.db.query(EnlistmentManager).filter(
                EnlistmentManager.oferta == oferta
            ).first()
        except Exception as e:
            logger.error(f"Error al obtener oferta {oferta}: {e}")
            return None

    def get_by_ofertas_batch(self, ofertas: List[str]) -> List[EnlistmentManager]:
        """
        Obtiene múltiples registros por lista de ofertas (optimizado).
        
        Args:
            ofertas: Lista de números de oferta
            
        Returns:
            Lista de registros encontrados
        """
        try:
            return self.db.query(EnlistmentManager).filter(
                EnlistmentManager.oferta.in_(ofertas)
            ).all()
        except Exception as e:
            logger.error(f"Error al obtener ofertas en batch: {e}")
            return []

    def bulk_insert(self, registros: List[Dict[str, Any]]) -> int:
        """
        Inserta múltiples registros de forma masiva usando bulk insert.
        
        Args:
            registros: Lista de diccionarios con los datos a insertar
            
        Returns:
            Cantidad de registros insertados
        """
        try:
            if not registros:
                return 0
            
            # Preparar objetos para bulk insert
            objetos = []
            for reg in registros:
                objetos.append(EnlistmentManager(
                    id=reg.get('id', uuid.uuid4()),
                    ticket_carga=reg['ticket_carga'],
                    oferta=reg['oferta'],
                    hash_registro=reg['hash_registro'],
                    campos_dinamicos=reg['campos_dinamicos'],
                    estado_oferta=reg.get('estado_oferta', 'ABIERTO'),
                    contador_cargas_ausente=reg.get('contador_cargas_ausente', 0)
                ))
            
            self.db.bulk_save_objects(objetos)
            self.db.commit()
            
            logger.info(f"Bulk insert exitoso: {len(objetos)} registros")
            return len(objetos)
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error en bulk_insert: {e}")
            raise

    def bulk_update(self, updates: List[Dict[str, Any]]) -> int:
        """
        Actualiza múltiples registros de forma masiva.
        
        Args:
            updates: Lista de diccionarios con id y campos a actualizar
            
        Returns:
            Cantidad de registros actualizados
        """
        try:
            if not updates:
                return 0
            
            count = 0
            for update_data in updates:
                registro_id = update_data.pop('id')
                self.db.query(EnlistmentManager).filter(
                    EnlistmentManager.id == registro_id
                ).update(update_data, synchronize_session=False)
                count += 1
            
            self.db.commit()
            logger.info(f"Bulk update exitoso: {count} registros")
            return count
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error en bulk_update: {e}")
            raise

    def get_all_paginated(self, page: int = 1, limit: int = 100, 
                         filters: Optional[Dict[str, Any]] = None) -> Tuple[List[EnlistmentManager], int]:
        """
        Obtiene registros paginados con filtros opcionales.
        
        Args:
            page: Número de página (1-based)
            limit: Cantidad de registros por página
            filters: Filtros a aplicar (campos del JSONB)
            
        Returns:
            Tupla (lista de registros, total de registros)
        """
        try:
            query = self.db.query(EnlistmentManager)
            
            # Aplicar filtros JSONB si existen
            if filters:
                for key, value in filters.items():
                    if key == 'oferta':
                        query = query.filter(EnlistmentManager.oferta == value)
                    elif key == 'estado_oferta':
                        query = query.filter(EnlistmentManager.estado_oferta == value)
                    elif key == 'fecha_desde':
                        query = query.filter(EnlistmentManager.updated_at >= value)
                    elif key == 'fecha_hasta':
                        query = query.filter(EnlistmentManager.updated_at <= value)
                    else:
                        # Filtro en JSONB
                        query = query.filter(
                            EnlistmentManager.campos_dinamicos[key].astext == str(value)
                        )
            
            # Obtener total antes de paginar
            total = query.count()
            
            # Aplicar paginación
            offset = (page - 1) * limit
            registros = query.order_by(desc(EnlistmentManager.updated_at)).offset(offset).limit(limit).all()
            
            return registros, total
            
        except Exception as e:
            logger.error(f"Error en get_all_paginated: {e}")
            return [], 0

    # ==========================================
    # OPERACIONES ENLISTMENT_MANAGER_HISTORY
    # ==========================================

    def create_history_record(self, data: Dict[str, Any]) -> EnlistmentManagerHistory:
        """
        Crea un registro en el histórico.
        
        Args:
            data: Datos del registro histórico
            
        Returns:
            Registro creado
        """
        try:
            history = EnlistmentManagerHistory(**data)
            self.db.add(history)
            self.db.commit()
            self.db.refresh(history)
            return history
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error al crear registro histórico: {e}")
            raise

    def bulk_insert_history(self, registros: List[Dict[str, Any]]) -> int:
        """
        Inserta múltiples registros históricos de forma masiva.
        
        Args:
            registros: Lista de diccionarios con datos históricos
            
        Returns:
            Cantidad de registros insertados
        """
        try:
            if not registros:
                return 0
            
            objetos = []
            for reg in registros:
                objetos.append(EnlistmentManagerHistory(
                    id=uuid.uuid4(),
                    fk_enlistment_manager_id=reg.get('fk_enlistment_manager_id'),
                    ticket_carga=reg['ticket_carga'],
                    create_date_automation=reg['create_date_automation'],
                    oferta=reg['oferta'],
                    hash_registro=reg['hash_registro'],
                    tipo_operacion=reg['tipo_operacion'],
                    campos_dinamicos=reg['campos_dinamicos'],
                    campos_modificados=reg.get('campos_modificados'),
                    estado_oferta=reg.get('estado_oferta', 'ABIERTO')
                ))
            
            self.db.bulk_save_objects(objetos)
            self.db.commit()
            
            logger.info(f"Bulk insert history exitoso: {len(objetos)} registros")
            return len(objetos)
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error en bulk_insert_history: {e}")
            raise

    def create_manual_history_record(
        self, 
        oferta_obj: EnlistmentManager, 
        campos_modificados: Dict[str, Any], 
        ticket_carga: str = "GESTION_MANUAL"
    ) -> Optional[EnlistmentManagerHistory]:
        """
        Crea un registro de histórico para operaciones manuales de gestión.
        Se usa cuando el cambio es realizado por un usuario en lugar de la carga automática.
        
        Args:
            oferta_obj: Objeto EnlistmentManager con el estado actual
            campos_modificados: Dict con los campos que cambiaron {"campo": {"old": valor, "new": valor}}
            ticket_carga: Identificador del ticket (por defecto "GESTION_MANUAL")
            
        Returns:
            Registro histórico creado o None en caso de error
        """
        try:
            history = EnlistmentManagerHistory(
                id=uuid.uuid4(),
                fk_enlistment_manager_id=oferta_obj.id,
                ticket_carga=ticket_carga,
                create_date_automation= get_bogota_now(), # datetime.now().astimezone(),
                oferta=oferta_obj.oferta,
                hash_registro=oferta_obj.hash_registro,
                tipo_operacion=TipoOperacion.UPDATE,
                campos_dinamicos=oferta_obj.campos_dinamicos,
                campos_modificados=campos_modificados,
                estado_oferta=oferta_obj.estado_oferta
            )
            self.db.add(history)
            self.db.commit()
            self.db.refresh(history)
            logger.info(f"Registro histórico manual creado para oferta {oferta_obj.oferta}")
            return history
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error al crear registro histórico manual: {e}")
            return None

    def get_history_by_oferta(self, oferta: str, limit: int = 50) -> List[EnlistmentManagerHistory]:
        """
        Obtiene el histórico de cambios de una oferta.
        
        Args:
            oferta: Número de oferta
            limit: Límite de registros a retornar
            
        Returns:
            Lista de registros históricos ordenados por fecha desc
        """
        try:
            return self.db.query(EnlistmentManagerHistory).filter(
                EnlistmentManagerHistory.oferta == oferta
            ).order_by(desc(EnlistmentManagerHistory.create_date_automation)).limit(limit).all()
        except Exception as e:
            logger.error(f"Error al obtener histórico de oferta {oferta}: {e}")
            return []

    def get_history_by_ticket(self, ticket_carga: str) -> List[EnlistmentManagerHistory]:
        """
        Obtiene todos los cambios de un ticket específico.
        
        Args:
            ticket_carga: Ticket de carga
            
        Returns:
            Lista de registros históricos
        """
        try:
            return self.db.query(EnlistmentManagerHistory).filter(
                EnlistmentManagerHistory.ticket_carga == ticket_carga
            ).all()
        except Exception as e:
            logger.error(f"Error al obtener histórico de ticket {ticket_carga}: {e}")
            return []

    # ==========================================
    # OPERACIONES ENLISTMENT_MANAGER_CONTROL
    # ==========================================

    def create_control_record(self, data: Dict[str, Any]) -> EnlistmentManagerControl:
        """
        Crea un registro de control para una nueva carga.
        
        Args:
            data: Datos del control
            
        Returns:
            Registro de control creado
        """
        try:
            control = EnlistmentManagerControl(**data)
            self.db.add(control)
            self.db.commit()
            self.db.refresh(control)
            return control
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error al crear registro de control: {e}")
            raise

    def update_control_record(self, ticket_carga: str, data: Dict[str, Any]) -> EnlistmentManagerControl:
        """
        Actualiza un registro de control existente.
        
        Args:
            ticket_carga: Ticket de la carga
            data: Campos a actualizar
            
        Returns:
            Registro actualizado
        """
        try:
            control = self.db.query(EnlistmentManagerControl).filter(
                EnlistmentManagerControl.ticket_carga == ticket_carga
            ).first()
            
            if not control:
                raise ValueError(f"Control con ticket {ticket_carga} no encontrado")
            
            for key, value in data.items():
                setattr(control, key, value)
            
            self.db.commit()
            self.db.refresh(control)
            return control
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error al actualizar control {ticket_carga}: {e}")
            raise

    def get_control_by_ticket(self, ticket_carga: str) -> Optional[EnlistmentManagerControl]:
        """
        Obtiene un registro de control por ticket.
        
        Args:
            ticket_carga: Ticket de la carga
            
        Returns:
            Registro de control o None
        """
        try:
            return self.db.query(EnlistmentManagerControl).filter(
                EnlistmentManagerControl.ticket_carga == ticket_carga
            ).first()
        except Exception as e:
            logger.error(f"Error al obtener control {ticket_carga}: {e}")
            return None

    def get_last_control(self) -> Optional[EnlistmentManagerControl]:
        """
        Obtiene el último registro de control.
        
        Returns:
            Último registro de control o None
        """
        try:
            return self.db.query(EnlistmentManagerControl).order_by(
                desc(EnlistmentManagerControl.create_date_automation)
            ).first()
        except Exception as e:
            logger.error(f"Error al obtener último control: {e}")
            return None

    def get_controls_by_date_range(self, fecha_desde: date, fecha_hasta: date) -> List[EnlistmentManagerControl]:
        """
        Obtiene registros de control en un rango de fechas.
        
        Args:
            fecha_desde: Fecha inicial
            fecha_hasta: Fecha final
            
        Returns:
            Lista de registros de control
        """
        try:
            return self.db.query(EnlistmentManagerControl).filter(
                and_(
                    func.date(EnlistmentManagerControl.create_date_automation) >= fecha_desde,
                    func.date(EnlistmentManagerControl.create_date_automation) <= fecha_hasta
                )
            ).order_by(desc(EnlistmentManagerControl.create_date_automation)).all()
        except Exception as e:
            logger.error(f"Error al obtener controles por rango de fechas: {e}")
            return []

    # ==========================================
    # CONSULTAS ESTADÍSTICAS
    # ==========================================

    def get_stats_by_field(self, field_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Obtiene estadísticas agrupadas por un campo del JSONB.
        
        Args:
            field_name: Nombre del campo en campos_dinamicos
            limit: Límite de resultados
            
        Returns:
            Lista de dict con campo y conteo
        """
        try:
            query = text(f"""
                SELECT 
                    campos_dinamicos->>:field_name as valor,
                    COUNT(*) as total
                FROM enlistment_manager
                WHERE campos_dinamicos->>:field_name IS NOT NULL
                GROUP BY valor
                ORDER BY total DESC
                LIMIT :limit
            """)
            
            result = self.db.execute(query, {"field_name": field_name, "limit": limit})
            return [{"valor": row[0], "total": row[1]} for row in result]
            
        except Exception as e:
            logger.error(f"Error al obtener stats del campo {field_name}: {e}")
            return []

    def get_daily_stats(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        Obtiene estadísticas diarias de los últimos N días.
        
        Args:
            days: Número de días hacia atrás
            
        Returns:
            Lista de estadísticas por día
        """
        try:
            query = text("""
                SELECT 
                    DATE(create_date_automation) as fecha,
                    COUNT(*) as total_cargas,
                    AVG(tiempo_ejecucion_segundos) as tiempo_promedio,
                    SUM(total_registros_procesados) as total_registros,
                    SUM(total_registros_nuevos) as total_nuevos,
                    SUM(total_registros_actualizados) as total_actualizados
                FROM enlistment_manager_control
                WHERE create_date_automation >= NOW() - INTERVAL ':days days'
                AND estado = 'COMPLETADO'
                GROUP BY DATE(create_date_automation)
                ORDER BY fecha DESC
            """)
            
            result = self.db.execute(query, {"days": days})
            return [dict(row._mapping) for row in result]
            
        except Exception as e:
            logger.error(f"Error al obtener estadísticas diarias: {e}")
            return []

    # ==========================================
    # OPERACIONES DE CONTROL DE ESTADO DE OFERTAS
    # ==========================================

    def get_all_ofertas_abiertas(self) -> List[str]:
        """
        Obtiene lista de todas las ofertas en estado ABIERTO.
        Excluye ofertas con concepto MALO o RFS (protegidas de modificaciones automáticas).
        
        Returns:
            Lista de números de oferta
        """
        try:
            registros = self.db.query(EnlistmentManager).filter(
                EnlistmentManager.estado_oferta == 'ABIERTO'
            ).all()
            
            # Filtrar ofertas con concepto protegido (MALO o RFS)
            return [
                r.oferta for r in registros 
                if r.campos_dinamicos.get('concepto', '') not in ['MALO', 'RFS']
            ]
        except Exception as e:
            logger.error(f"Error al obtener ofertas abiertas: {e}")
            return []

    def increment_contador_ausencias(
        self, 
        ofertas: List[str], 
        umbral: int
    ) -> Dict[str, Any]:
        """
        Incrementa el contador de ausencias de ofertas y cierra las que alcancen el umbral.
        
        Args:
            ofertas: Lista de ofertas ausentes
            umbral: Umbral de cargas para cerrar automáticamente
            
        Returns:
            Dict con ofertas cerradas, incrementadas y sus datos
        """
        try:
            if not ofertas:
                return {"cerradas": 0, "incrementadas": 0, "ofertas_cerradas": []}
            
            # Obtener registros actuales
            registros = self.db.query(EnlistmentManager).filter(
                EnlistmentManager.oferta.in_(ofertas)
            ).all()
            
            ofertas_para_cerrar = []
            ofertas_para_incrementar = []
            datos_cerradas = []
            
            for reg in registros:
                # PROTECCIÓN: No modificar ofertas con concepto MALO o RFS
                # Estas ofertas solo pueden ser modificadas manualmente por supervisores
                concepto_actual = reg.campos_dinamicos.get('concepto', '')
                if concepto_actual in ['MALO', 'RFS']:
                    logger.debug(f"Oferta {reg.oferta} tiene concepto protegido '{concepto_actual}', omitiendo procesamiento de ausencias")
                    continue
                
                nuevo_contador = reg.contador_cargas_ausente + 1
                
                if nuevo_contador >= umbral:
                    # Cerrar automáticamente
                    ofertas_para_cerrar.append(reg.oferta)
                    datos_cerradas.append({
                        'id': reg.id,
                        'oferta': reg.oferta,
                        'hash_registro': reg.hash_registro,
                        'campos_dinamicos': reg.campos_dinamicos
                    })
                else:
                    # Solo incrementar contador
                    ofertas_para_incrementar.append(reg.oferta)
            
            # Actualizar estados y contadores
            if ofertas_para_cerrar:
                self.db.query(EnlistmentManager).filter(
                    EnlistmentManager.oferta.in_(ofertas_para_cerrar)
                ).update({
                    "estado_oferta": "CERRADO_AUTOMATICO",
                    "contador_cargas_ausente": umbral,
                    "contador_cargas_reapertura": 0,  # Resetear contador de reapertura al cerrar
                    "usuario_asignado_login": None,
                    "usuario_asignado_nombre": None,
                    "usuario_asignado_profile_id": None,
                    "fecha_asignacion": None,
                    "fecha_gestion": None
                }, synchronize_session=False)
            
            if ofertas_para_incrementar:
                # Incrementar contador sin cambiar estado
                for oferta in ofertas_para_incrementar:
                    self.db.query(EnlistmentManager).filter(
                        EnlistmentManager.oferta == oferta
                    ).update({
                        "contador_cargas_ausente": EnlistmentManager.contador_cargas_ausente + 1,
                        "contador_cargas_reapertura": 0  # Resetear contador de reapertura mientras está ausente
                    }, synchronize_session=False)
            
            self.db.commit()
            
            logger.info(f"Cerradas: {len(ofertas_para_cerrar)}, Incrementadas: {len(ofertas_para_incrementar)}")
            
            return {
                "cerradas": len(ofertas_para_cerrar),
                "incrementadas": len(ofertas_para_incrementar),
                "ofertas_cerradas": datos_cerradas
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error en increment_contador_ausencias: {e}")
            raise

    def reset_contador_ausencia(self, registro_id: uuid.UUID) -> None:
        """
        Resetea el contador de ausencias cuando una oferta vuelve a aparecer.
        
        Args:
            registro_id: ID del registro
        """
        try:
            self.db.query(EnlistmentManager).filter(
                EnlistmentManager.id == registro_id
            ).update(
                {"contador_cargas_ausente": 0},
                synchronize_session=False
            )
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error en reset_contador_ausencia: {e}")

    # ==========================================
    # TRANSACCIONES MANUALES
    # ==========================================

    def commit(self):
        """Commit manual de la transacción"""
        try:
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error en commit: {e}")
            raise

    def rollback(self):
        """Rollback manual de la transacción"""
        self.db.rollback()

