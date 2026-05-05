from fastapi import APIRouter, HTTPException

from domain.cronograma.entities import GenerarCronogramaRequest, GenerarCronogramaResponse
from domain.cronograma import service

router = APIRouter(prefix="/cronograma", tags=["Cronograma"])


@router.post("/generar", response_model=GenerarCronogramaResponse)
def generar_cronograma(request: GenerarCronogramaRequest):
    try:
        return service.generar_cronograma(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error interno: {exc}")
