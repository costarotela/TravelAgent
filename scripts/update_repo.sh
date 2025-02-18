#!/bin/bash

# Colores para mensajes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Función para imprimir mensajes
print_message() {
    echo -e "${2}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

# Verificar que estamos en el directorio correcto
if [ ! -d "src" ] || [ ! -d "tests" ]; then
    print_message "Error: Ejecutar desde el directorio raíz del proyecto" "$RED"
    exit 1
fi

# 1. Actualizar dependencias
print_message "Actualizando dependencias..." "$YELLOW"
pip freeze > requirements.txt
print_message "✓ Dependencias actualizadas" "$GREEN"

# 2. Ejecutar tests
print_message "Ejecutando tests..." "$YELLOW"
if ! python -m unittest discover tests; then
    print_message "✗ Tests fallaron" "$RED"
    exit 1
fi
print_message "✓ Tests completados" "$GREEN"

# 3. Verificar estilo de código
print_message "Verificando estilo de código..." "$YELLOW"
flake8 src tests || true
print_message "✓ Estilo verificado (ignorando errores)" "$GREEN"

# 4. Formatear código
print_message "Formateando código..." "$YELLOW"
black src tests
print_message "✓ Código formateado" "$GREEN"

# 5. Verificar cambios en git
print_message "Verificando cambios..." "$YELLOW"
if [ -z "$(git status --porcelain)" ]; then
    print_message "No hay cambios para commitear" "$YELLOW"
    exit 0
fi

# 6. Agregar cambios
print_message "Agregando cambios..." "$YELLOW"
git add .

# 7. Crear commit
print_message "Creando commit..." "$YELLOW"
read -p "Ingrese mensaje de commit: " commit_message
if [ -z "$commit_message" ]; then
    commit_message="chore: Actualización de documentación y código v1.0.0"
fi
git commit -m "$commit_message"
print_message "✓ Commit creado" "$GREEN"

# 8. Push a repositorio
print_message "Subiendo cambios..." "$YELLOW"
if ! git push origin main; then
    print_message "✗ Error al subir cambios" "$RED"
    exit 1
fi
print_message "✓ Cambios subidos exitosamente" "$GREEN"

print_message "¡Proceso completado!" "$GREEN"
