"""
Manejo seguro de credenciales para proveedores.
"""
from cryptography.fernet import Fernet
import base64
import json
import os
from pathlib import Path
from typing import Dict, Optional

class CredentialManager:
    """Gestor seguro de credenciales."""
    
    def __init__(self, encryption_key: Optional[str] = None):
        """
        Inicializa el gestor de credenciales.
        
        Args:
            encryption_key: Clave de encriptación (opcional)
        """
        self._key = encryption_key or os.getenv('TRAVEL_AGENT_ENCRYPTION_KEY')
        if not self._key:
            self._key = Fernet.generate_key().decode()
            
        self._fernet = Fernet(self._ensure_valid_key(self._key))
        self._credentials: Dict[str, dict] = {}
        
    def _ensure_valid_key(self, key: str) -> bytes:
        """Asegura que la clave tenga el formato correcto."""
        try:
            # Si es base64 válido, úsalo directamente
            return key.encode() if isinstance(key, str) else key
        except:
            # Si no, conviértelo a base64
            return base64.urlsafe_b64encode(key.encode().ljust(32)[:32])
    
    def load_credentials(self, path: str) -> None:
        """
        Carga credenciales desde archivo.
        
        Args:
            path: Ruta al archivo de credenciales
        """
        if not os.path.exists(path):
            return
            
        try:
            with open(path, 'rb') as f:
                encrypted_data = f.read()
                if encrypted_data:
                    decrypted_data = self._fernet.decrypt(encrypted_data)
                    self._credentials = json.loads(decrypted_data)
                else:
                    self._credentials = {}
        except Exception as e:
            raise ValueError(f"Error cargando credenciales: {str(e)}")
    
    def save_credentials(self, path: str) -> None:
        """
        Guarda credenciales de forma segura.
        
        Args:
            path: Ruta donde guardar credenciales
        """
        os.makedirs(os.path.dirname(path), exist_ok=True)
        encrypted_data = self._fernet.encrypt(
            json.dumps(self._credentials).encode()
        )
        with open(path, 'wb') as f:
            f.write(encrypted_data)
    
    def set_provider_credentials(self,
                               provider: str,
                               username: str,
                               password: str) -> None:
        """
        Establece credenciales para un proveedor.
        
        Args:
            provider: ID del proveedor
            username: Nombre de usuario
            password: Contraseña
        """
        provider = provider.upper()
        self._credentials[provider] = {
            "username": username,
            "password": password
        }
    
    def get_provider_credentials(self, provider: str) -> Optional[dict]:
        """
        Obtiene credenciales de un proveedor.
        
        Args:
            provider: ID del proveedor
        
        Returns:
            Dict con username y password o None
        """
        return self._credentials.get(provider.upper())
    
    def load_from_env(self) -> None:
        """Carga credenciales desde variables de entorno."""
        for provider in ["OLA", "OTRO_PROVEEDOR"]:  # Agregar más según necesidad
            env_prefix = f"TRAVEL_AGENT_{provider}"
            username = os.getenv(f"{env_prefix}_USERNAME")
            password = os.getenv(f"{env_prefix}_PASSWORD")
            
            if username and password:
                self.set_provider_credentials(provider, username, password)
    
    def validate_credentials(self, provider: str) -> bool:
        """
        Valida que existan las credenciales necesarias.
        
        Args:
            provider: ID del proveedor
        
        Returns:
            True si las credenciales están completas
        """
        creds = self.get_provider_credentials(provider)
        return bool(
            creds and
            "username" in creds and
            "password" in creds and
            creds["username"] and
            creds["password"]
        )
