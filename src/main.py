"""Main application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.monitoring import router as monitoring_router

# Crear la aplicación FastAPI
app = FastAPI(
    title="Travel Provider Monitor",
    description="API for monitoring travel providers",
    version="1.0.0"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar los orígenes permitidos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir routers
app.include_router(monitoring_router)
