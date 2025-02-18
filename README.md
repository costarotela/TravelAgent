# Smart Travel Agency - Sistema de Gestión B2B

## Descripción
Sistema de gestión para agencias de viajes enfocado en B2B (Business to Business). Proporciona herramientas para la gestión eficiente de presupuestos, análisis de precios y gestión de proveedores.

## Componentes Principales

### 1. Motor de Reglas de Negocio
- Evaluación y aplicación de reglas comerciales
- Gestión de márgenes y descuentos
- Validaciones automáticas

### 2. Sistema de Actualización de Presupuestos
- Detección de cambios en precios y disponibilidad
- Recálculo automático de presupuestos
- Historial de cambios

### 3. Sistema de Análisis de Precios y Proveedores
- Análisis de tendencias de precios
- Predicción de variaciones
- Evaluación de rendimiento de proveedores
- Métricas de calidad y confiabilidad
- Recomendaciones para gestión de proveedores

### 4. Interfaz de Vendedor
- Dashboard de actualizaciones en tiempo real
- Editor de presupuestos
- Visualización de análisis y métricas

## Usuarios Principales

### Vendedores/Agentes
- Gestión de presupuestos
- Seguimiento de cambios de precios
- Aplicación de reglas de negocio

### Administradores
- Configuración de reglas comerciales
- Gestión de proveedores
- Monitoreo de rendimiento
- Análisis de métricas

## Requisitos Técnicos

### Dependencias Principales
- Python 3.8+
- Prophet: Análisis de series temporales
- Pandas & NumPy: Manipulación de datos
- Streamlit: Interfaz de usuario
- SQLAlchemy: Gestión de base de datos

### Instalación
```bash
pip install -r requirements.txt
```

### Configuración
1. Copiar `.env.example` a `.env`
2. Configurar variables de entorno
3. Inicializar base de datos: `python scripts/init_db.py`

## Uso

### Iniciar Sistema
```bash
python -m src.main
```

### Acceder a la Interfaz
Abrir navegador en `http://localhost:8501`

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
