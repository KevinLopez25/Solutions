from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.dependencies import get_db
from domain.ia.entities import (
    ValidarPerfilesRequest, ValidarPerfilesResponse,
    ConfirmarPerfilRequest, ConfirmarPerfilResponse,
    ChatRequest, ChatResponse,
)
from domain.ia import service

router = APIRouter(prefix="/ia", tags=["IA"])


@router.post("/validar-perfiles", response_model=ValidarPerfilesResponse)
def validar_perfiles(request: ValidarPerfilesRequest, db: Session = Depends(get_db)):
    try:
        return service.validar_perfiles(request, db)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/confirmar-perfil", response_model=ConfirmarPerfilResponse)
def confirmar_perfil(request: ConfirmarPerfilRequest, db: Session = Depends(get_db)):
    try:
        return service.confirmar_perfil(request, db)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    try:
        return service.chat(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
