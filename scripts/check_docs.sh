#!/bin/bash

# Script para verificar la documentación del repositorio
# Asegura que los principios fundamentales estén reflejados correctamente

echo "Iniciando verificación de documentación..."

# Directorios principales
DOCS_DIR="docs"
MAIN_README="README.md"

# Lista de archivos críticos a verificar
CRITICAL_FILES=(
    "$MAIN_README"
    "$DOCS_DIR/ARQUITECTURA.md"
    "$DOCS_DIR/OLA_INTEGRATION.md"
    "$DOCS_DIR/VENDOR_INTERFACE.md"
    "$DOCS_DIR/BUDGET_ENGINE.md"
    "$DOCS_DIR/BUSINESS_RULES.md"
    "$DOCS_DIR/PREFERENCE_SYSTEM.md"
)

# Principios fundamentales a verificar
PRINCIPLES=(
    "Estabilidad Durante la Sesión"
    "Procesamiento Asíncrono"
    "Control del Vendedor"
)

# Colores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Función para verificar principios en un archivo
check_principles() {
    local file=$1
    echo -e "${YELLOW}Verificando $file...${NC}"
    
    for principle in "${PRINCIPLES[@]}"; do
        if grep -q "$principle" "$file"; then
            echo -e "${GREEN}✅ Principio '$principle' encontrado${NC}"
        else
            echo -e "${RED}⚠️ Principio '$principle' NO encontrado${NC}"
        fi
    done
    echo
}

# Verificar todos los archivos críticos
for file in "${CRITICAL_FILES[@]}"; do
    if [ -f "$file" ]; then
        check_principles "$file"
    else
        echo -e "${RED}⚠️ Archivo no encontrado: $file${NC}"
    fi
done

# Verificar estructura de priorización
echo -e "${YELLOW}Verificando estructura de priorización...${NC}"
for file in "${CRITICAL_FILES[@]}"; do
    if [ -f "$file" ]; then
        if grep -q "IMPRESCINDIBLE\|PARCIALMENTE NECESARIO\|OMITIBLE" "$file"; then
            echo -e "${GREEN}✅ Estructura de priorización encontrada en $file${NC}"
        else
            echo -e "${RED}⚠️ Estructura de priorización NO encontrada en $file${NC}"
        fi
    fi
done

echo
echo -e "${GREEN}Verificación completada.${NC}"
