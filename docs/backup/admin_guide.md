# Manual del Administrador - Smart Travel Agency

## Configuración del Sistema

### Requisitos del Sistema
- Linux/Unix
- Python 3.8+
- PostgreSQL 12+
- 4GB RAM mínimo
- 2 CPU cores mínimo

### Instalación

#### 1. Preparación
```bash
# Crear directorio
mkdir -p /opt/smarttravel
cd /opt/smarttravel

# Clonar repositorio
git clone https://github.com/costarotela/TravelAgent.git
cd TravelAgent

# Crear entorno virtual
python -m venv venv
source venv/bin/activate
```

#### 2. Dependencias
```bash
# Instalar dependencias
pip install -r requirements.txt

# Verificar instalación
python -m pytest
```

#### 3. Base de Datos
```bash
# Crear base de datos
createdb smarttravel

# Ejecutar migraciones
alembic upgrade head
```

### Configuración

#### Variables de Entorno
Crear archivo `.env`:
```ini
# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=smarttravel
DB_USER=admin
DB_PASS=secure_password

# Monitoring
PROMETHEUS_PORT=9090
LOG_LEVEL=INFO

# Application
APP_PORT=8501
APP_ENV=production
```

## Administración

### Gestión de Usuarios

#### Crear Usuario
```sql
INSERT INTO users (username, role, email)
VALUES ('vendedor1', 'seller', 'vendedor1@smarttravel.com');
```

#### Modificar Permisos
```sql
UPDATE users
SET role = 'admin'
WHERE username = 'vendedor1';
```

### Reglas de Negocio

#### Configurar Reglas
1. Acceder a "Configuración > Reglas"
2. Definir:
   - Márgenes por tipo de servicio
   - Descuentos permitidos
   - Validaciones requeridas

#### Actualizar Reglas
1. Seleccionar regla
2. Modificar parámetros
3. Guardar cambios
4. Verificar aplicación

### Monitoreo

#### Métricas Principales
- Uso de CPU/Memoria
- Tiempo de respuesta
- Errores por minuto
- Usuarios activos

#### Alertas
Configurar en `config/alerts.yml`:
```yaml
alerts:
  high_cpu:
    threshold: 80
    duration: 5m
    action: email

  error_rate:
    threshold: 10
    duration: 1m
    action: slack
```

## Mantenimiento

### Backups

#### Base de Datos
```bash
# Backup diario
pg_dump smarttravel > /backups/smarttravel_$(date +%Y%m%d).sql

# Restaurar
psql smarttravel < backup.sql
```

#### Logs
```bash
# Rotación de logs
logrotate /etc/logrotate.d/smarttravel
```

### Actualización

#### Sistema
```bash
# Actualizar código
git pull origin main

# Actualizar dependencias
pip install -r requirements.txt

# Migraciones
alembic upgrade head

# Reiniciar servicios
systemctl restart smarttravel
```

## Seguridad

### Mejores Prácticas
1. Actualizar contraseñas regularmente
2. Monitorear accesos inusuales
3. Mantener sistema actualizado
4. Revisar logs de seguridad

### Firewall
```bash
# Permitir puertos necesarios
ufw allow 8501/tcp  # UI
ufw allow 9090/tcp  # Prometheus
```

## Troubleshooting

### Problemas Comunes

#### Error de Conexión DB
1. Verificar servicio PostgreSQL
2. Revisar credenciales
3. Comprobar firewall

#### Rendimiento Lento
1. Revisar uso de recursos
2. Analizar queries lentas
3. Optimizar índices

### Logs
```bash
# Aplicación
tail -f /var/log/smarttravel/app.log

# Error
tail -f /var/log/smarttravel/error.log
```

## Contacto Soporte Técnico
- Email: tech@smarttravel.com
- Urgencias: +54 (011) 4444-5555
- Horario: 24/7
