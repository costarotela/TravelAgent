#!/usr/bin/env python3
"""Script para actualizar documentación y subir cambios al repositorio.

Este script:
1. Actualiza la documentación con las características implementadas
2. Ejecuta los tests para verificar que todo funciona
3. Sube los cambios al repositorio remoto

Uso:
    python scripts/update_and_push.py [--no-tests] [--no-push] "Mensaje del commit"
"""

import argparse
import os
import subprocess
import sys
from datetime import datetime
from typing import List, Dict, Any

def run_command(cmd: List[str], cwd: str = None) -> subprocess.CompletedProcess:
    """Ejecuta un comando y retorna el resultado."""
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)

def update_features_doc() -> None:
    """Actualiza el archivo de características con las implementadas."""
    features = {
        "Optimización de Precios": {
            "status": "✅ Completado",
            "details": [
                "Múltiples estrategias de pricing",
                "ROI y margen optimizados",
                "Adaptación a calidad del hotel",
                "Factores de competencia y demanda",
                "Tests completos"
            ]
        },
        "Comparación de Paquetes": {
            "status": "🚧 En Desarrollo",
            "details": [
                "Comparación de características",
                "Análisis de precios",
                "Tests en progreso"
            ]
        },
        "Interfaz de Usuario": {
            "status": "📝 Pendiente",
            "details": [
                "Diseño de UI interactiva",
                "Integración con backend",
                "Experiencia del vendedor"
            ]
        },
        "Integración con Proveedores": {
            "status": "🚧 En Desarrollo",
            "details": [
                "Extracción de datos en tiempo real",
                "Caché implementado",
                "Pendiente más proveedores"
            ]
        }
    }
    
    with open('docs/FEATURES.md', 'w', encoding='utf-8') as f:
        f.write("# Características Implementadas\n\n")
        f.write(f"*Última actualización: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n")
        
        for feature, info in features.items():
            f.write(f"## {feature} {info['status']}\n\n")
            for detail in info['details']:
                f.write(f"- {detail}\n")
            f.write("\n")

def run_tests() -> bool:
    """Ejecuta los tests y retorna True si todos pasan."""
    result = run_command(['python', '-m', 'pytest'])
    return result.returncode == 0

def update_repository(commit_msg: str) -> bool:
    """Actualiza el repositorio con los cambios."""
    # Verificar si hay cambios
    status = run_command(['git', 'status', '--porcelain'])
    if not status.stdout.strip():
        print("No hay cambios para commitear")
        return True
        
    # Agregar cambios
    add_result = run_command(['git', 'add', '.'])
    if add_result.returncode != 0:
        print("Error al agregar cambios:", add_result.stderr)
        return False
        
    # Crear commit
    commit_result = run_command(['git', 'commit', '-m', commit_msg])
    if commit_result.returncode != 0:
        print("Error al crear commit:", commit_result.stderr)
        return False
        
    # Subir cambios
    push_result = run_command(['git', 'push'])
    if push_result.returncode != 0:
        print("Error al subir cambios:", push_result.stderr)
        return False
        
    return True

def main():
    """Función principal."""
    parser = argparse.ArgumentParser(description='Actualiza documentación y sube cambios')
    parser.add_argument('commit_message', help='Mensaje para el commit')
    parser.add_argument('--no-tests', action='store_true', help='No ejecutar tests')
    parser.add_argument('--no-push', action='store_true', help='No subir cambios')
    args = parser.parse_args()
    
    # Crear directorio docs si no existe
    os.makedirs('docs', exist_ok=True)
    
    # Actualizar documentación
    print("📝 Actualizando documentación...")
    update_features_doc()
    print("✅ Documentación actualizada")
    
    # Ejecutar tests
    if not args.no_tests:
        print("\n🧪 Ejecutando tests...")
        if not run_tests():
            print("❌ Algunos tests fallaron")
            sys.exit(1)
        print("✅ Tests completados")
    
    # Subir cambios
    if not args.no_push:
        print("\n📤 Subiendo cambios...")
        if not update_repository(args.commit_message):
            print("❌ Error al subir cambios")
            sys.exit(1)
        print("✅ Cambios subidos correctamente")
    
    print("\n🎉 ¡Todo listo!")

if __name__ == '__main__':
    main()
