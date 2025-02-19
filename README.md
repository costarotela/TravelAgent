# Smart Travel Agency

Sistema inteligente de asistencia para la elaboración de presupuestos de viajes que combina:
- Extracción y análisis automatizado de datos de proveedores
- Optimización multi-pasada de presupuestos
- Control total del vendedor sobre el proceso
- Estabilidad garantizada durante sesiones de venta

El sistema actúa como un asistente digital que trabaja "tras bambalinas" realizando múltiples pasadas de búsqueda, análisis y optimización, mientras mantiene la interfaz estable para la interacción vendedor-cliente.

## Principios Fundamentales

1. **Estabilidad en Sesión Activa**
   - Los datos capturados al inicio de la sesión permanecen estables
   - Modificaciones controladas solo por el vendedor
   - Sin interrupciones por actualizaciones externas

2. **Gestión de Actualizaciones**
   - Procesamiento después de finalizada la sesión
   - No interfieren con sesiones activas
   - Notificación para futuras interacciones

## Configuración del Entorno

1. Crear y activar entorno conda:
```bash
conda env create -f environment.yml
conda activate travel-agent
```

2. Variables de entorno:
```bash
cp .env.example .env
# Editar .env con las configuraciones necesarias
```

## Estructura del Proyecto

```
SmartTravelAgency/
├── src/                    # Código fuente principal
│   ├── api/               # API REST endpoints
│   ├── auth/              # Autenticación
│   ├── core/              # Lógica de negocio
│   ├── dashboard/         # Interfaz de gestión
│   └── utils/             # Utilidades
├── agent_core/            # Núcleo del agente
│   ├── managers/          # Gestores de servicios
│   ├── schemas/           # Modelos de datos
│   └── scrapers/          # Integración proveedores
└── tests/                 # Tests
```

## Uso de la API

### 1. Autenticación

```bash
# Obtener token
curl -X POST "http://localhost:8000/api/v1/token" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "username=test&password=test"
```

### 2. Gestión de Sesiones

```bash
# Crear sesión
curl -X POST "http://localhost:8000/api/v1/sessions/create" \
     -H "Authorization: Bearer <token>" \
     -H "Content-Type: application/json" \
     -d '{
       "vendor_id": "V1",
       "customer_id": "C1"
     }'

# Agregar paquete
curl -X POST "http://localhost:8000/api/v1/sessions/<session_id>/packages" \
     -H "Authorization: Bearer <token>" \
     -H "Content-Type: application/json" \
     -d '{
       "provider": "OLA",
       "package_id": "PKG123",
       "details": {...}
     }'
```

## Desarrollo

### Tests
```bash
pytest tests/
```

### Linting
```bash
flake8 src/ agent_core/
```

### Documentación
```bash
# Generar documentación
cd docs && make html
```

## Monitoreo

### Endpoints de Estado
- `/health`: Estado básico del sistema
- `/status`: Métricas y estado detallado

### Logs
- Ubicación: `logs/travel_agent.log`
- Rotación automática
- Niveles configurables en .env

## Seguridad

1. **Autenticación**
   - OAuth2 con JWT
   - Tokens con expiración
   - Contraseñas hasheadas (bcrypt)

2. **Autorización**
   - Todas las rutas protegidas
   - Control de acceso por roles
   - Validación en cada capa

## Próximas Mejoras

- [ ] Sistema de usuarios en base de datos
- [ ] Roles y permisos granulares
- [ ] Rate limiting
- [ ] Logging de seguridad mejorado
- [ ] Nuevos proveedores de viajes
- [ ] Mejoras en UI del dashboard

## Contribución

1. Fork del repositorio
2. Crear rama feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit cambios (`git commit -am 'Agregar nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Crear Pull Request

## Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo `LICENSE` para más detalles.
