"""
Configuración del sistema.
"""

from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configuración del sistema."""
    
    # Credenciales de proveedores
    OLA_USERNAME: str
    OLA_PASSWORD: str
    AERO_USERNAME: str
    AERO_PASSWORD: str
    DESPEGAR_USERNAME: str
    DESPEGAR_PASSWORD: str
    
    # Configuración de Supabase
    SUPABASE_URL: str
    SUPABASE_KEY: str
    
    # Base de datos externa
    DB_HOST: str
    DB_PORT: int
    DB_NAME: str
    DB_USER: str
    DB_PASSWORD: str
    
    # OpenAI para análisis
    OPENAI_API_KEY: str
    
    # Configuración de browser-use
    BROWSER_HEADLESS: bool = True
    BROWSER_TIMEOUT: int = 30
    
    # Configuración de caché
    CACHE_DIR: str = "./cache"
    CACHE_EXPIRY: int = 3600  # 1 hora
    
    # Configuración de logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: Optional[str] = None
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Instancia global de configuración
config = Settings()
