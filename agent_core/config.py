"""
Sistema de configuración del agente de viajes.
Soporta múltiples ambientes y configuración dinámica.
"""

import os
from typing import Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
import json
import logging
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

class Environment(str, Enum):
    """Ambientes soportados."""
    DEV = "development"
    TEST = "testing"
    PROD = "production"

@dataclass
class DatabaseConfig:
    """Configuración de base de datos."""
    host: str
    port: int
    name: str
    user: str
    password: str
    pool_size: int = 5
    max_overflow: int = 10
    timeout: int = 30

@dataclass
class CacheConfig:
    """Configuración de caché."""
    type: str
    host: str
    port: int
    db: int
    ttl: int = 3600
    max_size: int = 1000
    policy: str = "lru"

@dataclass
class APIConfig:
    """Configuración de API."""
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 4
    timeout: int = 60
    cors_origins: list = None
    rate_limit: Dict[str, int] = None

@dataclass
class LogConfig:
    """Configuración de logging."""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file: Optional[str] = None
    max_size: int = 10485760  # 10MB
    backup_count: int = 5

@dataclass
class SecurityConfig:
    """Configuración de seguridad."""
    secret_key: str
    token_expiration: int = 3600
    password_min_length: int = 8
    max_login_attempts: int = 3
    lockout_duration: int = 300

@dataclass
class AgentConfig:
    """Configuración del agente."""
    max_workers: int = 4
    task_timeout: int = 300
    retry_attempts: int = 3
    backoff_factor: float = 1.5
    cache_enabled: bool = True
    async_enabled: bool = True

