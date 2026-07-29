"""
Utilidad para procesamiento de direcciones usando modelo ML de spaCy.
Extrae la dirección principal (DIR_PRINCIPAL) de textos de direcciones.
"""
import logging
from typing import List, Dict, Optional
import pandas as pd
import spacy
from pathlib import Path

logger = logging.getLogger("direcciones_ml")

# Variable global para mantener el modelo cargado en memoria
_nlp_model = None


def cargar_modelo_direcciones(ruta_modelo: str = "app/models_ia/modelo_direcciones_col") -> spacy.language.Language:
    """
    Carga el modelo NER entrenado con spaCy para extraer direcciones.
    El modelo se carga una sola vez y se reutiliza en llamadas subsecuentes.
    
    Args:
        ruta_modelo: Ruta al directorio del modelo entrenado
        
    Returns:
        Modelo spaCy cargado
        
    Raises:
        Exception: Si el modelo no puede ser cargado
    """
    global _nlp_model
    
    if _nlp_model is None:
        try:
            logger.info(f"🔄 Cargando modelo de IA desde: '{ruta_modelo}'")
            _nlp_model = spacy.load(ruta_modelo)
            logger.info(f"✅ Modelo de IA cargado exitosamente")
        except Exception as e:
            logger.error(f"❌ Error al cargar el modelo de IA: {e}")
            raise Exception(f"No se pudo cargar el modelo desde '{ruta_modelo}'. "
                          f"Asegúrate de que la carpeta exista y contenga un modelo válido.")
    
    return _nlp_model


def extraer_direccion_principal(texto: str, nlp_model: Optional[spacy.language.Language] = None) -> str:
    """
    Extrae la dirección principal de un texto usando el modelo ML.
    
    Args:
        texto: Texto de la dirección a procesar
        nlp_model: Modelo spaCy precargado (opcional)
        
    Returns:
        Dirección principal extraída o texto original si no se detecta entidad
    """
    # Si la celda está vacía, retornar como está
    if pd.isna(texto) or not str(texto).strip():
        return texto
    
    # Cargar modelo si no se proporcionó
    if nlp_model is None:
        nlp_model = cargar_modelo_direcciones()
    
    # 1. Limpiamos y estandarizamos el texto de entrada a mayúsculas
    texto_limpio = str(texto).upper().strip()
    
    # 2. Pasamos el texto por nuestra Inteligencia Artificial
    doc = nlp_model(texto_limpio)
    
    # 3. Buscamos en las entidades detectadas la que corresponde a la dirección base
    for entidad in doc.ents:
        if entidad.label_ == "DIR_PRINCIPAL":
            # Si la IA encuentra la entidad, retornamos solo ese fragmento
            return entidad.text.strip()
    
    # 4. Si el modelo no detectó la entidad, devolvemos el texto original
    return texto_limpio


def limpiar_direcciones_con_ml(direcciones: List[str]) -> Dict[str, str]:
    """
    Procesa una lista de direcciones con el modelo ML y retorna un mapeo.
    
    Args:
        direcciones: Lista de direcciones a procesar
        
    Returns:
        Diccionario {dirección_original: dirección_limpia_ML}
    """
    if not direcciones:
        logger.warning("⚠️ Lista de direcciones vacía")
        return {}
    
    # Cargar modelo una sola vez
    nlp_model = cargar_modelo_direcciones()
    
    logger.info(f"🔄 Procesando {len(direcciones)} direcciones con ML...")
    
    resultado = {}
    for direccion in direcciones:
        if pd.notna(direccion) and str(direccion).strip():
            direccion_limpia = extraer_direccion_principal(str(direccion), nlp_model)
            resultado[str(direccion)] = direccion_limpia
        else:
            resultado[str(direccion)] = str(direccion)
    
    logger.info(f"✅ {len(resultado)} direcciones procesadas con ML")
    
    return resultado


def limpiar_direcciones_dataframe(df: pd.DataFrame, columna_direccion: str = 'direccion') -> pd.DataFrame:
    """
    Limpia direcciones en un DataFrame usando ML.
    Agrega columna 'direccion_limpia_ml' con los resultados.
    
    Args:
        df: DataFrame con columna de direcciones
        columna_direccion: Nombre de la columna que contiene las direcciones
        
    Returns:
        DataFrame con columna adicional 'direccion_limpia_ml'
    """
    if columna_direccion not in df.columns:
        logger.error(f"❌ Columna '{columna_direccion}' no encontrada en el DataFrame")
        raise ValueError(f"La columna '{columna_direccion}' no existe en el DataFrame")
    
    # Cargar modelo una sola vez
    nlp_model = cargar_modelo_direcciones()
    
    logger.info(f"🔄 Aplicando ML a columna '{columna_direccion}' ({len(df)} registros)...")
    
    # Aplicar la función de IA a toda la columna
    df['direccion_limpia_ml'] = df[columna_direccion].apply(
        lambda x: extraer_direccion_principal(x, nlp_model)
    )
    
    # Contar registros procesados exitosamente
    procesados = df['direccion_limpia_ml'].notna().sum()
    logger.info(f"✅ ML aplicado a {procesados} registros")
    
    return df
