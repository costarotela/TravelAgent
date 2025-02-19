"""Main FastAPI application."""

import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import router as api_router
from src.utils.monitoring import SimpleMonitor
from src.utils.cache import SimpleCache
from agent_core.managers.session_manager import session_manager
from agent_core.managers.storage_manager import storage_manager

# Inicializar monitores
monitor = SimpleMonitor()
cache = SimpleCache()

# Crear aplicación
app = FastAPI(
    title="Travel Agent API",
    description="API for travel provider management",
    version="0.1.0",
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir rutas de la API
app.include_router(api_router)

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

@app.get("/status")
async def get_status():
    """Get basic system status."""
    return {
        "status": "operational",
        "cache_size": len(cache.cache),
        "uptime": "available in full version",
    }

@app.on_event("startup")
async def startup_event():
    """Inicializar componentes al arrancar."""
    # Inicializar storage manager
    await storage_manager.init()
    
    # Inicializar session manager
    await session_manager.init()

async def main():
    """Función principal asíncrona."""
    config = {
        'host': '0.0.0.0',
        'port': 8001,
        'reload': True
    }
    
    import uvicorn
    server = uvicorn.Server(uvicorn.Config(app, **config))
    await server.serve()

if __name__ == "__main__":
    # Ejecutar el servidor en el event loop
    asyncio.run(main())
