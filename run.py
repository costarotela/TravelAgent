"""Script principal para ejecutar la aplicación."""
import os
import sys
from pathlib import Path
import streamlit as st

# Configuración global de la página - DEBE SER EL PRIMER COMANDO DE STREAMLIT
st.set_page_config(
    page_title="Agencia de Viajes",
    page_icon="✈️",
    layout="wide"
)

# Agregar el directorio raíz al PYTHONPATH
root_dir = Path(__file__).parent.absolute()
sys.path.append(str(root_dir))

# Importar y ejecutar la aplicación
from src.ui.app import main

if __name__ == "__main__":
    main()
