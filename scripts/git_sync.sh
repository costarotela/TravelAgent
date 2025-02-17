#!/bin/bash

# Colores para mensajes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Función para mostrar mensajes
print_message() {
    echo -e "${2}${1}${NC}"
}

# Función para verificar si hay cambios para commitear
check_changes() {
    if [[ -z $(git status -s) ]]; then
        print_message "No hay cambios para commitear." "$YELLOW"
        exit 0
    fi
}

# Función para verificar si el último comando se ejecutó correctamente
check_error() {
    if [ $? -ne 0 ]; then
        print_message "Error: $1" "$RED"
        exit 1
    fi
}

# Verificar si estamos en un repositorio git
if ! git rev-parse --is-inside-work-tree > /dev/null 2>&1; then
    print_message "Error: No estás en un repositorio git." "$RED"
    exit 1
fi

# Verificar cambios
check_changes

# Obtener la rama actual
current_branch=$(git branch --show-current)
print_message "Rama actual: $current_branch" "$GREEN"

# Mostrar estado actual
print_message "\nEstado actual del repositorio:" "$YELLOW"
git status

# Preguntar por el mensaje del commit
read -p "Mensaje del commit (presiona Enter para usar 'update'): " commit_message
commit_message=${commit_message:-"update"}

# Ejecutar git add
print_message "\nAgregando cambios..." "$GREEN"
git add .
check_error "No se pudieron agregar los cambios"

# Ejecutar git commit
print_message "\nCreando commit..." "$GREEN"
git commit -m "$commit_message"
check_error "No se pudo crear el commit"

# Ejecutar git push
print_message "\nSubiendo cambios a remote..." "$GREEN"
git push origin $current_branch
check_error "No se pudieron subir los cambios"

print_message "\n✅ Sincronización completada exitosamente!" "$GREEN"
