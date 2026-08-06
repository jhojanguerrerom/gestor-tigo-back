"""
Constantes compartidas del sistema
"""

# Conceptos que deben marcarse como CERRADO_AUTOMATICO
# Estas ofertas se cierran automáticamente al cargarlas o cuando cambian a estos conceptos
CONCEPTOS_ANULACION = ['ANULA', 'ANULA-C', 'ANULA-D', 'ANULA-N']

# Conceptos que no deben salir en selección aleatoria de demepedido/congelar,
# pero sí pueden solicitarse de forma manual.
CONCEPTOS_EXCLUIDOS_ALEATORIO = ['14', 'RECONFIGURACION BOT', 'RECONFIGURACION MANUAL']
