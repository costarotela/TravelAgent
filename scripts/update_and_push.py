#!/usr/bin/env python3
"""Script para actualizar documentación y subir cambios al repositorio.

Este script:
1. Actualiza la documentación con las características implementadas
2. Ejecuta pre-commit (formato, tests, principios)
3. Sube los cambios al repositorio remoto

Uso:
    python scripts/update_and_push.py [--no-checks] [--no-push] "Mensaje del commit"
"""

import argparse
import os
import subprocess
from datetime import datetime
from typing import List


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
                "Tests completos",
            ],
        },
        "Comparación de Paquetes": {
            "status": "🚧 En Desarrollo",
            "details": [
                "Comparación de características",
                "Análisis de precios",
                "Tests en progreso",
            ],
        },
        "Interfaz de Usuario": {
            "status": "📝 Pendiente",
            "details": [
                "Diseño de UI interactiva",
                "Integración con backend",
                "Experiencia del vendedor",
            ],
        },
        "Integración con Proveedores": {
            "status": "🚧 En Desarrollo",
            "details": [
                "Extracción de datos en tiempo real",
                "Caché implementado",
                "Pendiente más proveedores",
            ],
        },
    }

    os.makedirs("docs", exist_ok=True)
    with open("docs/FEATURES.md", "w", encoding="utf-8") as f:
        f.write("# Características Implementadas\n\n")
        f.write(
            f"*Última actualización: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n"
        )

        for feature, info in features.items():
            f.write(f"## {feature} {info['status']}\n\n")
            for detail in info["details"]:
                f.write(f"- {detail}\n")
            f.write("\n")


def run_checks() -> bool:
    """Ejecuta pre-commit para verificar formato, tests y principios."""
    print("\n🔍 Ejecutando verificaciones...")
    result = run_command(["pre-commit", "run", "--all-files"])
    if result.returncode != 0:
        print("❌ Algunas verificaciones fallaron:")
        print(result.stdout)
        return False
    print("✅ Verificaciones completadas")
    return True


def update_repository(commit_msg: str) -> bool:
    """Actualiza el repositorio con los cambios."""
    print("\n📤 Verificando cambios...")

    # Verificar si hay cambios
    status = run_command(["git", "status", "--porcelain"])
    if not status.stdout.strip():
        print("ℹ️ No hay cambios para commitear")
        return True

    # Agregar y commitear cambios
    add_result = run_command(["git", "add", "."])
    if add_result.returncode != 0:
        print("❌ Error al agregar cambios:", add_result.stderr)
        return False

    commit_result = run_command(["git", "commit", "-m", commit_msg])
    if commit_result.returncode != 0:
        print("❌ Error al crear commit:", commit_result.stderr)
        return False

    # Subir cambios
    push_result = run_command(["git", "push"])
    if push_result.returncode != 0:
        print("❌ Error al subir cambios:", push_result.stderr)
        return False

    print("✅ Cambios subidos correctamente")
    return True


def main():
    """Función principal."""
    parser = argparse.ArgumentParser(
        description="Actualiza documentación y sube cambios"
    )
    parser.add_argument("commit_message", help="Mensaje para el commit")
    parser.add_argument(
        "--no-checks", action="store_true", help="No ejecutar verificaciones"
    )
    parser.add_argument("--no-push", action="store_true", help="No subir cambios")
    args = parser.parse_args()

    # Actualizar documentación
    print("📝 Actualizando documentación...")
    update_features_doc()
    print("✅ Documentación actualizada")

    # Ejecutar verificaciones
    if not args.no_checks and not run_checks():
        return 1

    # Subir cambios
    if not args.no_push and not update_repository(args.commit_message):
        return 1

    print("\n🎉 ¡Todo listo!")
    return 0


if __name__ == "__main__":
    exit(main())
