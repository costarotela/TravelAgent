# Smart Travel Agency - Sistema de Gestión B2B

## Objetivo Principal
Facilitar la elaboración y gestión de presupuestos de viaje, priorizando la estabilidad durante la interacción vendedor-cliente y garantizando el control total del vendedor sobre el proceso.

## Principios Fundamentales

### 1. Estabilidad Durante la Sesión
- Los datos permanecen estables durante toda la sesión de venta
- Las actualizaciones no interrumpen sesiones activas
- Las modificaciones son controladas exclusivamente por el vendedor

### 2. Control del Vendedor
- Control total sobre el proceso de venta
- Decisiones explícitas sobre modificaciones
- Gestión completa de la interacción con el cliente

### 3. Procesamiento Asíncrono
- Las validaciones y actualizaciones se procesan fuera de la sesión de venta
- Los cambios se notifican para futuras interacciones
- La consistencia de datos se mantiene durante toda la sesión

## Componentes Principales

### 1. Gestión de Sesiones de Venta (✅ IMPRESCINDIBLE)
- Control de estado durante la interacción con cliente
- Aislamiento de datos por sesión
- Modificaciones controladas por vendedor

### 2. Sistema de Presupuestos (✅ IMPRESCINDIBLE)
- Elaboración dinámica con asistencia del vendedor
- Construcción basada en datos de proveedores
- Capacidad de reconstrucción y modificación

### 3. Actualización de Datos (⚠️ PARCIALMENTE NECESARIO)
- Detección asíncrona de cambios
- Notificaciones para futuras sesiones
- Procesamiento fuera de sesiones activas

### 4. Interfaz de Vendedor (✅ IMPRESCINDIBLE)
- Editor de presupuestos intuitivo
- Visualización clara de datos
- Control total sobre modificaciones

### 5. Módulo de Web Scraping (⚠️ PARCIALMENTE NECESARIO)
- Recolección inicial de datos
- Actualizaciones asíncronas
- Sistema anti-bloqueo

## Métricas de Éxito

### 1. Experiencia del Vendedor
- Tiempo de creación de sesión < 2 segundos
- Tiempo de respuesta en modificaciones < 1 segundo
- Zero interrupciones durante sesión activa

### 2. Calidad de Datos
- 100% consistencia durante la sesión
- Validación completa al cierre
- Notificaciones efectivas de cambios

### 3. Rendimiento del Sistema
- Disponibilidad del sistema > 99.9%
- Tiempo de reconstrucción < 5 segundos
- Procesamiento asíncrono eficiente

## Documentación Relacionada

- [Arquitectura](docs/ARQUITECTURA.md)
- [Integración OLA](docs/OLA_INTEGRATION.md)
- [Interfaz de Vendedor](docs/VENDOR_INTERFACE.md)
- [Motor de Presupuestos](docs/BUDGET_ENGINE.md)

## Requisitos Técnicos

### Dependencias Principales
- Python 3.8+
- Prophet: Análisis de series temporales
- Pandas & NumPy: Manipulación de datos
- Streamlit: Interfaz de usuario
- SQLAlchemy: Gestión de base de datos
- Selenium WebDriver
- Chrome/Chromium
- Redis (para caché)
- Sistema de proxies

### Instalación
```bash
pip install -r requirements.txt
```

### Configuración
1. Copiar `.env.example` a `.env`
2. Configurar variables de entorno
3. Inicializar base de datos: `python scripts/init_db.py`
4. Configurar credenciales en `.env`:
```env
PROXY_LIST_PATH=./config/proxies.txt
USER_AGENTS_PATH=./config/user_agents.txt
REDIS_URL=redis://localhost:6379
```

## Uso

### Iniciar Sistema
```bash
python -m src.main
```

### Acceder a la Interfaz
Abrir navegador en `http://localhost:8501`

### Monitorear Actividad
```bash
python -m smart_travel_agent --monitor
```

## Documentación Adicional
- [Guía de Usuario](docs/user_guide.md)
- [Manual de Administrador](docs/admin_guide.md)
- [API Reference](docs/api_reference.md)

## Contribuir
1. Fork del repositorio
2. Crear rama para feature: `git checkout -b feature/nueva-funcionalidad`
3. Commit cambios: `git commit -am 'Agregar nueva funcionalidad'`
4. Push a la rama: `git push origin feature/nueva-funcionalidad`
5. Crear Pull Request

## Licencia

Este proyecto está licenciado bajo la Licencia MIT - ver el archivo [LICENSE.md](LICENSE.md) para detalles.

## Advertencia Legal

Este software debe ser utilizado de acuerdo con los términos y condiciones de los sitios web objetivo y las leyes aplicables. El uso de técnicas de scraping debe respetar las políticas de uso de cada sitio.
