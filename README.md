# Travel Agent Assistant

Sistema inteligente de asistencia para vendedores de agencias de viajes.

## Descripción

El Travel Agent Assistant es un sistema diseñado para ayudar a los vendedores de agencias de viajes en el proceso de búsqueda, análisis y generación de presupuestos personalizados para sus clientes.

## Características Principales

- **Búsqueda Inteligente**: Integración con proveedores principales (OLA, AERO, Despegar)
- **Análisis de Paquetes**: Comparación y análisis automático de opciones
- **Presupuestos Personalizados**: Sistema de generación y versionado de presupuestos
- **Base de Conocimiento**: Aprendizaje continuo basado en operaciones anteriores
- **Supervisión del Vendedor**: Control total sobre las operaciones
- **Reservas Automatizadas**: Gestión de reservas con proveedores

## Estructura del Proyecto

```
travel_agent/
├── core/               # Componentes principales
├── providers/          # Integración con proveedores
├── memory/            # Sistema de memoria y base de conocimiento
├── budget/            # Generación y gestión de presupuestos
├── knowledge/         # Base de conocimiento y aprendizaje
├── interface/         # Interfaces de usuario y API
└── tools/             # Herramientas auxiliares
```

## Componentes Core

1. **Browser Manager**: Gestión de interacciones web
2. **Price Monitor**: Monitoreo de precios
3. **Package Analyzer**: Análisis de paquetes turísticos
4. **Opportunity Tracker**: Seguimiento de oportunidades
5. **Recommendation Engine**: Motor de recomendaciones
6. **Session Manager**: Administración de sesiones

## Instalación

1. Clonar el repositorio
2. Instalar dependencias: `pip install -r requirements.txt`
3. Configurar variables de entorno en `.env`
4. Ejecutar `scripts/setup.sh`

## Uso

1. El vendedor inicia sesión en el sistema
2. Ingresa los requisitos del cliente
3. El sistema busca y analiza opciones
4. Se generan presupuestos personalizados
5. El vendedor revisa y aprueba
6. Se realizan reservas si es necesario

## Tecnologías Principales

- **Browser-use**: Automatización web robusta
- **Supabase**: Base de conocimiento y almacenamiento
- **LangChain**: Procesamiento de lenguaje natural
- **FastAPI**: API REST
- **React**: Interfaz web

## Configuración

Ver `.env.example` para las variables de entorno necesarias:
- Credenciales de proveedores
- Configuración de Supabase
- Configuración de base de datos externa
- Claves de API

## Desarrollo

1. Crear rama: `git checkout -b feature/nueva-caracteristica`
2. Commit cambios: `git commit -m "feat: descripción"`
3. Push: `git push origin feature/nueva-caracteristica`

## Testing

```bash
pytest tests/
```

## Contribución

1. Fork del repositorio
2. Crear rama de característica
3. Commit cambios
4. Push a la rama
5. Crear Pull Request

## Licencia

Propietario - Todos los derechos reservados
