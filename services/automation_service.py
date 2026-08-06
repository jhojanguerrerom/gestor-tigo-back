import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
import pandas as pd
from app.repositories.automation_repository import AutomationRepository
from app.services.enlistment_service import EnlistmentService
from app.utils.direcciones_ml import limpiar_direcciones_con_ml, cargar_modelo_direcciones

logger = logging.getLogger("automation_service")


class AutomationService:
    """
    Servicio para automatización de carga de datos de Fenix y Siebel.
    Traduce la lógica de negocio del controlador Automation.php de CodeIgniter.
    """

    def __init__(self, db: Session):
        """Inicializa el service con la sesión de base de datos.
        
        Args:
            db: Sesión de SQLAlchemy inyectada por dependency
        """
        self.db = db
        self.repository = AutomationRepository(db)
        self.enlistment_service = EnlistmentService(db)

    # ==========================================
    # PROCESAMIENTO DE DATOS GESTOR
    # ==========================================
    async def process_data_gestor(self, is_returnable: bool = False) -> Dict[str, Any]:
        try:
            res_siebel = self.repository.get_data_siebel()

            # Convertir a DataFrame de pandas
            df_siebel = pd.DataFrame(res_siebel)

            logger.info(f"Total registros originales: {len(df_siebel)}")

            # Eliminar duplicados basados en el campo oferta, manteniendo solo la primera aparición
            df_siebel = df_siebel.drop_duplicates(subset='oferta', keep='first')
            logger.info(f"Total registros después de eliminar duplicados: {len(df_siebel)}")


            # Obtener lista de ofertas únicas
            ofertas_unicas = df_siebel['oferta'].tolist()
            
            # Dividir en listas de máximo 1000 ofertas
            batch_size = 1000
            ofertas_por_lotes = [
                ofertas_unicas[i:i + batch_size] 
                for i in range(0, len(ofertas_unicas), batch_size)
            ]
            
            logger.info(f"Total de lotes creados: {len(ofertas_por_lotes)}")
            logger.info(f"Ofertas en el último lote: {len(ofertas_por_lotes[-1]) if ofertas_por_lotes else 0}")
            
            # Procesar cada lote de ofertas y obtener datos de Fenix
            all_fenix_data = []
            for i, ofertas in enumerate(ofertas_por_lotes):
                logger.info(f"Procesando lote {i+1}/{len(ofertas_por_lotes)} con {len(ofertas)} ofertas")
                res_fenix = self.repository.get_data_fenix(ofertas)
                logger.info(f"Total de pedidos fenix en lote {i+1}: {len(res_fenix)}")
                all_fenix_data.extend(res_fenix)
            
            # Crear DataFrame con todos los datos de Fenix
            df_fenix = pd.DataFrame(all_fenix_data)
            logger.info(f"Total de registros de Fenix obtenidos: {len(df_fenix)}")
            
            # Fusionar DataFrames: df_siebel (principal) con df_fenix
            # Relación: oferta (df_siebel) = pedido_crm (df_fenix)
            df_merged = pd.merge(
                df_siebel,
                df_fenix,
                left_on='oferta',
                right_on='pedido_crm',
                how='left',
                suffixes=('_siebel', '_fenix')
            )
            
            logger.info(f"Total de registros después de la fusión: {len(df_merged)}")
            logger.info(f"Columnas del DataFrame fusionado: {df_merged.columns.tolist()}")
            
            # ==========================================
            # Preservar concepto original antes de modificaciones
            # ==========================================
            df_merged['concepto_original'] = df_merged['concepto'].copy()
            logger.info(f"Columna 'concepto_original' creada con {df_merged['concepto_original'].notna().sum()} registros")
            
            # ==========================================
            # Bloque de obtener TECNOLOGIA, PRODUCTO, UEN de SIEBEL y agregar en el dataframe
            # Procesar cada lote de ofertas
            all_items_data = []
            for i, ofertas in enumerate(ofertas_por_lotes):
                logger.info(f"Procesando lote de items {i+1}/{len(ofertas_por_lotes)} con {len(ofertas)} ofertas")
                res_siebel_items = self.repository.get_data_siebel_items(ofertas)
                logger.info(f"Total de items siebel en lote {i+1}: {len(res_siebel_items)}")
                all_items_data.extend(res_siebel_items)
            
            # Crear DataFrame con todos los datos de Fenix
            df_siebel_items = pd.DataFrame(all_items_data)
            logger.info(f"Total de registros de Siebel Items obtenidos: {len(df_siebel_items)}")
            
            df_merged = pd.merge(
                df_merged,
                df_siebel_items,
                left_on='oferta',
                right_on='oferta',
                how='left',
                suffixes=('_siebel_items', '_fenix')
            )
            # ==========================================
            
            # ==========================================
            # Bloque de obtener FLAG de SIEBEL y agregar en el dataframe
            # Procesar cada lote de ofertas
            all_flag_data = []
            for i, ofertas in enumerate(ofertas_por_lotes):
                logger.info(f"Procesando lote de flag {i+1}/{len(ofertas_por_lotes)} con {len(ofertas)} ofertas")
                res_siebel_flag = self.repository.get_data_siebel_flag(ofertas)
                logger.info(f"Total de flag siebel en lote {i+1}: {len(res_siebel_flag)}")
                all_flag_data.extend(res_siebel_flag)
            
            # Crear DataFrame con todos los datos de Fenix
            df_siebel_flag = pd.DataFrame(all_flag_data)
            logger.info(f"Total de registros de Siebel Flag obtenidos: {len(df_siebel_flag)}")
            
            df_merged = pd.merge(
                df_merged,
                df_siebel_flag,
                left_on='oferta',
                right_on='oferta',
                how='left',
                suffixes=('_siebel_flag', '_fenix')
            )
            # ==========================================
            
            # ==========================================
            # Bloque reemplazo de concepto por concepto_id
            # Si concepto_id tiene un valor válido (no nulo ni vacío), 
            # reemplazar el valor del campo concepto con concepto_id
            # IMPORTANTE: Este bloque debe ejecutarse ANTES de las validaciones ANULA-C
            # para que las validaciones evalúen el concepto_id correcto
            # ==========================================
            
            # Crear máscara para identificar registros con concepto_id válido
            mask_concepto_id_valido = (
                df_merged['concepto_id'].notna() &  # No es nulo
                (df_merged['concepto_id'] != '') &   # No es cadena vacía
                (df_merged['concepto_id'].astype(str).str.strip() != '')  # No es solo espacios
            )
            
            # Contar registros que serán actualizados
            count_reemplazo = mask_concepto_id_valido.sum()
            
            if count_reemplazo > 0:
                # Reemplazar concepto con concepto_id para los registros válidos
                df_merged.loc[mask_concepto_id_valido, 'concepto'] = df_merged.loc[mask_concepto_id_valido, 'concepto_id']
                logger.info(f"Reemplazo concepto por concepto_id: {count_reemplazo} registros actualizados")
            else:
                logger.info("No se encontraron registros con concepto_id válido para reemplazo")
            
            # ==========================================
            
            # ==========================================
            # Bloque de Validacion ANULA-C
            # Inicializar columna validacion_anulacion
            df_merged['validacion_anulacion'] = None
            logger.info("Columna 'validacion_anulacion' inicializada")
            
            # Validación 1: Reconfigurar por cobertura con flags en NO
            # mask_validacion_1 = (
            #     (df_merged['concepto'] == 'Reconfigurar por cobertura') &
            #     (df_merged['estado_direccion'].isin(['M', 'N', 'Y'])) &
            #     (df_merged['flag_hfc'] == 'NO') &
            #     (df_merged['flag_gpon'] == 'NO') &
            #     (df_merged['flag_tercero'] == 'NO')
            # )
            
            # count_validacion_1 = mask_validacion_1.sum()
            # if count_validacion_1 > 0:
            #     df_merged.loc[mask_validacion_1, 'concepto'] = 'ANULA-C'
            #     df_merged.loc[mask_validacion_1, 'validacion_anulacion'] = 'COBERTURA'
            #     logger.info(f"Validación ANULA 1: {count_validacion_1} registros actualizados (Reconfigurar por cobertura) - validacion_anulacion: COBERTURA")
            
            # Validación 2: Pendiente Provisión Tercero
            # Corregido: Paréntesis para que la condición UEN aplique a TODOS los conceptos
            mask_validacion_2 = (
                (
                    (df_merged['concepto'] == 'Pendiente Provisión Tercero') |
                    (df_merged['concepto'] == 'PSERV') |
                    (df_merged['concepto'] == 'PSIEB') |
                    (df_merged['concepto'] == 'PRESI')
                ) &
                (df_merged['uen'].str.upper() == 'RESIDENCIAL')
            )
            
            count_validacion_2 = mask_validacion_2.sum()
            if count_validacion_2 > 0:
                df_merged.loc[mask_validacion_2, 'concepto'] = 'ANULA-C'
                df_merged.loc[mask_validacion_2, 'validacion_anulacion'] = 'CONCEPTO_ID'
                logger.info(f"Validación ANULA 2: {count_validacion_2} registros actualizados (Pendiente Provisión Tercero) - validacion_anulacion: CONCEPTO_ID")
            
            # Validación 3: Pendiente Provisión sin pedido_id ni concepto_id
            # mask_validacion_3 = (
            #     (df_merged['concepto'] == 'Pendiente Provisión') &
            #     (
            #         (df_merged['pedido_id'].isna()) | 
            #         (df_merged['pedido_id'] == '') | 
            #         (df_merged['pedido_id'].astype(str).str.strip() == '')
            #     ) &
            #     (
            #         (df_merged['concepto_id'].isna()) | 
            #         (df_merged['concepto_id'] == '') | 
            #         (df_merged['concepto_id'].astype(str).str.strip() == '')
            #     )
            # )
            
            # count_validacion_3 = mask_validacion_3.sum()
            # if count_validacion_3 > 0:
            #     df_merged.loc[mask_validacion_3, 'concepto'] = 'ANULA-C'
            #     df_merged.loc[mask_validacion_3, 'validacion_anulacion'] = 'CONCEPTO_ID'
            #     logger.info(f"Validación ANULA 3: {count_validacion_3} registros actualizados (Pendiente Provisión sin pedido_id ni concepto_id) - validacion_anulacion: CONCEPTO_ID")
            
            # logger.info(f"Total de registros marcados como ANULA-C: {count_validacion_1 + count_validacion_2 + count_validacion_3}")
            logger.info(f"Total de registros marcados como ANULA-C: {count_validacion_2}")
            # ==========================================
            
            # ==========================================
            # Agregar columna 'garantia' con valor por defecto False
            # ==========================================
            df_merged['garantia'] = False
            logger.info("Columna 'garantia' agregada con valor por defecto False")
            
            # Agregar columna 'responsable' con validaciones
            def asignar_responsable(row):
                # Lista de conceptos para las validaciones
                conceptos_anulados = [
                    'Solicitud Anulada(ANULA)',
                    'Anul  por Garantia en el ingreso(AXGAR)',
                    'Acceso aprobado(OKRED)',
                    'Pendiente Estudio Técnico(PETEC)',
                    'Pendiente de respuesta SMPRO(PSMPR)',
                    'Requiere revisión de la Unidad de Medición(PUMED)',
                    'Pendiente por Reconfigurar Oferta(14)',
                    'Reestudio Técnico(15)',
                    'Anul por cobertura(36)',
                    'Anul por decisión del cliente(42)',
                    'Anul sin diponibilidad técnica(43)',
                    'Pendiente Identificador de Llamada(65)',
                    'Pendiente Circuito en Central(70)',
                    'Inconsistencia de la Información(99)',
                    'Carga Infraestructura en Inventario(19)'
                ]
                
                concepto_matriz = [
                    'Migracion Cablera (OT-T06)',
                    'Pendiente por circuito en el Carrier',
                    'Actualizar-citofonía virtual',
                    'Cambio número-citofonía',
                    'Cancelar motivo técnico',
                    'Cancelar motivo técnico (OT-C11)',
                    'Cobertura',
                    'Construcción',
                    'Disponibilidad',
                    'Error estudio Técnico',
                    'Factibilidad manual',
                    'Mala Asignación (OT-T05)',
                    'Pendiente Provisión',
                    'Reconfigurar motivo técnico',
                    'Reconfigurar motivo tecnico (OT-C12)',
                    'Reconfigurar pedido',
                    'Reconfigurar por cobertura',
                    'Reconfigurar x disp. Fenix',
                    'Reconfigurar x disponibilidad',
                    'Retiro-Citofonía Virtual',
                    'Validar Configuración Técnica',
                    'PENDIENTE MALA ASIGNACION',
                    'Pendiente Errores no Reintentables',
                    'Pendiente por Mala Asignación',
                    'Pendiente Estudio Técnico',
                    'Pendiente por cumplido de la solucion',
                    'Carga Infraestructura en Inventario',
                    'Pendiente por Reconfigurar Oferta',
                    'Errores en Fénix',
                    'Pendiente numeración',
                    'Renumerar o Reconfigurar Oferta',
                    'Prospecto por circuito bastidor (Puerto DSL)',
                    'Pendiente por orden del puerto',
                    'Reestudio Técnico',
                    'Requiere revisión de la Unidad de Medición',
                    'Verificar Asignacion',
                    'Reconfiguracion en Oferta',
                    'Conservar Numero',
                    'Verificar Disponibilidad',
                    'Pendiente por otro componente del paquete',
                    'Mala Asignación',
                    'Pendiente Asignar Numeracion',
                    'Pendiente por Configuración',
                    'Pendiente Por Filiales',
                    'Pendiente vencido Tecnico',
                    'PENDIENTE DE ASIGNACIÓN',
                    'Migración cablera',
                    'Corregir Microzona',
                    'Pendiente por Dirección IP',
                    'Pendiente Provisión Tercero',
                    'Premisas Extendidas',
                    'ANULA-C',
                    'Envío diseño',
                    'Normalizacion'
                ]
                
                # Validación 1
                if (row.get('concepto_original') in ['Sin_Pendiente', 'Sin_Pendiente_Abierto', 'Confirmar oferta reconfigurada'] and
                    row.get('disponibilidad') == 'Factibilidad Negativa,Recurso no Disponible,'):
                    return 'Eliana Henao'
                
                # Validación 2
                if (row.get('concepto_original') == 'Sin_Pendiente_Abierto' and
                    row.get('disponibilidad') == 'Pendiente'):
                    return 'Eliana Henao'
                
                # Validación 3
                if (row.get('concepto_original') == 'Pendiente Provisión' and
                    row.get('concepto_telefonia') in conceptos_anulados):
                    return 'Eliana Henao'
                
                # Validación 4
                if (row.get('concepto_original') == 'Pendiente Provisión' and
                    pd.isna(row.get('concepto_telefonia')) and
                    row.get('concepto_internet') in conceptos_anulados):
                    return 'Eliana Henao'
                
                # Validación 5
                if (row.get('concepto_original') == 'Pendiente Provisión' and
                    pd.isna(row.get('concepto_internet')) and
                    row.get('concepto_television') in conceptos_anulados):
                    return 'Eliana Henao'
                
                # Validación 6
                if (row.get('concepto_original') == 'Pendiente Provisión' and
                    row.get('estado_oferta') == 'Disponibilidad' and
                    (row.get('tipo_transaccion_internet') == 'NA Nuevo' or
                     row.get('tipo_transaccion_television') == 'NA Nuevo' or
                     row.get('tipo_transaccion_telefonia') == 'NA Nuevo')):
                    return 'Eliana Henao'
                
                # # Validacion Automatica
                # if (row.get('concepto_original') == 'Pendiente Provisión' and
                #     row.get('estado_oferta') == 'Disponibilidad'):
                #     return 'Automatico'
                
                # Validación 7
                if (row.get('concepto_original') in concepto_matriz):
                    return 'Eliana Henao'
                
                return None
            
            # Aplicar la función para crear la columna 'responsable'
            df_merged['responsable'] = df_merged.apply(asignar_responsable, axis=1)
            
            logger.info(f"Columna 'responsable' agregada. Registros con responsable asignado: {df_merged['responsable'].notna().sum()}")
            
            # ==========================================
            # Bloque reemplazo de concepto basado en UEN
            # Si concepto = 14 y UEN es Residencial entonces concepto = RECONFIGURACION BOT
            # Si concepto = 14 y UEN es Empresarial entonces concepto = RECONFIGURACION MANUAL
            # ==========================================
            
            # Validación para concepto = '14' con UEN Residencial
            mask_reconfiguracion_bot = (
                (
                    (df_merged['concepto'] == '14') |
                    (df_merged['concepto'].str.upper() == 'PREMISAS EXTENDIDAS')
                ) &
                (df_merged['uen'].str.upper() == 'RESIDENCIAL')
            )
            
            count_bot = mask_reconfiguracion_bot.sum()
            if count_bot > 0:
                df_merged.loc[mask_reconfiguracion_bot, 'concepto'] = 'RECONFIGURACION BOT'
                logger.info(f"Reemplazo concepto '14' por 'RECONFIGURACION BOT' (UEN Residencial): {count_bot} registros actualizados")
            
            # Validación para concepto = '14' con UEN Empresarial
            mask_reconfiguracion_manual = (
                (
                    (df_merged['concepto'] == '14') |
                    (df_merged['concepto'].str.upper() == 'PREMISAS EXTENDIDAS')
                ) &
                (df_merged['uen'].str.upper() == 'EMPRESARIAL')
            )
            
            count_manual = mask_reconfiguracion_manual.sum()
            if count_manual > 0:
                df_merged.loc[mask_reconfiguracion_manual, 'concepto'] = 'RECONFIGURACION MANUAL'
                logger.info(f"Reemplazo concepto '14' por 'RECONFIGURACION MANUAL' (UEN Empresarial): {count_manual} registros actualizados")
            
            # ==========================================
            
            # Limpiar los Responsables Null y conceptos FACTU
            registros_antes = len(df_merged)
            df_merged = df_merged[
                (df_merged['responsable'].notna()) &
                (df_merged['concepto'] != 'FACTU')
            ]
            registros_despues = len(df_merged)
            registros_eliminados = registros_antes - registros_despues
            logger.info(f"Registros eliminados (responsable Null o concepto FACTU): {registros_eliminados}. Registros restantes: {registros_despues}")
            
            # Eliminar registros donde concepto o concepto_original sea Sin_Pendiente_Abierto
            registros_antes_sin_pendiente = len(df_merged)
            df_merged = df_merged[
                (df_merged['concepto'] != 'Sin_Pendiente_Abierto') &
                (df_merged['concepto_original'] != 'Sin_Pendiente_Abierto')
            ]
            registros_despues_sin_pendiente = len(df_merged)
            registros_eliminados_sin_pendiente = registros_antes_sin_pendiente - registros_despues_sin_pendiente
            logger.info(f"Registros eliminados (concepto o concepto_original = Sin_Pendiente_Abierto): {registros_eliminados_sin_pendiente}. Registros restantes: {registros_despues_sin_pendiente}")
            
            # ==========================================
            # Bloque reemplazo de concepto basado en direcciones (ANULA-D)
            # ==========================================
            
            logger.info("🔎 Iniciando validación ANULA-D por direcciones...")
            
            try:
                # Paso 1: Extraer y limpiar direcciones del dataframe con ML
                if 'direccion' in df_merged.columns:
                    logger.info("🤖 Paso 1: Limpiando direcciones con modelo ML...")
                    
                    # Filtrar direcciones no nulas y no vacías
                    direcciones_originales = df_merged['direccion'].dropna()
                    direcciones_originales = direcciones_originales[direcciones_originales.astype(str).str.strip() != '']
                    direcciones_unicas = direcciones_originales.unique().tolist()
                    
                    logger.info(f"   Total direcciones únicas a procesar: {len(direcciones_unicas)}")
                    
                    # Aplicar ML para obtener direcciones principales
                    if direcciones_unicas:
                        # Cargar modelo una sola vez
                        nlp_model = cargar_modelo_direcciones()
                        
                        # Procesar direcciones con ML
                        mapa_direcciones_ml = limpiar_direcciones_con_ml(direcciones_unicas)
                        direcciones_limpias = list(set(mapa_direcciones_ml.values()))  # Eliminar duplicados
                        
                        logger.info(f"   ✅ Direcciones limpiadas con ML: {len(direcciones_limpias)}")
                        
                        # Paso 2: Búsqueda en PostgreSQL (Gestor)
                        logger.info("📊 Paso 2: Buscando direcciones en Gestor (PostgreSQL)...")
