# Smart Travel Agency 

Sistema inteligente para agentes de viajes que automatiza y optimiza el proceso de búsqueda, análisis y recomendación de paquetes turísticos.

## Características Principales

- **Búsqueda Inteligente**: Búsqueda y análisis automatizado de paquetes turísticos
- **Análisis de Mercado**: Monitoreo de precios y detección de oportunidades
- **Recomendaciones Personalizadas**: Sugerencias basadas en preferencias y patrones
- **Visualizaciones**: Gráficos y reportes interactivos
- **Gestión de Presupuestos**: Generación y seguimiento de presupuestos
- **Integración con Proveedores**: Conexión con múltiples proveedores de viajes
### Agente Premium
Nuestro sistema incluye un asistente AI avanzado que realiza:

1. **Observación y Reflexión** 
   - Análisis de mercado en tiempo real
   - Investigación web automática
   - Identificación de oportunidades

2. **Análisis Inteligente**
   - Comparación avanzada de precios
   - Análisis de tendencias
   - Evaluación de calidad/precio

3. **Planificación Estratégica**
   - Optimización de itinerarios
   - Recomendaciones personalizadas
   - Gestión inteligente de recursos

4. **Revisión y Control**
   - Verificación automática
   - Control de calidad
   - Monitoreo continuo

5. **Toma de Decisiones**
   - Recomendaciones basadas en datos
   - Optimización automática
   - Gestión de contingencias

## Interfaz de Usuario

La aplicación cuenta con una interfaz web construida con Streamlit que proporciona las siguientes funcionalidades:

1. **Dashboard**
   - Métricas clave
   - Gráficos interactivos
   - Actividad reciente

2. **Búsqueda de Paquetes**
   - Formulario de búsqueda avanzado
   - Filtros personalizables
   - Visualización de resultados
   - Detalles de paquetes

3. **Gestión de Presupuestos**
   - Lista de presupuestos activos
   - Creación de presupuestos
   - Plantillas predefinidas
   - Seguimiento de estados

4. **Reportes**
   - Generación de reportes
   - Múltiples formatos de exportación
   - Visualización de datos
   - Guardado y compartición

5. **Gestión de Proveedores**
   - Estado de proveedores
   - Monitoreo en tiempo real
   - Configuración de APIs
   - Métricas de rendimiento

6. **Configuración**
   - Ajustes generales
   - Notificaciones
   - Seguridad
   - Personalización

## Configuración del Entorno

### Requisitos Previos
- [Miniconda](https://docs.conda.io/en/latest/miniconda.html) o [Anaconda](https://www.anaconda.com/download)
- Git

### Instalación

1. Clonar el repositorio:
```bash
git clone https://github.com/costarotela/TravelAgent.git
cd TravelAgent
```

2. Crear y activar el entorno Conda:
```bash
conda env create -f environment.yml
conda activate travel-agent
```

3. Configurar variables de entorno:
```bash
cp .env.example .env
# Editar .env con las credenciales necesarias
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
│   ├── RELEVAMIENTO.md        # Documento de relevamiento inicial
│   ├── ESTADO_EVOLUCION.md    # Estado y plan de evolución
│   └── api/                   # Documentación de API
├── src/                       # Código fuente principal
│   ├── core/                  # Componentes principales
│   │   ├── agent/            # Agente principal y orquestación
│   │   ├── providers/        # Gestión de proveedores
│   │   ├── search/          # Motor de búsqueda
│   │   ├── analysis/        # Análisis y recomendaciones
│   │   └── budget/          # Gestión de presupuestos
│   ├── interfaces/          # Interfaces de usuario
│   ├── utils/              # Utilidades comunes
│   └── config/             # Configuración
├── tests/                  # Tests
├── scripts/               # Scripts de utilidad
├── .env.example          # Template de variables de entorno
├── environment.yml       # Configuración del entorno Conda
└── README.md            # Documentación principal
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

## Desarrollo

### Actualizar Dependencias

Para agregar nuevas dependencias:
1. Agregar el paquete a `environment.yml`
2. Actualizar el entorno:
```bash
conda env update -f environment.yml
```

### Ejecutar Tests
```bash
pytest
```

### Formatear Código
```bash
black src tests
isort src tests
```

## Uso

1. Iniciar el agente:
```python
from smart_travel_agency.core.agent import SmartTravelAgent

agent = SmartTravelAgent()
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
