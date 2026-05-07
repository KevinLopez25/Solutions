import traceback

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.dependencies import get_db
from domain.propuesta.entities import GenerarPropuestaRequest, GenerarPropuestaResponse
from domain.propuesta import service

router = APIRouter(prefix="/propuesta", tags=["Propuesta"])


@router.post("/generar", response_model=GenerarPropuestaResponse)
def generar_propuesta(request: GenerarPropuestaRequest, db: Session = Depends(get_db)):
    try:
        return service.generar_propuesta(db, request)
    except (ValueError, FileNotFoundError) as exc:
        error_msg = str(exc).strip() or "Error de validación"
        raise HTTPException(status_code=400, detail=error_msg)
    except Exception as exc:
        traceback.print_exc()
        error_msg = str(exc).strip() or "Error interno del servidor"
        raise HTTPException(status_code=500, detail=error_msg)


@router.get("/filiales")
def get_filiales():
    return ["corp", "group", "cbit"]
