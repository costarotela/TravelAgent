"""Sistema de configuración del agente de viajes."""

import os
from pathlib import Path
from dataclasses import dataclass


@dataclass
class Config:
    """Configuración básica del sistema."""

    base_dir: Path
    data_dir: Path
    db_type: str = "sqlite"
    mongodb_uri: str = ""
    mongodb_db: str = "travel_agent"

    @classmethod
    def create(cls) -> "Config":
        """Crear instancia de configuración."""
        base_dir = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        data_dir = base_dir / "data"
        data_dir.mkdir(exist_ok=True)

        mongodb_uri = os.getenv("MONGODB_URI", "")
        mongodb_db = os.getenv("MONGODB_DB", "travel_agent")

        return cls(
            base_dir=base_dir,
            data_dir=data_dir,
            mongodb_uri=mongodb_uri,
            mongodb_db=mongodb_db,
        )


# Instancia global de configuración
config = Config.create()
