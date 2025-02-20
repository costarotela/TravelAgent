#!/usr/bin/env python3
"""Verifica que los archivos sigan los principios del proyecto."""

import sys
from pathlib import Path

PRINCIPLES = [
    "Elaboración de presupuestos",
    "Adaptación a cambios",
    "Datos en tiempo real",
    "Interfaz interactiva",
    "Reconstrucción"
]

def check_file(file_path: Path) -> bool:
    """Verifica que el archivo contenga los principios."""
    content = file_path.read_text().lower()
    missing = [p for p in PRINCIPLES if p.lower() not in content]
    
    if missing:
        print(f"\n⚠️ {file_path}: Principios faltantes:")
        for principle in missing:
            print(f"  - {principle}")
        return False
    return True

def main():
    """Función principal."""
    files = sys.argv[1:] if len(sys.argv) > 1 else []
    if not files:
        return 0
        
    failed = False
    for file in files:
        if not check_file(Path(file)):
            failed = True
            
    return 1 if failed else 0

if __name__ == '__main__':
    sys.exit(main())
