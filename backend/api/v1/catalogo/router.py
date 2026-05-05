from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.dependencies import get_db
from domain.catalogo import service
from domain.catalogo.entities import (
    TorreOut, TorreCreate,
    PerfilOut, PerfilCreate, PerfilUpdate,
    ConsideracionOut, ConsideracionCreate, ConsideracionUpdate,
    EntregableOut, EntregableCreate, EntregableUpdate,
    FueraAlcanceOut, FueraAlcanceCreate, FueraAlcanceUpdate,
)

router = APIRouter(prefix="/catalogo", tags=["Catálogo"])


# ── Torres ────────────────────────────────────────────────────────────────────
@router.get("/torres", response_model=list[TorreOut])
def list_torres(db: Session = Depends(get_db)):
    return service.list_torres(db)


@router.post("/torres", response_model=TorreOut, status_code=status.HTTP_201_CREATED)
def create_torre(data: TorreCreate, db: Session = Depends(get_db)):
    return service.create_torre(db, data)


@router.delete("/torres/{torre_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_torre(torre_id: int, db: Session = Depends(get_db)):
    if not service.delete_torre(db, torre_id):
        raise HTTPException(status_code=404, detail="Torre no encontrada")


# ── Perfiles ──────────────────────────────────────────────────────────────────
@router.get("/perfiles", response_model=list[PerfilOut])
def list_perfiles(torre_id: int | None = None, db: Session = Depends(get_db)):
    return service.list_perfiles(db, torre_id)


@router.post("/perfiles", response_model=PerfilOut, status_code=status.HTTP_201_CREATED)
def create_perfil(data: PerfilCreate, db: Session = Depends(get_db)):
    return service.create_perfil(db, data)


@router.put("/perfiles/{perfil_id}", response_model=PerfilOut)
def update_perfil(perfil_id: int, data: PerfilUpdate, db: Session = Depends(get_db)):
    obj = service.update_perfil(db, perfil_id, data)
    if not obj:
        raise HTTPException(status_code=404, detail="Perfil no encontrado")
    return obj


@router.delete("/perfiles/{perfil_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_perfil(perfil_id: int, db: Session = Depends(get_db)):
    if not service.delete_perfil(db, perfil_id):
        raise HTTPException(status_code=404, detail="Perfil no encontrado")


# ── Consideraciones ───────────────────────────────────────────────────────────
@router.get("/consideraciones", response_model=list[ConsideracionOut])
def list_consideraciones(torre_id: int | None = None, db: Session = Depends(get_db)):
    return service.list_consideraciones(db, torre_id)


@router.post("/consideraciones", response_model=ConsideracionOut, status_code=status.HTTP_201_CREATED)
def create_consideracion(data: ConsideracionCreate, db: Session = Depends(get_db)):
    return service.create_consideracion(db, data)


@router.put("/consideraciones/{consideracion_id}", response_model=ConsideracionOut)
def update_consideracion(consideracion_id: int, data: ConsideracionUpdate, db: Session = Depends(get_db)):
    obj = service.update_consideracion(db, consideracion_id, data)
    if not obj:
        raise HTTPException(status_code=404, detail="Consideración no encontrada")
    return obj


@router.delete("/consideraciones/{consideracion_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_consideracion(consideracion_id: int, db: Session = Depends(get_db)):
    if not service.delete_consideracion(db, consideracion_id):
        raise HTTPException(status_code=404, detail="Consideración no encontrada")


# ── Entregables ───────────────────────────────────────────────────────────────
@router.get("/entregables", response_model=list[EntregableOut])
def list_entregables(torre_id: int | None = None, db: Session = Depends(get_db)):
    return service.list_entregables(db, torre_id)


@router.post("/entregables", response_model=EntregableOut, status_code=status.HTTP_201_CREATED)
def create_entregable(data: EntregableCreate, db: Session = Depends(get_db)):
    return service.create_entregable(db, data)


@router.put("/entregables/{ent_id}", response_model=EntregableOut)
def update_entregable(ent_id: int, data: EntregableUpdate, db: Session = Depends(get_db)):
    obj = service.update_entregable(db, ent_id, data)
    if not obj:
        raise HTTPException(status_code=404, detail="Entregable no encontrado")
    return obj


@router.delete("/entregables/{ent_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_entregable(ent_id: int, db: Session = Depends(get_db)):
    if not service.delete_entregable(db, ent_id):
        raise HTTPException(status_code=404, detail="Entregable no encontrado")


# ── Fuera del Alcance ─────────────────────────────────────────────────────────
@router.get("/fuera-del-alcance", response_model=list[FueraAlcanceOut])
def list_fuera_alcance(torre_id: int | None = None, db: Session = Depends(get_db)):
    return service.list_fuera_alcance(db, torre_id)


@router.post("/fuera-del-alcance", response_model=FueraAlcanceOut, status_code=status.HTTP_201_CREATED)
def create_fuera_alcance(data: FueraAlcanceCreate, db: Session = Depends(get_db)):
    return service.create_fuera_alcance(db, data)


@router.put("/fuera-del-alcance/{fda_id}", response_model=FueraAlcanceOut)
def update_fuera_alcance(fda_id: int, data: FueraAlcanceUpdate, db: Session = Depends(get_db)):
    obj = service.update_fuera_alcance(db, fda_id, data)
    if not obj:
        raise HTTPException(status_code=404, detail="Ítem no encontrado")
    return obj


@router.delete("/fuera-del-alcance/{fda_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_fuera_alcance(fda_id: int, db: Session = Depends(get_db)):
    if not service.delete_fuera_alcance(db, fda_id):
        raise HTTPException(status_code=404, detail="Ítem no encontrado")
