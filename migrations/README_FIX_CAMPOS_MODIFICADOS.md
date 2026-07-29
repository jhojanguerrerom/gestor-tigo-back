# Migración: Estandarización de campos_modificados

## 📋 Descripción
Esta migración corrige el formato de las claves en el campo JSONB `campos_modificados` de la tabla `enlistment_manager_history`.

**Problema**: Algunos registros usan claves en español (`"anterior"`, `"nuevo"`) mientras que otros usan inglés (`"old"`, `"new"`).

**Solución**: Estandarizar todas las claves a inglés (`"old"`, `"new"`).

## 🎯 Cambios Realizados

### 1. Código Fuente
Se actualizó el archivo `app/services/enlistment_service.py` para usar siempre `"old"` y `"new"`:

**Antes:**
```python
"campos_modificados": {
    "estado_oferta": {"anterior": "CERRADO", "nuevo": "ABIERTO"},
    "garantia": {"anterior": False, "nuevo": True}
}
```

**Después:**
```python
"campos_modificados": {
    "estado_oferta": {"old": "CERRADO", "new": "ABIERTO"},
    "garantia": {"old": False, "new": True}
}
```

### 2. Base de Datos
Se creó el script de migración `fix_campos_modificados_keys.py` para actualizar los registros existentes.

## 🚀 Ejecución de la Migración

### Opción 1: Ejecutar directamente el script
```bash
# Activar el entorno virtual
source /workspaces/project_gestor_v2/venv/bin/activate

# Ejecutar la migración
cd /workspaces/project_gestor_v2
python -m app.migrations.fix_campos_modificados_keys
```

### Opción 2: Desde Python
```python
from app.migrations.fix_campos_modificados_keys import migrate_campos_modificados, verify_migration

# Ejecutar migración
result = migrate_campos_modificados()
print(result)

# Verificar resultado
is_ok = verify_migration()
print(f"Migración exitosa: {is_ok}")
```

## ⚠️ Consideraciones Importantes

1. **Backup**: Se recomienda hacer un backup de la tabla `enlistment_manager_history` antes de ejecutar la migración.

2. **Tiempo de ejecución**: La migración procesa registros de 100 en 100, por lo que puede tardar dependiendo del volumen de datos.

3. **Reversión**: No hay script de reversión automático. Si es necesario revertir, ejecutar:
   ```sql
   -- Este es solo un ejemplo, adaptar según sea necesario
   UPDATE enlistment_manager_history
   SET campos_modificados = (...)
   WHERE ...
   ```

4. **Verificación**: El script incluye una función `verify_migration()` que verifica que no queden registros con las claves antiguas.

## 📊 Monitoreo

Durante la ejecución, el script mostrará:
- Total de registros a actualizar
- Progreso cada 100 registros
- Resultado final con cantidad de registros actualizados

## ✅ Validación Post-Migración

Después de ejecutar la migración, verificar manualmente:

```sql
-- Verificar que no queden claves antiguas
SELECT COUNT(*)
FROM enlistment_manager_history
WHERE campos_modificados::text LIKE '%anterior%'
   OR campos_modificados::text LIKE '%nuevo%';
-- Resultado esperado: 0

-- Ver ejemplos de registros actualizados
SELECT id, oferta, campos_modificados
FROM enlistment_manager_history
WHERE campos_modificados IS NOT NULL
LIMIT 10;
```

## 📝 Historial
- **2026-03-06**: Migración creada para estandarizar claves de campos_modificados