class Config:
    """
    Gestor central de configuración.
    
    Características:
    1. Soporte para múltiples ambientes
    2. Carga desde variables de entorno
    3. Carga desde archivos
    4. Validación de configuración
    5. Valores por defecto seguros
    """
    
    def __init__(self):
        self.env = self._get_environment()
        self.base_path = Path(__file__).parent.parent
        
        # Cargar configuración base
        self._load_base_config()
        
        # Cargar configuración específica del ambiente
        self._load_environment_config()
        
        # Inicializar componentes
        self.db = self._init_database_config()
        self.cache = self._init_cache_config()
        self.api = self._init_api_config()
        self.log = self._init_log_config()
        self.security = self._init_security_config()
        self.agent = self._init_agent_config()
        
        # Validar configuración
        self._validate_config()
        
        # Configurar logging
        self._setup_logging()
    
    def _get_environment(self) -> Environment:
        """Determinar ambiente actual."""
        env = os.getenv("TRAVEL_AGENT_ENV", "development").lower()
        return Environment(env)
    
    def _load_base_config(self) -> None:
        """Cargar configuración base."""
        config_path = self.base_path / "config" / "base.json"
        if config_path.exists():
            with open(config_path) as f:
                self.base_config = json.load(f)
        else:
            self.base_config = {}
    
    def _load_environment_config(self) -> None:
        """Cargar configuración específica del ambiente."""
        config_path = self.base_path / "config" / f"{self.env.value}.json"
        if config_path.exists():
            with open(config_path) as f:
                self.env_config = json.load(f)
        else:
            self.env_config = {}
    
    def _init_database_config(self) -> DatabaseConfig:
        """Inicializar configuración de base de datos."""
        return DatabaseConfig(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "5432")),
            name=os.getenv("DB_NAME", "travel_agent"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", ""),
            pool_size=int(os.getenv("DB_POOL_SIZE", "5")),
            max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "10")),
            timeout=int(os.getenv("DB_TIMEOUT", "30"))
        )
    
    def _init_cache_config(self) -> CacheConfig:
        """Inicializar configuración de caché."""
        return CacheConfig(
            type=os.getenv("CACHE_TYPE", "redis"),
            host=os.getenv("CACHE_HOST", "localhost"),
            port=int(os.getenv("CACHE_PORT", "6379")),
            db=int(os.getenv("CACHE_DB", "0")),
            ttl=int(os.getenv("CACHE_TTL", "3600")),
            max_size=int(os.getenv("CACHE_MAX_SIZE", "1000")),
            policy=os.getenv("CACHE_POLICY", "lru")
        )
    
    def _init_api_config(self) -> APIConfig:
        """Inicializar configuración de API."""
        return APIConfig(
            host=os.getenv("API_HOST", "0.0.0.0"),
            port=int(os.getenv("API_PORT", "8000")),
            workers=int(os.getenv("API_WORKERS", "4")),
            timeout=int(os.getenv("API_TIMEOUT", "60")),
            cors_origins=os.getenv("API_CORS_ORIGINS", "").split(","),
            rate_limit={
                "requests": int(os.getenv("API_RATE_LIMIT_REQUESTS", "100")),
                "period": int(os.getenv("API_RATE_LIMIT_PERIOD", "60"))
            }
        )
    
    def _init_log_config(self) -> LogConfig:
        """Inicializar configuración de logging."""
        return LogConfig(
            level=os.getenv("LOG_LEVEL", "INFO"),
            format=os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"),
            file=os.getenv("LOG_FILE"),
            max_size=int(os.getenv("LOG_MAX_SIZE", "10485760")),
            backup_count=int(os.getenv("LOG_BACKUP_COUNT", "5"))
        )
    
    def _init_security_config(self) -> SecurityConfig:
        """Inicializar configuración de seguridad."""
        return SecurityConfig(
            secret_key=os.getenv("SECRET_KEY", "your-secret-key"),
            token_expiration=int(os.getenv("TOKEN_EXPIRATION", "3600")),
            password_min_length=int(os.getenv("PASSWORD_MIN_LENGTH", "8")),
            max_login_attempts=int(os.getenv("MAX_LOGIN_ATTEMPTS", "3")),
            lockout_duration=int(os.getenv("LOCKOUT_DURATION", "300"))
        )
    
    def _init_agent_config(self) -> AgentConfig:
        """Inicializar configuración del agente."""
        return AgentConfig(
            max_workers=int(os.getenv("AGENT_MAX_WORKERS", "4")),
            task_timeout=int(os.getenv("AGENT_TASK_TIMEOUT", "300")),
            retry_attempts=int(os.getenv("AGENT_RETRY_ATTEMPTS", "3")),
            backoff_factor=float(os.getenv("AGENT_BACKOFF_FACTOR", "1.5")),
            cache_enabled=os.getenv("AGENT_CACHE_ENABLED", "true").lower() == "true",
            async_enabled=os.getenv("AGENT_ASYNC_ENABLED", "true").lower() == "true"
        )
    
    def _validate_config(self) -> None:
        """Validar configuración completa."""
        # Validar base de datos
        if not self.db.password and self.env == Environment.PROD:
            raise ValueError("DB_PASSWORD es requerido en producción")
        
        # Validar seguridad
        if self.env == Environment.PROD:
            if len(self.security.secret_key) < 32:
                raise ValueError("SECRET_KEY debe tener al menos 32 caracteres en producción")
            if "your-secret-key" in self.security.secret_key:
                raise ValueError("Debe cambiar el SECRET_KEY por defecto en producción")
    
    def _setup_logging(self) -> None:
        """Configurar sistema de logging."""
        logging.basicConfig(
            level=getattr(logging, self.log.level.upper()),
            format=self.log.format
        )
        
        if self.log.file:
            handler = logging.handlers.RotatingFileHandler(
                self.log.file,
                maxBytes=self.log.max_size,
                backupCount=self.log.backup_count
            )
            handler.setFormatter(logging.Formatter(self.log.format))
            logging.getLogger().addHandler(handler)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Obtener valor de configuración."""
        # Buscar en variables de entorno
        env_key = f"TRAVEL_AGENT_{key.upper()}"
        if env_key in os.environ:
            return os.environ[env_key]
        
        # Buscar en configuración de ambiente
        if key in self.env_config:
            return self.env_config[key]
        
        # Buscar en configuración base
        if key in self.base_config:
            return self.base_config[key]
        
        return default
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir configuración a diccionario."""
        return {
            "environment": self.env.value,
            "database": self.db.__dict__,
            "cache": self.cache.__dict__,
            "api": self.api.__dict__,
            "log": self.log.__dict__,
            "security": {
                k: v for k, v in self.security.__dict__.items()
                if k != "secret_key"
            },
            "agent": self.agent.__dict__
        }

# Instancia global de configuración
config = Config()
