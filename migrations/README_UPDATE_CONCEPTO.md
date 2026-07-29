# Migración: Actualizar concepto desde concepto_id

## 📋 Descripción

Esta migración actualiza el campo `concepto` dentro del JSONB `campos_dinamicos` de la tabla `enlistment_manager`, reemplazando su valor con el contenido de `concepto_id` cuando este último tiene un valor válido (no nulo ni vacío).

## 🎯 Objetivo

Sincronizar automáticamente el campo `concepto` con `concepto_id` en todos los registros existentes, aplicando la misma lógica implementada en el proceso de carga de datos (`automation_service.py`).

## 📊 Alcance

- **Tabla afectada**: `enlistment_manager`
- **Campo modificado**: `campos_dinamicos->>'concepto'`
- **Condición**: Solo actualiza cuando `concepto_id` no es nulo ni cadena vacía

## 🔍 Lógica de Negocio

La migración implementa la siguiente lógica:

```python
if concepto_id is not None and concepto_id.strip() != '':
    concepto = concepto_id
```

### Ejemplo de Transformación

| Antes | Después |
|-------|---------|
| `"concepto": "Sin_Pendiente"` <br> `"concepto_id": "Pendiente Provisión"` | `"concepto": "Pendiente Provisión"` <br> `"concepto_id": "Pendiente Provisión"` |
| `"concepto": "Reconfigurar"` <br> `"concepto_id": null` | Sin cambios |
| `"concepto": "ANULA"` <br> `"concepto_id": ""` | Sin cambios |

## 🚀 Ejecución

### Desde línea de comandos

```bash
cd /Users/oscarloaiza/Desktop/Trabajo/Desktop/OperacionTigo/project_gestor_v2
python -m app.migrations.update_concepto_from_concepto_id
```

### Desde código Python

```python
from app.migrations.update_concepto_from_concepto_id import (
    migrate_concepto_from_concepto_id,
    verify_migration
)

# Ejecutar migración
resultado = migrate_concepto_from_concepto_id()
print(f"Registros actualizados: {resultado['rows_updated']}")

# Verificar migración
verificacion = verify_migration()
print(f"Sincronizados: {verificacion['sincronizados']}")
print(f"Desincronizados: {verificacion['desincronizados']}")
```

## ✅ Verificación

La migración incluye una función de verificación que:

1. Cuenta el total de registros con `concepto_id` válido
2. Identifica cuántos están sincronizados (`concepto` = `concepto_id`)
3. Identifica cuántos están desincronizados (`concepto` ≠ `concepto_id`)

### Consulta SQL de Verificación

```sql
SELECT 
    COUNT(*) as total_con_concepto_id,
    SUM(CASE 
        WHEN campos_dinamicos->>'concepto' = campos_dinamicos->>'concepto_id' 
        THEN 1 
        ELSE 0 
    END) as sincronizados,
    SUM(CASE 
        WHEN campos_dinamicos->>'concepto' != campos_dinamicos->>'concepto_id' 
        THEN 1 
        ELSE 0 
    END) as desincronizados
FROM enlistment_manager
WHERE campos_dinamicos->>'concepto_id' IS NOT NULL
  AND TRIM(campos_dinamicos->>'concepto_id') != '';
```

## 📝 Notas Técnicas

### Rendimiento
- La migración procesa registros en lotes con commit cada 100 registros
- Actualiza solo los registros que cumplan las condiciones
- Incluye índices JSONB para optimizar las consultas

### Transacciones
- Usa transacciones para garantizar atomicidad
- Hace rollback automático en caso de error
- Cierra la sesión de base de datos en el bloque `finally`

### Logging
- Registra el progreso cada 100 registros
- Log inicial con total de registros a procesar
- Log final con resumen de registros actualizados

## 🔗 Archivos Relacionados

- **Servicio**: [`app/services/automation_service.py`](../services/automation_service.py) (líneas 241-267)
- **Modelo**: [`app/models/enlistment_manager_model.py`](../models/enlistment_manager_model.py)
- **Migración**: [`app/migrations/update_concepto_from_concepto_id.py`](./update_concepto_from_concepto_id.py)

## 📅 Fecha de Creación

**11 de marzo de 2026**

## 👤 Autor

Sistema de Gestión de Operaciones - Project Gestor V2
