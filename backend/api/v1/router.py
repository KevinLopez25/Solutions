from fastapi import APIRouter

from api.v1.catalogo.router import router as catalogo_router
from api.v1.propuesta.router import router as propuesta_router
from api.v1.cronograma.router import router as cronograma_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(catalogo_router)
api_router.include_router(propuesta_router)
api_router.include_router(cronograma_router)
