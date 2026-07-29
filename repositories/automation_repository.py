import logging
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import bindparam, text
from app.models.gestor_operacion_model import GestorOperacion
from app.models.automation_config_model import (
    Actividad, Aprovisionador, Barrio, ConceptoAnterior, ConceptoId,
    ConceptoIdAnteriorNov, Departamento, DescTipoTrabajo, Fuente, Grupo,
    Microzona, MunicipioId, Producto, ProductoId, StatusPedido,
    TecnologiaId, TipoElemento, TipoTrabajo, UenCalculada, Zona
)
from app.db.oracle_fenix_session import SessionLocalFenix
from app.db.oracle_siebel_session import SessionLocalSiebel
from app.db.postgres import SessionLocalPG
from app.db.sqlserver_gestion_operativa_session import SessionLocalSQLServerGestion
from app.schemas.siebel_schema import SiebelBase

logger = logging.getLogger("automation_repository")


class AutomationRepository:
    """
    Repository para operaciones de automation.
    Maneja consultas a Oracle (Fenix y Siebel) y PostgreSQL.
    """

    def __init__(self, db_pg: Session):
        """Inicializa el repository con la sesión de PostgreSQL.
        
        Args:
            db_pg: Sesión de PostgreSQL inyectada por dependency
        
        Note:
            Las sesiones de Oracle y SQL Server se crean localmente en métodos específicos
        """
        self.db_pg = db_pg

    # ==========================================
    # CONSULTAS A ORACLE FENIX
    # ==========================================

    def get_query_fenix(self) -> str:
        """
        Retorna la query para obtener datos de Fenix.
        Base de datos FENIX Stanby - SessionLocalFenix
        """
        return """
        SELECT A.PEDIDO_ID,A.PEDIDO_CRM,A.CONCEPTO_INTERNET,A.CONCEPTO_TELEVISION,A.CONCEPTO_TELEFONIA,A.CONCEPTO_ID
        FROM(
        SELECT P.PEDIDO_ID,P.PEDIDO_CRM,
        (
            SELECT T.CONCEPTO FROM (
                SELECT C.DESCRIPCION || '(' || C.CONCEPTO_ID || ')' CONCEPTO,S.PEDIDO_ID
                FROM FNX_SOLICITUDES S
                INNER JOIN FNX_PEDIDOS PED ON PED.PEDIDO_ID = S.PEDIDO_ID
                INNER JOIN FNX_CONCEPTOS C ON S.CONCEPTO_ID = C.CONCEPTO_ID
                WHERE PED.PEDIDO_CRM IN :bind_pedidos AND S.PRODUCTO_ID = 'INTER'
                ORDER BY DECODE(S.TIPO_ELEMENTO_ID,'ACCESP',1,'INTCON',2,'EQACCP',3,'EQURED',4,'CUENTA',5,'ADMSER',6,'TDOMIN',7,'USER',8,'CPE',9,'ADMSEG',10,'EQACCS',11,'SERV',12,'PHLIN2',13,'CABLEM',14)
            ) T
            WHERE T.PEDIDO_ID = P.PEDIDO_ID AND ROWNUM = 1
        ) CONCEPTO_INTERNET,
        (
            SELECT T.CONCEPTO FROM (
                SELECT C.DESCRIPCION || '(' || C.CONCEPTO_ID || ')' CONCEPTO,S.PEDIDO_ID
                FROM FNX_SOLICITUDES S
                INNER JOIN FNX_PEDIDOS PED ON PED.PEDIDO_ID = S.PEDIDO_ID
                INNER JOIN FNX_CONCEPTOS C ON S.CONCEPTO_ID = C.CONCEPTO_ID
                WHERE PED.PEDIDO_CRM IN :bind_pedidos AND S.PRODUCTO_ID = 'TELEV'
                ORDER BY DECODE(S.TIPO_ELEMENTO_ID,'INSIP',1,'INSHFC',2,'STBOX',3,'SERVIP',4,'SERHFC',5,'EQURED',6,'TELEV',7,'EQACCP',8)
            ) T
            WHERE T.PEDIDO_ID = P.PEDIDO_ID AND ROWNUM = 1
        ) CONCEPTO_TELEVISION,
        (
            SELECT T.CONCEPTO FROM (
                SELECT C.DESCRIPCION || '(' || C.CONCEPTO_ID || ')' CONCEPTO,S.PEDIDO_ID
                FROM FNX_SOLICITUDES S
                INNER JOIN FNX_PEDIDOS PED ON PED.PEDIDO_ID = S.PEDIDO_ID
                INNER JOIN FNX_CONCEPTOS C ON S.CONCEPTO_ID = C.CONCEPTO_ID
                WHERE PED.PEDIDO_CRM IN :bind_pedidos AND S.PRODUCTO_ID = 'TO'
                ORDER BY DECODE(S.TIPO_ELEMENTO_ID,'TOIP',1,'TO',2,'EQURED',3,'EQACCP',4,'LICIVI',5,'CDMA',6)
            ) T
            WHERE T.PEDIDO_ID = P.PEDIDO_ID AND ROWNUM = 1
        ) CONCEPTO_TELEFONIA,
        SOL.CONCEPTO_ID,
        ROW_NUMBER() OVER (
            PARTITION BY P.PEDIDO_CRM
            ORDER BY
                CASE SOL.PRODUCTO_ID
                    WHEN 'INTER' THEN 1
                    WHEN 'TELEV' THEN 2
                    WHEN 'TO' THEN 3
                    ELSE 99
                END
        ) AS RN
        FROM FNX_PEDIDOS P
        INNER JOIN FNX_SOLICITUDES SOL ON P.PEDIDO_ID = SOL.PEDIDO_ID
        WHERE P.PEDIDO_CRM IN :bind_pedidos
        AND SOL.TIPO_ELEMENTO_ID IN ('INSHFC','ACCESP','TOIP','INSIP','TO','INSTA','TRKSIP','SEDEIP')
        AND SOL.ESTADO_BLOQUEO = 'N'
        ) A
        WHERE A.RN = 1
        """

    def get_data_fenix(self, bind_filter: List) -> List[Dict[str, Any]]:
        """
        Ejecuta la consulta en la base de datos Fenix Standby.
        Retorna una lista de diccionarios con los resultados.
        """
        db_fenix = SessionLocalFenix()
        try:
            query = self.get_query_fenix()
            result = db_fenix.execute(text(query).bindparams(bindparam(key="bind_pedidos", value=bind_filter, expanding=True)))

            # Convertir los resultados a lista de diccionarios
            columns = result.keys()
            data = [dict(zip(columns, row)) for row in result.fetchall()]

            logger.info(f"Registros obtenidos de Fenix: {len(data)}")
            return data
        except Exception as e:
            logger.error(f"Error al obtener datos de Fenix: {e}")
            raise
        finally:
            db_fenix.close()

    # ==========================================
    # CONSULTAS A ORACLE SIEBEL
    # ==========================================

    def get_query_siebel(self) -> str:
        """
        Retorna la query para obtener datos de Siebel.
        Base de datos SIEBEL Stanby - SessionLocalSiebel
        """
        # Aquí deberías agregar la query completa de Siebel
        # Por ahora retorno un placeholder
        return """
        SELECT
        OE.QUOTE_NUM OFERTA,
        OE.STAT_CD ESTADO_OFERTA,
        TO_CHAR (OE.CREATED, 'YYYY-MM-DD HH24:MI:SS') FECHA_CREADO,
        OE.ROW_ID,
        OE.REV_NUM,
        TO_CHAR (OE.LAST_UPD, 'YYYY-MM-DD HH24:MI:SS') FECHA_ESTADO,
        OE.CG_DLVRSPRD_TYP_CD ESTADO_ESTUDIO_LEGAL,
        OE.DESC_TEXT DESCRIPCION,
        CASE
            WHEN E.E_TODO_CD IS NULL THEN 'Sin_Pendiente'
            WHEN E.E_EVT_STAT_CD IN ('Rechazado', 'Cerrado', 'Cancelado') THEN 'Sin_Pendiente_Abierto'
            ELSE E.E_TODO_CD
        END CONCEPTO,
        CASE
            WHEN E.E_TODO_CD IS NULL AND OEX.OEX_ATTRIB_35 = 'Terminado Estudio de Riesgos' AND F.F_STATUS_CD = 'Aprobado' AND F.F_CREDIT_SCORE > 0 AND F.F_CRCHK_PSTPAID_SVC <= 0 THEN 'Sin_CupoD' -- New Line
            ELSE E.E_EVT_STAT_CD
        END ESTADO_PENDIENTE,
        TO_CHAR (E.E_CREATED, 'YYYY-MM-DD HH24:MI:SS') FECHA_PENDIENTE,
        E.E_COMMENTS_LONG COMENTARIO,
        OEX.OEX_X_UNE_RESULTADO_GLOBAL DISPONIBILIDAD,
        OEX.OEX_ATTRIB_37 TIPO_SCORING,
        OEX.OEX_ATTRIB_35 ESTADO_SCORING,
        U3.U3_LOGIN USUARIO_PENDIENTE,
        U2.U2_LOGIN USUARIO,
        CHL.CHL_NAME CANAL,
        CL.CL_DUNS_NUM DOCUMENTO,
        CASE
            WHEN DIR.DIR_PROVINCE IN ('Amazonas','Arauca','Bogotá D.C.','Caquetá','Cundinamarca','Guainía','Guaviare','Huila','La Guajira','Meta','Nariño','Putumayo','Tolima','Vaupés','Vichada') THEN 'Centro'
            WHEN DIR.DIR_PROVINCE IN ('Antioquia','San Andrés y Providencia','Caldas','Chocó','Quindío','Risaralda') THEN 'Noroccidente'
            WHEN DIR.DIR_PROVINCE IN ('Atlántico','Bolívar','Cesar','Córdoba','Magdalena','Sucre') THEN 'Norte'
            WHEN DIR.DIR_PROVINCE IN ('Boyacá','Casanare','Norte de Santander','Santander') THEN 'Oriente'
            WHEN DIR.DIR_PROVINCE IN ('Cauca', 'Valle del Cauca') THEN 'Sur'
            ELSE 'SIN_REGIONAL'
        END REGIONAL,
        DIR.DIR_PROVINCE DEPARTAMENTO,
        DIR.DIR_CITY MUNICIPIO,
        DIR.DIR_ADDR DIRECCION,
        DIR.DIR_LATITUDE LATITUDE,
        DIR.DIR_LONGITUDE LONGITUDE,
        DIRX.DIRX_ATTRIB_42 ESTADO_DIRECCION,
        (
            SELECT PROD21.ATTRIB_06 TIPO_TRANSACCION
            FROM SIEBEL.S_DOC_QUOTE OE1
            INNER JOIN SIEBEL.S_QUOTE_ITEM PROD1 ON PROD1.SD_ID = OE1.ROW_ID
            INNER JOIN SIEBEL.S_QUOTE_ITEM_X PROD21 ON PROD1.ROW_ID = PROD21.ROW_ID
            INNER JOIN SIEBEL.S_PROD_INT NOM1 ON NOM1.ROW_ID = PROD1.PROD_ID
            WHERE NOM1.NAME = 'Internet' AND OE.ROW_ID = OE1.ROW_ID AND ROWNUM = 1
        ) TIPO_TRANSACCION_INTERNET,
        (
            SELECT PROD21.ATTRIB_06 TIPO_TRANSACCION
            FROM SIEBEL.S_DOC_QUOTE OE1
            INNER JOIN SIEBEL.S_QUOTE_ITEM PROD1 ON PROD1.SD_ID = OE1.ROW_ID
            INNER JOIN SIEBEL.S_QUOTE_ITEM_X PROD21 ON PROD1.ROW_ID = PROD21.ROW_ID
            INNER JOIN SIEBEL.S_PROD_INT NOM1 ON NOM1.ROW_ID = PROD1.PROD_ID
            WHERE NOM1.NAME IN ('Televisión Satelital', 'Televisión Hogares') AND OE.ROW_ID = OE1.ROW_ID AND ROWNUM = 1
        ) TIPO_TRANSACCION_TELEVISION,
        (
            SELECT PROD21.ATTRIB_06 TIPO_TRANSACCION
            FROM SIEBEL.S_DOC_QUOTE OE1
            INNER JOIN SIEBEL.S_QUOTE_ITEM PROD1 ON PROD1.SD_ID = OE1.ROW_ID
            INNER JOIN SIEBEL.S_QUOTE_ITEM_X PROD21 ON PROD1.ROW_ID = PROD21.ROW_ID
            INNER JOIN SIEBEL.S_PROD_INT NOM1 ON NOM1.ROW_ID = PROD1.PROD_ID
            WHERE NOM1.NAME = 'Telefonía' AND OE.ROW_ID = OE1.ROW_ID AND ROWNUM = 1
        ) TIPO_TRANSACCION_TELEFONIA,
        DIRX.DIRX_ATTRIB_46 ID_GIS,
        DIRX.DIRX_ATTRIB_40 PAGINACION,
        OE.X_UNE_MARCA_MEGA MEGAGOLD,
        PROD2_ATTRIB_06 TIPO_TRABAJO
        FROM SIEBEL.S_DOC_QUOTE OE
        INNER JOIN (SELECT DISTINCT PROD.SD_ID, PROD2.ATTRIB_06 PROD2_ATTRIB_06 FROM SIEBEL.S_QUOTE_ITEM PROD INNER JOIN SIEBEL.S_QUOTE_ITEM_X PROD2 ON PROD2.ROW_ID = PROD.ROW_ID AND PROD2.X_EVE_USE IN('Residencial','Empresarial') AND PROD2.CREATED >= SYSDATE - 30 WHERE PROD.CREATED >= SYSDATE - 30) PROD ON PROD.SD_ID = OE.ROW_ID
        LEFT JOIN (SELECT F.ACCNT_ID, F.STATUS_CD F_STATUS_CD, F.CREDIT_SCORE F_CREDIT_SCORE, F.CRCHK_PSTPAID_SVC F_CRCHK_PSTPAID_SVC FROM SIEBEL.S_FINAN_PROF F WHERE F.CREATED >= SYSDATE - 30) F ON F.ACCNT_ID = OE.CUST_ACCNT_ID
        LEFT JOIN (SELECT E.ORDER_ID, E.TODO_CD E_TODO_CD, E.EVT_STAT_CD E_EVT_STAT_CD, E.CREATED E_CREATED, E.COMMENTS_LONG E_COMMENTS_LONG, E.LAST_UPD_BY E_LAST_UPD_BY FROM SIEBEL.S_EVT_ACT E WHERE E.CREATED >= SYSDATE - 30) E ON E.ORDER_ID = OE.ROW_ID
        LEFT JOIN (SELECT U3.ROW_ID U3_ROW_ID, U3.LOGIN U3_LOGIN FROM SIEBEL.S_USER U3) U3 ON U3.U3_ROW_ID = E.E_LAST_UPD_BY
        INNER JOIN (SELECT OEX.PAR_ROW_ID OEX_PAR_ROW_ID, OEX.ATTRIB_35 OEX_ATTRIB_35, OEX.X_UNE_RESULTADO_GLOBAL OEX_X_UNE_RESULTADO_GLOBAL, OEX.ATTRIB_37 OEX_ATTRIB_37, OEX.X_EVE_SALES_ADVISOR OEX_X_EVE_SALES_ADVISOR, OEX.ATTRIB_07 OEX_ATTRIB_07 FROM SIEBEL.S_DOC_QUOTE_X OEX) OEX ON OEX.OEX_PAR_ROW_ID = OE.ROW_ID
        LEFT JOIN (SELECT U2.ROW_ID U2_ROW_ID, U2.LOGIN U2_LOGIN FROM SIEBEL.S_USER U2) U2 ON U2.U2_ROW_ID = OEX.OEX_X_EVE_SALES_ADVISOR
        LEFT JOIN (SELECT CHL.ROW_ID CHL_ROW_ID, CHL.NAME CHL_NAME FROM SIEBEL.S_PARTY CHL) CHL ON CHL.CHL_ROW_ID = OEX.OEX_ATTRIB_07
        LEFT JOIN (SELECT CL.ROW_ID CL_ROW_ID, CL.DUNS_NUM CL_DUNS_NUM, CL.PR_ADDR_ID CL_PR_ADDR_ID FROM SIEBEL.S_ORG_EXT CL) CL ON CL.CL_ROW_ID = OE.SERV_ACCNT_ID
        LEFT JOIN (SELECT DIR.ROW_ID DIR_ROW_ID, DIR.PROVINCE DIR_PROVINCE, DIR.CITY DIR_CITY, DIR.ADDR DIR_ADDR, DIR.LATITUDE DIR_LATITUDE, DIR.LONGITUDE DIR_LONGITUDE FROM SIEBEL.S_ADDR_PER DIR) DIR ON DIR.DIR_ROW_ID = CL.CL_PR_ADDR_ID
        LEFT JOIN (SELECT DIRX.ROW_ID DIRX_ROW_ID, DIRX.ATTRIB_42 DIRX_ATTRIB_42, DIRX.ATTRIB_46 DIRX_ATTRIB_46, DIRX.ATTRIB_40 DIRX_ATTRIB_40 FROM SIEBEL.S_ADDR_PER_X DIRX) DIRX ON DIRX.DIRX_ROW_ID = DIR.DIR_ROW_ID
        LEFT JOIN (SELECT R.QUOTE_NUM R_QUOTE_NUM, R.STAT_CD R_STAT_CD FROM SIEBEL.S_DOC_QUOTE R WHERE R.STAT_CD = 'Cancelado') R ON R.R_QUOTE_NUM = OE.QUOTE_NUM
        WHERE OE.STAT_CD NOT IN ('Pedido Generado', 'Cancelado', 'Prospecto')
        AND OE.CREATED >= TRUNC(SYSDATE) - 30
        AND R.R_QUOTE_NUM IS NULL
        ORDER BY 
        OE.QUOTE_NUM, 
        CASE WHEN E.E_TODO_CD IS NULL AND OEX.OEX_ATTRIB_35 = 'Terminado Estudio de Riesgos' AND F.F_STATUS_CD = 'Aprobado' AND F.F_CREDIT_SCORE > 0 AND F.F_CRCHK_PSTPAID_SVC <= 0 THEN 'Sin_CupoD' ELSE E.E_EVT_STAT_CD END,
        TO_CHAR(E.E_CREATED, 'YYYY-MM-DD HH24:MI:SS') DESC
        """

    def get_data_siebel(self) -> List[SiebelBase]:
        """
        Ejecuta la consulta en la base de datos Siebel Standby.
        Retorna una lista de diccionarios con los resultados.
        """
        db_siebel = SessionLocalSiebel()
        try:
            query = self.get_query_siebel()
            result = db_siebel.execute(text(query))

            # Convertir los resultados a lista de diccionarios
            columns = result.keys()
            data = [dict(zip(columns, row)) for row in result.fetchall()]

            logger.info(f"Registros obtenidos de Siebel: {len(data)}")
            return data
        except Exception as e:
            logger.error(f"Error al obtener datos de Siebel: {e}")
            raise
        finally:
            db_siebel.close()
            
    def get_query_siebel_items(self) -> str:
        """
        Retorna la query para obtener datos de Siebel de items de ofertas (TECNOLOGIA, PRODUCTO UEN).
        Base de datos SIEBEL Stanby - SessionLocalSiebel
        """
        
        return """
        SELECT ITEM.OFERTA, ITEM.TECNOLOGIA, ITEM.PRODUCTO, ITEM.UEN
        FROM (
            SELECT OE.QUOTE_NUM AS OFERTA, SQIX.ATTRIB_36 AS TECNOLOGIA, PI.NAME AS PRODUCTO, SQIX.X_EVE_USE AS UEN, SQI.PROD_ID,
                ROW_NUMBER() OVER (
                    PARTITION BY OE.QUOTE_NUM
                    ORDER BY
                        CASE SQI.PROD_ID
                            WHEN '1-KJS9' THEN 1
                            WHEN '1-6CCV' THEN 2
                            WHEN '1-1IAQT' THEN 3
                        END
                ) AS RN
            FROM SIEBEL.S_DOC_QUOTE OE
            INNER JOIN SIEBEL.S_QUOTE_ITEM SQI ON SQI.SD_ID = OE.QUOTE_NUM
            INNER JOIN SIEBEL.S_QUOTE_ITEM_X SQIX ON SQIX.ROW_ID = SQI.ROW_ID
            INNER JOIN SIEBEL.S_PROD_INT PI ON PI.ROW_ID = SQI.PROD_ID
            WHERE OE.QUOTE_NUM IN :bind_ofertas
        ) ITEM
        WHERE ITEM.RN = 1"""
    
    def get_data_siebel_items(self, bind_filter: List) -> List[Dict[str, Any]]:
        """
        Ejecuta la consulta en la base de datos Siebel Standby.
        Retorna una lista de diccionarios con los resultados.
        """
        db_siebel = SessionLocalSiebel()
        try:
            query = self.get_query_siebel_items()
            result = db_siebel.execute(text(query).bindparams(bindparam(key="bind_ofertas", value=bind_filter, expanding=True)))

            # Convertir los resultados a lista de diccionarios
            columns = result.keys()
            data = [dict(zip(columns, row)) for row in result.fetchall()]

            logger.info(f"Registros obtenidos de Siebel: {len(data)}")
            return data
        except Exception as e:
            logger.error(f"Error al obtener datos de Siebel: {e}")
            raise
        finally:
            db_siebel.close()
    
    def get_query_siebel_flag(self) -> str:
        """
        Retorna la query para obtener datos de Siebel de flags de ofertas (HFC, GPON, TERCERO).
        Base de datos SIEBEL Stanby - SessionLocalSiebel
        """
        
        return """SELECT DISTINCT x.row_id OFERTA,
        CASE
            WHEN DX.X_UNE_COBERTURA_HFC = '0' THEN 'NO'
            ELSE 'SI'
        END AS FLAG_HFC,
        CASE
            WHEN DX.X_UNE_COBERTURA_GPON = '0' THEN 'NO'
            ELSE 'SI'
        END AS FLAG_GPON,
        CASE
            WHEN DX.X_UNE_COBERTURA_TERCERO = 'Y' THEN 'SI'
            ELSE 'NO'
        END AS FLAG_TERCERO
        FROM
        siebel.s_doc_quote q,
        siebel.s_doc_quote_x x,
        siebel.s_org_ext o,
        siebel.s_addr_per d,
        siebel.s_addr_per_x dx
        WHERE q.row_id = x.par_row_id(+)
        AND q.serv_accnt_id = o.row_id
        AND o.pr_addr_id = d.row_id
        AND d.row_id = dx.row_id
        AND DX.X_UNE_COBERTURA_HFC = '0'
        AND DX.X_UNE_COBERTURA_GPON = '0'
        AND x.row_id IN :bind_ofertas"""
              
    def get_data_siebel_flag(self, bind_filter: List) -> List[Dict[str, Any]]:
        """
        Ejecuta la consulta en la base de datos Siebel Standby.
        Retorna una lista de diccionarios con los resultados.
        """
        db_siebel = SessionLocalSiebel()
        try:
            query = self.get_query_siebel_flag()
            result = db_siebel.execute(text(query).bindparams(bindparam(key="bind_ofertas", value=bind_filter, expanding=True)))

            # Convertir los resultados a lista de diccionarios
            columns = result.keys()
            data = [dict(zip(columns, row)) for row in result.fetchall()]

            logger.info(f"Registros obtenidos de Siebel: {len(data)}")
            return data
        except Exception as e:
            logger.error(f"Error al obtener datos de Siebel: {e}")
            raise
        finally:
            db_siebel.close()
    
    # ==========================================
    # OPERACIONES EN POSTGRESQL
    # ==========================================

    # Diccionario que mapea nombres de tabla a modelos
    CATALOG_MODELS = {
        "actividad": (Actividad, "actividad"),
        "aprovisionador": (Aprovisionador, "aprovisionador"),
        "barrio": (Barrio, "barrio"),
        "concepto_anterior": (ConceptoAnterior, "concepto_anterior"),
        "concepto_id": (ConceptoId, "concepto_id"),
        "concepto_id_anterior_nov": (ConceptoIdAnteriorNov, "concepto_id_anterior_nov"),
        "departamento": (Departamento, "departamento"),
        "desc_tipo_trabajo": (DescTipoTrabajo, "desc_tipo_trabajo"),
        "fuente": (Fuente, "fuente"),
        "grupo": (Grupo, "grupo"),
        "microzona": (Microzona, "microzona"),
        "municipio_id": (MunicipioId, "municipio_id"),
        "producto": (Producto, "producto"),
        "producto_id": (ProductoId, "producto_id"),
        "status_pedido": (StatusPedido, "status_pedido"),
        "tecnologia_id": (TecnologiaId, "tecnologia_id"),
        "tipo_elemento": (TipoElemento, "tipo_elemento"),
        "tipo_trabajo": (TipoTrabajo, "tipo_trabajo"),
        "uen_calculada": (UenCalculada, "uen_calculada"),
        "zona": (Zona, "zona"),
    }

    def get_catalog_id(self, table_name: str, field_name: str, value: str) -> Optional[str]:
        """
        Obtiene o crea un registro en una tabla de catálogo y retorna su ID.
        Reemplaza la funcionalidad de get_config_foreing y set_config_foreing.

        Args:
            table_name: Nombre de la tabla de catálogo
            field_name: Nombre del campo (debe coincidir con table_name)
            value: Valor a buscar/insertar

        Returns:
            UUID del registro como string, o None si hay error
        """
        try:
            if table_name not in self.CATALOG_MODELS:
                logger.error(f"Tabla de catálogo no encontrada: {table_name}")
                return None

            model_class, field_attr = self.CATALOG_MODELS[table_name]

            # Buscar registro existente
            field_column = getattr(model_class, field_attr)
            record = self.db_pg.query(model_class).filter(
                field_column == value).first()

            if record:
                return str(record.id)

            # Si no existe, crear nuevo registro
            new_record = model_class(**{field_attr: value, "is_state": True})
            self.db_pg.add(new_record)
            self.db_pg.commit()
            self.db_pg.refresh(new_record)

            logger.info(f"Registro creado en {table_name}: {value}")
            return str(new_record.id)

        except Exception as e:
            self.db_pg.rollback()
            logger.error(f"Error al obtener/crear catálogo {table_name}: {e}")
            return None

    def get_zona_by_municipio(self, municipio_id_value: str) -> Optional[str]:
        """
        Obtiene el ID de zona basado en el municipio_id.
        En el esquema actual, zona es una tabla de catálogo simple.
        Esta función está aquí para compatibilidad con el código PHP original.

        Args:
            municipio_id_value: Valor del municipio_id

        Returns:
            UUID de zona como string, o None si no se encuentra
        """
        try:
            print("municipio_id_value", municipio_id_value)

            # Primero obtener el ID del municipio
            municipio_uuid = self.get_catalog_id(
                "municipio_id", "municipio_id", municipio_id_value)

            if not municipio_uuid:
                return None

            # En el esquema SQL no hay una tabla de relación municipio-zona
            # Por lo tanto, necesitarías definir esa lógica o tener una tabla adicional
            # Por ahora retorno None indicando que se necesita implementación adicional
            logger.warning(
                f"Relación municipio-zona no implementada para: {municipio_id_value}")
            return None

        except Exception as e:
            logger.error(f"Error al obtener zona por municipio: {e}")
            return None

    def get_gestor_operacion_by_pedido(self, pedido: str) -> Optional[GestorOperacion]:
        """
        Busca un registro de gestor_operacion por número de pedido.
        """
        try:
            return self.db_pg.query(GestorOperacion).filter(GestorOperacion.pedido == pedido).first()
        except Exception as e:
            logger.error(f"Error al buscar gestor_operacion: {e}")
            raise

    def create_gestor_operacion(self, data: Dict[str, Any]) -> GestorOperacion:
        """
        Crea un nuevo registro en gestor_operacion.
        """
        try:
            nuevo_registro = GestorOperacion(**data)
            self.db_pg.add(nuevo_registro)
            self.db_pg.commit()
            self.db_pg.refresh(nuevo_registro)
            logger.info(f"Gestor_operacion creado: {nuevo_registro.pedido}")
            return nuevo_registro
        except Exception as e:
            self.db_pg.rollback()
            logger.error(f"Error al crear gestor_operacion: {e}")
            raise

    def update_gestor_operacion(self, gestor_id: int, data: Dict[str, Any]) -> GestorOperacion:
        """
        Actualiza un registro existente en gestor_operacion.
        """
        try:
            gestor = self.db_pg.query(GestorOperacion).filter(
                GestorOperacion.id == gestor_id).first()
            if not gestor:
                raise ValueError(
                    f"Gestor_operacion con id {gestor_id} no encontrado")

            for key, value in data.items():
                if hasattr(gestor, key):
                    setattr(gestor, key, value)

            self.db_pg.commit()
            self.db_pg.refresh(gestor)
            logger.info(f"Gestor_operacion actualizado: {gestor.pedido}")
            return gestor
        except Exception as e:
            self.db_pg.rollback()
            logger.error(f"Error al actualizar gestor_operacion: {e}")
            raise

    # ==========================================
    # CONSULTAS VALIDACION ANULA-D
    # ==========================================

    def buscar_direcciones_en_gestor(self, direcciones_limpias: List[str]) -> List[str]:
        """
        Busca direcciones en oferta_gestion_detalle y enlistment_manager (PostgreSQL).
        Retorna las direcciones encontradas en gestiones de los últimos 60 días.
        
        Args:
            direcciones_limpias: Lista de direcciones limpias/formateadas con ML
            
        Returns:
            Lista de direcciones encontradas
        """
        if not direcciones_limpias:
            logger.warning("⚠️ Lista de direcciones vacía para búsqueda en Gestor")
            return []
        
        try:
            # Construir condiciones ILIKE dinámicamente
            condiciones_ilike = []
            for direccion in direcciones_limpias:
                # Escapar comillas simples para SQL
                direccion_escaped = direccion.replace("'", "''")
                condiciones_ilike.append(f"em.campos_dinamicos->>'direccion' ILIKE '%{direccion_escaped}%'")
            
            # Unir todas las condiciones con OR
            where_clause = " OR ".join(condiciones_ilike)
            
            query = f"""
                SELECT DISTINCT em.campos_dinamicos->>'direccion' as direccion
                FROM oferta_gestion_detalle ogd
                LEFT JOIN enlistment_manager em ON em.oferta = ogd.oferta
                WHERE ogd.accion_id IN ('40106c90-0770-464b-9f62-34c1e3ad6202') 
                  AND ogd.subaccion_id IN ('757a338c-112f-423f-9325-6c747295a492') 
                  AND ogd.fecha_gestion BETWEEN CURRENT_DATE - 60 AND CURRENT_DATE
                  AND ({where_clause})
            """
            
            logger.info(f"🔍 Buscando {len(direcciones_limpias)} direcciones en Gestor (PostgreSQL)...")
            result = self.db_pg.execute(text(query))
            
            # Extraer direcciones encontradas
            direcciones_encontradas = [row[0] for row in result.fetchall() if row[0]]
            
            logger.info(f"✅ Encontradas {len(direcciones_encontradas)} direcciones en Gestor")
            return direcciones_encontradas
            
        except Exception as e:
            logger.error(f"❌ Error al buscar direcciones en Gestor: {e}")
            raise

    def buscar_direcciones_en_gestion_operativa(self, direcciones_limpias: List[str]) -> List[str]:
        """
        Busca direcciones en FacPedidos_SSMM (SQL Server).
        Retorna las direcciones encontradas en pedidos de los últimos 60 días.
        
        Args:
            direcciones_limpias: Lista de direcciones limpias/formateadas con ML
            
        Returns:
            Lista de direcciones encontradas
        """
        if not direcciones_limpias:
            logger.warning("⚠️ Lista de direcciones vacía para búsqueda en Gestión Operativa")
            return []
        
        db_sqlserver = SessionLocalSQLServerGestion()
        try:
            # Construir condiciones LIKE dinámicamente
            condiciones_like = []
            for direccion in direcciones_limpias:
                # Escapar comillas simples para SQL
                direccion_escaped = direccion.replace("'", "''")
                condiciones_like.append(f"A.direccion LIKE '%{direccion_escaped}%'")
            
            # Unir todas las condiciones con OR
            where_clause = " OR ".join(condiciones_like)
            
            query = f"""
                SELECT DISTINCT A.direccion
                FROM dbo.FacPedidos_SSMM A WITH (NOLOCK) 
                WHERE A.FECHA BETWEEN DATEADD(DAY, -60, GETDATE()) AND DATEADD(DAY, 1, GETDATE())
                  AND A.ESTADO_CLICK IN ('Incompleto','FallidaConVisita','FallidaSinVisita')
                  AND A.comentario IN ('FUERA DE NORMA TECNICA','FUERA DE COBERTURA','RED PENDIENTE EN EDIFICIO')
                  AND ({where_clause})
            """
            
            logger.info(f"🔍 Buscando {len(direcciones_limpias)} direcciones en Gestión Operativa (SQL Server)...")
            result = db_sqlserver.execute(text(query))
            
            # Extraer direcciones encontradas
            direcciones_encontradas = [row[0] for row in result.fetchall() if row[0]]
            
            logger.info(f"✅ Encontradas {len(direcciones_encontradas)} direcciones en Gestión Operativa")
            return direcciones_encontradas
            
        except Exception as e:
            logger.error(f"❌ Error al buscar direcciones en Gestión Operativa: {e}")
            raise
        finally:
            db_sqlserver.close()
