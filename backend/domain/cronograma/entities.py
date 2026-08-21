from pydantic import BaseModel


class RolCronograma(BaseModel):
    perfil: str
    seniority: str = ""
    personas: int = 1
    torre: str = ""


class ActividadCronograma(BaseModel):
    torre: str
    horas: float
    personas: int = 1


class GenerarCronogramaRequest(BaseModel):
    proyecto: str = ""
    cliente: str = ""
    horas_semanales: float = 42
    roles: list[RolCronograma] = []
    actividades: list[ActividadCronograma] = []


class GenerarCronogramaResponse(BaseModel):
    filename: str
    content_b64: str
