# Travel Agent

Agente de viajes inteligente con capacidades avanzadas de búsqueda, recomendación y gestión de ventas.

## Estructura del Proyecto

```
TravelAgent/
├── agent_core/
│   ├── __init__.py
│   ├── schemas.py          # Modelos de datos con validación Pydantic
│   ├── config.py          # Sistema de configuración multi-ambiente
│   ├── interfaces.py      # Interfaces y protocolos base
│   └── managers/
│       ├── __init__.py
│       ├── cache_manager.py    # Gestión de caché multi-backend
│       ├── storage_manager.py  # Almacenamiento persistente
│       └── session_manager.py  # Gestión de sesiones de venta
├── data/                  # Datos persistentes
├── cache/                 # Archivos de caché
├── config/               # Archivos de configuración
│   ├── base.json
│   ├── development.json
│   ├── testing.json
│   └── production.json
├── docs/                 # Documentación
│   └── migration_map.md
├── requirements.txt      # Dependencias del proyecto
└── README.md            # Este archivo
```

## Características Principales

### Gestión de Datos
- Modelos de datos con validación Pydantic
- Enums para tipos y estados
- Serialización/deserialización automática
- Validadores personalizados

### Configuración
- Soporte para múltiples ambientes
- Carga desde variables de entorno
- Carga desde archivos JSON
- Validación de configuración
- Logging avanzado

### Caché
- Múltiples backends (Redis, Disco, Memoria)
- Políticas configurables
- Compresión automática
- Métricas y monitoreo
- Limpieza automática

### Almacenamiento
- Múltiples backends (MongoDB, SQLite, Archivos)
- Operaciones asíncronas
- Búsqueda y consultas
- Validación de datos
- Métricas y monitoreo

### Gestión de Sesiones
- Estado de sesión persistente
- Recuperación automática
- Limpieza de sesiones expiradas
- Métricas de conversión
- Reportes detallados

## Instalación

1. Clonar el repositorio:
```bash
git clone https://github.com/yourusername/TravelAgent.git
cd TravelAgent
```

2. Crear y activar entorno virtual:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

3. Instalar dependencias:
```bash
pip install -r requirements.txt
```

4. Configurar variables de entorno:
```bash
cp .env.example .env
# Editar .env con tus configuraciones
```

## Uso

1. Iniciar el agente:
```python
from agent_core.config import config
from agent_core.managers import cache_manager, storage_manager, session_manager

# La configuración se carga automáticamente
print(config.to_dict())

# Los managers son singletons
cache_manager.get_metrics()
storage_manager.get_metrics()
session_manager.get_metrics()
```

2. Crear una sesión de venta:
```python
from agent_core.schemas import SalesQuery, CustomerProfile, SearchCriteria

# Crear perfil de cliente
customer = CustomerProfile(
    id="customer123",
    name="John Doe",
    email="john@example.com"
)

# Crear consulta
query = SalesQuery(
    id="query123",
    customer=customer,
    criteria=SearchCriteria(
        destination="Paris",
        dates={
            "start": "2025-06-01",
            "end": "2025-06-07"
        }
    )
)

# Iniciar sesión
session = await session_manager.create_session(query, customer)
print(f"Session created: {session.session_id}")
```

## Desarrollo

1. Configurar ambiente de desarrollo:
```bash
cp config/development.json.example config/development.json
# Editar configuración según necesidades
```

2. Ejecutar tests:
```bash
pytest tests/
```

3. Verificar estilo de código:
```bash
flake8 agent_core/
black agent_core/
```

## Contribuir

1. Fork el repositorio
2. Crear rama para feature: `git checkout -b feature/nueva-caracteristica`
3. Commit cambios: `git commit -am 'Agregar nueva caracteristica'`
4. Push a la rama: `git push origin feature/nueva-caracteristica`
5. Crear Pull Request

## Licencia

Este proyecto está licenciado bajo MIT License - ver el archivo [LICENSE](LICENSE) para detalles.
