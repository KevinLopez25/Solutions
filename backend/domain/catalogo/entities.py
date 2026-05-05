from pydantic import BaseModel, ConfigDict


class TorreOut(BaseModel):
    id: int
    nombre: str
    nombre_norm: str
    activa: bool
    model_config = ConfigDict(from_attributes=True)


class PerfilOut(BaseModel):
    id: int
    torre_id: int
    rol: str
    descripcion: str
    model_config = ConfigDict(from_attributes=True)


class ConsideracionOut(BaseModel):
    id: int
    torre_id: int | None
    texto: str
    es_general: bool
    orden: int
    model_config = ConfigDict(from_attributes=True)


class EntregableOut(BaseModel):
    id: int
    torre_id: int
    item: str
    orden: int
    model_config = ConfigDict(from_attributes=True)


class FueraAlcanceOut(BaseModel):
    id: int
    torre_id: int
    item: str
    orden: int
    model_config = ConfigDict(from_attributes=True)


# ── Write schemas ─────────────────────────────────────────────────────────────

class TorreCreate(BaseModel):
    nombre: str


class PerfilCreate(BaseModel):
    torre_id: int
    rol: str
    descripcion: str


class PerfilUpdate(BaseModel):
    rol: str
    descripcion: str


class ConsideracionCreate(BaseModel):
    torre_id: int | None = None
    texto: str
    es_general: bool = False
    orden: int = 0


class ConsideracionUpdate(BaseModel):
    texto: str
    orden: int


class EntregableCreate(BaseModel):
    torre_id: int
    item: str
    orden: int = 0


class EntregableUpdate(BaseModel):
    item: str
    orden: int


class FueraAlcanceCreate(BaseModel):
    torre_id: int
    item: str
    orden: int = 0


class FueraAlcanceUpdate(BaseModel):
    item: str
    orden: int
