# Guía de Desarrollo

## Control de Calidad y Actualización

Para mantener la calidad y consistencia del código, utilizamos un único script de actualización:

```bash
python scripts/update_and_push.py "mensaje del commit"
```

Este script realiza automáticamente:

1. **Actualización de Documentación**
   - Mantiene `FEATURES.md` al día con el estado del proyecto
   - Asegura que la documentación refleje el estado actual

2. **Verificaciones de Calidad** (via pre-commit)
   - Formato de código (black)
   - Verificación de estilo (flake8)
   - Ejecución de tests
   - Verificación de principios del proyecto

3. **Control de Cambios**
   - Gestión automática de git
   - Subida de cambios al repositorio

### Opciones Disponibles

- `--no-checks`: Omitir verificaciones de calidad
- `--no-push`: No subir cambios al repositorio

### Ejemplos de Uso

```bash
# Flujo completo
python scripts/update_and_push.py "feat: nueva funcionalidad de optimización"

# Solo actualizar docs sin verificaciones
python scripts/update_and_push.py --no-checks --no-push "docs: actualización de características"
```

### Principios del Proyecto

Cada archivo debe documentar cómo contribuye a los objetivos principales:

1. Elaboración de presupuestos basados en proveedores
2. Construcción dinámica con asistencia del vendedor
3. Adaptación a cambios en tiempo real
4. Interfaz interactiva para el vendedor
5. Capacidad de reconstrucción

### Hooks de pre-commit

Los hooks verifican automáticamente:

- Formato y estilo de código
- Tests unitarios
- Presencia de principios del proyecto
- Tamaño de archivos
- Sintaxis YAML
- Declaraciones de debug
