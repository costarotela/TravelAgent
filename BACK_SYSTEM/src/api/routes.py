"""API routes for budget management."""

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from typing import List, Optional
from datetime import datetime, timedelta

from agent_core.managers.session_budget_manager import (
    SessionBudgetManager,
    get_budget_manager,
)
from agent_core.schemas.travel import PaqueteOLA
from .auth import (
    get_current_user,
    create_access_token,
    verify_password,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)

router = APIRouter(prefix="/api/v1")


@router.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """Obtener token de acceso."""
    # TODO: Implementar verificación contra base de datos
    # Por ahora usamos credenciales hardcodeadas para pruebas
    if form_data.username != "test" or not verify_password(
        form_data.password,
        "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewKyNiAYqeScNazS",
    ):  # password: test
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": form_data.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/sessions/create")
async def create_session(
    vendor_id: str,
    customer_id: str,
    current_user: str = Depends(get_current_user),
    budget_manager: SessionBudgetManager = Depends(get_budget_manager),
) -> dict:
    """Crear una nueva sesión de presupuesto."""
    try:
        session_id = await budget_manager.create_session(vendor_id, customer_id)
        return {"session_id": session_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sessions/{session_id}/packages")
async def add_package(
    session_id: str,
    package: PaqueteOLA,
    current_user: str = Depends(get_current_user),
    budget_manager: SessionBudgetManager = Depends(get_budget_manager),
) -> dict:
    """Agregar un paquete a la sesión activa."""
    try:
        await budget_manager.add_package(session_id, package)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}/budget")
async def get_session_budget(
    session_id: str,
    current_user: str = Depends(get_current_user),
    budget_manager: SessionBudgetManager = Depends(get_budget_manager),
) -> dict:
    """Obtener el presupuesto actual de la sesión."""
    try:
        budget = await budget_manager.get_budget(session_id)
        return budget
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sessions/{session_id}/modifications")
async def add_modification(
    session_id: str,
    modification: dict,
    current_user: str = Depends(get_current_user),
    budget_manager: SessionBudgetManager = Depends(get_budget_manager),
) -> dict:
    """Agregar una modificación al presupuesto."""
    try:
        await budget_manager.add_modification(session_id, modification)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sessions/{session_id}/close")
async def close_session(
    session_id: str,
    current_user: str = Depends(get_current_user),
    budget_manager: SessionBudgetManager = Depends(get_budget_manager),
) -> dict:
    """Cerrar una sesión de presupuesto."""
    try:
        await budget_manager.close_session(session_id)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
