"""Main FastAPI application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.utils.monitoring import SimpleMonitor
from src.utils.cache import SimpleCache

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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
