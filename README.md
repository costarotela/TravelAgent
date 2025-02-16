# Travel Agent Assistant

Sistema inteligente para agentes de viajes que automatiza y optimiza el proceso de búsqueda, análisis y recomendación de paquetes turísticos.

## Características Principales

- 🔍 **Búsqueda Inteligente**: Búsqueda y análisis automatizado de paquetes turísticos
- 📊 **Análisis de Mercado**: Monitoreo de precios y detección de oportunidades
- 💡 **Recomendaciones Personalizadas**: Sugerencias basadas en preferencias y patrones
- 📈 **Visualizaciones**: Gráficos y reportes interactivos
- 💼 **Gestión de Presupuestos**: Generación y seguimiento de presupuestos
- 🔄 **Integración con Proveedores**: Conexión con múltiples proveedores de viajes

## Estructura del Proyecto

```
TravelAgent/
├── docs/
│   └── RELEVAMIENTO.md     # Documento de relevamiento
├── travel_agent/
│   ├── core/               # Componentes principales
│   │   ├── agent.py                 # Agente principal
│   │   ├── agent_observer.py        # Monitoreo y métricas
│   │   ├── agent_orchestrator.py    # Orquestación de flujos
│   │   ├── analysis_engine.py       # Motor de análisis
│   │   ├── browser_manager.py       # Gestión de navegación
│   │   ├── budget_engine.py         # Motor de presupuestos
│   │   ├── config.py                # Configuración
│   │   ├── opportunity_tracker.py   # Rastreo de oportunidades
│   │   ├── package_analyzer.py      # Análisis de paquetes
│   │   ├── price_monitor.py         # Monitoreo de precios
│   │   ├── provider_manager.py      # Gestión de proveedores
│   │   ├── recommendation_engine.py # Motor de recomendaciones
│   │   ├── schemas.py              # Modelos de datos
│   │   ├── session_manager.py      # Gestión de sesiones
│   │   ├── storage_manager.py      # Gestión de almacenamiento
│   │   └── visualization_engine.py  # Motor de visualización
│   ├── memory/             # Gestión de memoria y conocimiento
│   └── utils/             # Utilidades comunes
├── tests/                 # Tests unitarios y de integración
├── .env.example          # Variables de entorno de ejemplo
└── requirements.txt      # Dependencias del proyecto
```

## Componentes Core

### 1. Agente Principal (`agent.py`)
Coordina todos los componentes y gestiona el flujo principal de trabajo.

### 2. Observador (`agent_observer.py`)
- Monitoreo del estado del agente
- Registro de eventos y acciones
- Generación de métricas
- Detección de anomalías

### 3. Orquestador (`agent_orchestrator.py`)
- Gestión de flujos de trabajo
- Coordinación de eventos
- Supervisión de componentes

### 4. Motor de Análisis (`analysis_engine.py`)
- Análisis de datos de viajes
- Procesamiento de información de mercado
- Generación de insights
- Evaluación de tendencias

### 5. Gestor de Navegación (`browser_manager.py`)
- Gestión de sesiones web
- Extracción de datos
- Automatización de interacciones

### 6. Motor de Presupuestos (`budget_engine.py`)
- Generación de presupuestos
- Gestión de versiones
- Cálculo de costos
- Personalización de ofertas

### 7. Rastreador de Oportunidades (`opportunity_tracker.py`)
- Detección de oportunidades
- Análisis de mercado
- Alertas en tiempo real

### 8. Analizador de Paquetes (`package_analyzer.py`)
- Análisis de paquetes turísticos
- Comparación de precios
- Evaluación de características

### 9. Monitor de Precios (`price_monitor.py`)
- Monitoreo continuo de precios
- Detección de cambios
- Alertas de variaciones

### 10. Gestor de Proveedores (`provider_manager.py`)
- Gestión de proveedores
- Coordinación de búsquedas
- Procesamiento de reservas
- Gestión de credenciales

### 11. Motor de Recomendaciones (`recommendation_engine.py`)
- Generación de recomendaciones
- Aprendizaje de preferencias
- Personalización de sugerencias

### 12. Gestor de Sesiones (`session_manager.py`)
- Gestión de sesiones de venta
- Mantenimiento de estados
- Coordinación de flujos

### 13. Gestor de Almacenamiento (`storage_manager.py`)
- Gestión de persistencia
- Coordinación de backups
- Manejo de caché
- Optimización de acceso

### 14. Motor de Visualización (`visualization_engine.py`)
- Generación de visualizaciones
- Creación de reportes
- Exportación de datos
- Formateo de resultados

## Instalación

1. Clonar el repositorio:
```bash
git clone https://github.com/username/travel-agent.git
cd travel-agent
```

2. Crear entorno virtual:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o
.\venv\Scripts\activate  # Windows
```

3. Instalar dependencias:
```bash
pip install -r requirements.txt
```

4. Configurar variables de entorno:
```bash
cp .env.example .env
# Editar .env con las credenciales necesarias
```

## Uso

1. Iniciar el agente:
```python
from travel_agent.core.agent import TravelAgent

agent = TravelAgent()
await agent.start()
```

2. Realizar búsqueda:
```python
results = await agent.search_packages(criteria={
    "destination": "Cancún",
    "dates": ["2025-03-01", "2025-03-07"],
    "budget": 1500
})
```

3. Generar presupuesto:
```python
budget = await agent.create_budget(
    packages=results,
    metadata={"client_id": "123"}
)
```

## Desarrollo

1. Instalar dependencias de desarrollo:
```bash
pip install -r requirements-dev.txt
```

2. Ejecutar tests:
```bash
pytest
```

3. Verificar estilo de código:
```bash
flake8
black .
```

## Contribución

1. Fork del repositorio
2. Crear rama de feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit de cambios (`git commit -am 'Agregar nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Crear Pull Request

## Licencia

Este proyecto está bajo la Licencia MIT. Ver archivo `LICENSE` para más detalles.

## Contacto

- **Autor**: Tu Nombre
- **Email**: tu@email.com
- **GitHub**: [@username](https://github.com/username)
