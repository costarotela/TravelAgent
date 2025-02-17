# Smart Travel Agency 

Sistema simplificado para agentes de viajes que facilita la búsqueda y generación de presupuestos de viajes.

## Características Principales

- **Búsqueda Simple**: Búsqueda rápida de vuelos y paquetes
- **Presupuestos Básicos**: Generación simple de presupuestos
- **Interfaz Intuitiva**: UI simple y fácil de usar
- **Almacenamiento Local**: Base de datos SQLite para persistencia
- **Proveedor Aero**: Integración con proveedor principal de vuelos

## Documentación

La documentación del proyecto se encuentra en el directorio `docs/`:

- `PLAN_SIMPLIFICACION.md`: Plan detallado de simplificación del sistema
- `ESTADO_EVOLUCION.md`: Estado actual del proyecto y próximos pasos
- `PLAN_MEJORAS.md`: Plan de mejoras incrementales

## Interfaz de Usuario

La aplicación cuenta con una interfaz web simple construida con Streamlit que proporciona:

1. **Búsqueda de Vuelos**
   - Formulario simple de búsqueda
   - Filtros básicos
   - Visualización de resultados en tabla

2. **Gestión de Presupuestos**
   - Creación de presupuestos
   - Lista de presupuestos activos
   - Exportación simple

## Configuración del Entorno

### Requisitos Previos
- Python 3.8+
- pip

### Instalación

1. Clonar el repositorio:
```bash
git clone https://github.com/costarotela/TravelAgent.git
cd TravelAgent
```

2. Instalar dependencias:
```bash
pip install -r requirements.txt
```

## Ejecución

1. Ejecutar la aplicación:
```bash
python run.py
```

2. Abrir en el navegador:
```
http://localhost:8501
```

## Estructura del Proyecto

```
TravelAgent/
├── docs/
│   ├── PLAN_SIMPLIFICACION.md  # Plan de simplificación
│   ├── ESTADO_EVOLUCION.md     # Estado actual
│   └── PLAN_MEJORAS.md         # Plan de mejoras
├── src/
│   ├── core/
│   │   ├── providers/         # Proveedores de viajes
│   │   └── budget/           # Gestión de presupuestos
│   ├── ui/                   # Interfaces de usuario
│   └── utils/               # Utilidades
├── data/                   # Base de datos SQLite
└── requirements.txt       # Dependencias del proyecto
```

## Componentes Principales

### 1. Búsqueda (`search.py`)
- Formulario de búsqueda simple
- Filtros básicos
- Visualización de resultados

### 2. Presupuestos (`budget/`)
- Generación de presupuestos
- Almacenamiento en SQLite
- Exportación básica

### 3. Proveedor Aero (`providers/aero.py`)
- Búsqueda de vuelos
- Caché en memoria
- Manejo de errores básico

## Contribución

1. Hacer fork del repositorio
2. Crear rama para nueva funcionalidad
3. Hacer commit de los cambios
4. Crear pull request

## Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo `LICENSE` para más detalles.