#                        direcciones_encontradas_gestor = self.repository.buscar_direcciones_en_gestor(direcciones_limpias)
                        direcciones_encontradas_gestor = False

                        # Aplicar ML a las direcciones encontradas en Gestor
                        if direcciones_encontradas_gestor:
                            logger.info(f"   🤖 Aplicando ML a {len(direcciones_encontradas_gestor)} direcciones encontradas en Gestor...")
                            mapa_gestor_ml = limpiar_direcciones_con_ml(direcciones_encontradas_gestor)
                            direcciones_gestor_limpias = set(mapa_gestor_ml.values())
                            
                            # Marcar coincidencias en el dataframe
                            logger.info(f"   🔍 Buscando coincidencias en el dataframe...")
                            
                            # Crear mapeo inverso: dirección limpia ML -> dirección original
                            mapa_inverso = {v: k for k, v in mapa_direcciones_ml.items()}
                            
                            # Buscar registros que coincidan (excluir UEN EMPRESARIAL)
                            mask_anula_gestor = df_merged.apply(
                                lambda row: (
                                    pd.notna(row.get('direccion')) and
                                    str(row.get('uen') or '').upper() != 'EMPRESARIAL' and
                                    mapa_direcciones_ml.get(str(row['direccion']), '') in direcciones_gestor_limpias
                                ),
                                axis=1
                            )
                            
                            count_anula_gestor = mask_anula_gestor.sum()
                            if count_anula_gestor > 0:
                                # Cambiar concepto a ANULA-D
                                df_merged.loc[mask_anula_gestor, 'concepto'] = 'ANULA-D'
                                df_merged.loc[mask_anula_gestor, 'validacion_anulacion'] = 'DIRECCION'
                                
                                # Asignar directamente validacion_anulacion_direccion (NO anidado en campos_dinamicos)
                                df_merged.loc[mask_anula_gestor, 'validacion_anulacion_direccion'] = 'GESTOR'

                                logger.info(f"   ✅ ANULA-D (GESTOR): {count_anula_gestor} registros marcados")
                            else:
                                logger.info(f"   ℹ️ No se encontraron coincidencias en Gestor")
                        else:
                            logger.info(f"   ℹ️ No se encontraron direcciones en Gestor")
                        
                        # Paso 3: Obtener direcciones NO encontradas en Gestor para SQL Server
                        logger.info("📊 Paso 3: Preparando búsqueda en Gestión Operativa (SQL Server)...")
                        
                        # Direcciones que NO fueron marcadas como ANULA-D por Gestor
                        direcciones_no_gestor = set(direcciones_limpias)
                        if direcciones_encontradas_gestor:
                            direcciones_gestor_limpias_set = set(mapa_gestor_ml.values())
                            direcciones_no_gestor = direcciones_no_gestor - direcciones_gestor_limpias_set
                        
                        direcciones_no_gestor_list = list(direcciones_no_gestor)
                        logger.info(f"   Direcciones pendientes para SQL Server: {len(direcciones_no_gestor_list)}")
                        
                        # Paso 4: Búsqueda en SQL Server (Gestión Operativa)
                        if direcciones_no_gestor_list:
                            logger.info(f"   🔍 Buscando en Gestión Operativa...")
                            direcciones_encontradas_sqlserver = self.repository.buscar_direcciones_en_gestion_operativa(direcciones_no_gestor_list)
                            
                            # Aplicar ML a las direcciones encontradas en SQL Server
                            if direcciones_encontradas_sqlserver:
                                logger.info(f"   🤖 Aplicando ML a {len(direcciones_encontradas_sqlserver)} direcciones encontradas en SQL Server...")
                                mapa_sqlserver_ml = limpiar_direcciones_con_ml(direcciones_encontradas_sqlserver)
                                direcciones_sqlserver_limpias = set(mapa_sqlserver_ml.values())
                                
                                # Marcar coincidencias en el dataframe (solo las que NO fueron marcadas por Gestor)
                                logger.info(f"   🔍 Buscando coincidencias en el dataframe...")
                                
                                mask_anula_sqlserver = df_merged.apply(
                                    lambda row: (
                                        pd.notna(row.get('direccion')) and
                                        row.get('concepto') != 'ANULA-D' and  # No sobrescribir las ya marcadas
                                        str(row.get('uen') or '').upper() != 'EMPRESARIAL' and
                                        mapa_direcciones_ml.get(str(row['direccion']), '') in direcciones_sqlserver_limpias
                                    ),
                                    axis=1
                                )
                                
                                count_anula_sqlserver = mask_anula_sqlserver.sum()
                                if count_anula_sqlserver > 0:
                                    # Cambiar concepto a ANULA-D
                                    df_merged.loc[mask_anula_sqlserver, 'concepto'] = 'ANULA-D'
                                    df_merged.loc[mask_anula_sqlserver, 'validacion_anulacion'] = 'DIRECCION'
                                    
                                    # Asignar directamente validacion_anulacion_direccion (NO anidado en campos_dinamicos)
                                    df_merged.loc[mask_anula_sqlserver, 'validacion_anulacion_direccion'] = 'GESTION_OPERATIVA'

                                    logger.info(f"   ✅ ANULA-D (GESTION_OPERATIVA): {count_anula_sqlserver} registros marcados")
                                else:
                                    logger.info(f"   ℹ️ No se encontraron coincidencias en SQL Server")
                            else:
                                logger.info(f"   ℹ️ No se encontraron direcciones en SQL Server")
                        else:
                            logger.info(f"   ℹ️ No hay direcciones pendientes para buscar en SQL Server")
                        
                        # Resumen final
                        total_anula_d = (df_merged['concepto'] == 'ANULA-D').sum()
                        logger.info(f"✅ Validación ANULA-D completada. Total registros ANULA-D: {total_anula_d}")
                    else:
                        logger.info("ℹ️ No hay direcciones únicas para procesar")
                else:
                    logger.warning("⚠️ Columna 'direccion' no encontrada en el dataframe")
                    
            except Exception as e:
                logger.error(f"❌ Error en validación ANULA-D por direcciones: {e}", exc_info=True)
                # No fallar el proceso completo, continuar con el resto
                logger.warning("⚠️ Continuando con el proceso a pesar del error en ANULA-D")
            
            # ==========================================
            
            
            # Convertir campos de fecha de UTC a UTC-5 (hora de Bogotá)
            campos_fecha = ['fecha_creado', 'fecha_estado', 'fecha_pendiente']
            
            for campo in campos_fecha:
                if campo in df_merged.columns:
                    # Convertir a datetime si no lo es ya
                    df_merged[campo] = pd.to_datetime(df_merged[campo], errors='coerce')
                    
                    # Aplicar conversión UTC-5 solo a valores no nulos
                    mask = df_merged[campo].notna()
                    if mask.any():
                        # Asignar timezone UTC y luego convertir a America/Bogota (UTC-5)
                        df_merged.loc[mask, campo] = (
                            df_merged.loc[mask, campo]
                            .dt.tz_localize('UTC', ambiguous='NaT', nonexistent='NaT')
                            .dt.tz_convert('America/Bogota')
                            .dt.tz_localize(None)  # Remover timezone info para mantener solo la hora local
                        )
                        logger.info(f"Campo '{campo}' convertido a UTC-5. Registros convertidos: {mask.sum()}")
            
            # Reemplazar valores NaN, NaT e infinitos con None para serialización correcta
            df_merged = df_merged.replace({pd.NaT: None, pd.NA: None})
            df_merged = df_merged.where(pd.notna(df_merged), None)
            
            # Convertir el DataFrame fusionado a lista de diccionarios
            data_merged = df_merged.to_dict('records')
            columnas = df_merged.columns.tolist()
            
            # ==========================================
            # ALMACENAR EN ENLISTMENT_MANAGER
            # ==========================================
            logger.info("🚀 Almacenando datos en Enlistment Manager...")
            try:
                enlistment_result = await self.enlistment_service.process_and_store(
                    data_merged=data_merged,
                    columnas=columnas
                )
                logger.info("✅ Datos almacenados exitosamente en Enlistment Manager")
                logger.info(f"   Ticket: {enlistment_result['ticket_carga']}")
                logger.info(f"   Nuevos: {enlistment_result['nuevos']}, Modificados: {enlistment_result['modificados']}, Sin cambios: {enlistment_result['sin_cambios']}")
            except Exception as e:
                logger.error(f"❌ Error al almacenar en Enlistment Manager: {e}", exc_info=True)
                # No fallar la respuesta principal si falla el almacenamiento
                enlistment_result = None
            
            return {
                "type": "success", 
                "msg": "Data process successfull",
            }
        except Exception as e:
            logger.error(f"Error al procesar datos de Siebel: {e}")
            if is_returnable:
                raise
            return {"type": "error", "msg": str(e)}
