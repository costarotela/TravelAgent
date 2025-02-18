# Costa Rotela Travel Agency

Sistema de gestión de presupuestos y búsqueda de vuelos para TudoBem Travel Agency.

## Características

### 1. Gestión de Presupuestos
- Creación automática de presupuestos de paquetes de viaje con asistencia de vendedor
- Almacenamiento persistente en SQLite
- Exportación a PDF
- Filtrado y búsqueda avanzada
- Vista detallada de presupuestos

### 2. Búsqueda de Vuelos
- Integración con API Aero
- Filtros personalizables
- Sistema de caché para mejor rendimiento
- Comparación de opciones
- Creación directa de presupuestos

### 3. Interfaz de Usuario
- Dashboard con estadísticas
- Búsqueda rápida de vuelos
- Actividad reciente
- Navegación intuitiva
- Manejo global de errores
- Diseño responsivo

## Instalación

1. Clonar el repositorio:
```bash
git clone https://github.com/costarotela/TravelAgent.git
cd TravelAgent
```

2. Crear entorno virtual:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
```

3. Instalar dependencias:
```bash
pip install -r requirements.txt
```

4. Configurar variables de entorno:
```bash
cp .env.example .env
# Editar .env con tus credenciales
```

## Uso

1. Iniciar la aplicación:
```bash
streamlit run src/ui/main.py
```

2. Acceder a través del navegador:
```
http://localhost:8501
```

## Desarrollo

### Estructura del Proyecto
```
TravelAgent/
├── docs/                  # Documentación
├── src/                   # Código fuente
│   ├── core/             # Lógica de negocio
│   │   ├── budget/       # Gestión de presupuestos
│   │   └── providers/    # Proveedores de vuelos
│   ├── ui/               # Interfaz de usuario
│   │   └── pages/        # Páginas de la aplicación
│   └── utils/            # Utilidades
├── tests/                # Tests
└── requirements.txt      # Dependencias
```

### Ejecutar Tests
```bash
python -m unittest discover tests
```

## Contribuir

1. Fork el repositorio
2. Crear rama para feature: `git checkout -b feature/nueva-funcionalidad`
3. Commit cambios: `git commit -m 'Agregar nueva funcionalidad'`
4. Push a la rama: `git push origin feature/nueva-funcionalidad`
5. Crear Pull Request

## Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo `LICENSE` para más detalles.

## Contacto

- **Email**: support@costarotela.com
- **Web**: https://costarotela.com
- **Tel**: +54 (011) 4444-5555
