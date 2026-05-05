"""
Servicio de dominio para el catálogo.
Orquesta las operaciones CRUD delegando persistencia al repositorio.
"""
from sqlalchemy.orm import Session

from domain.catalogo.entities import (
    TorreCreate, TorreOut,
    PerfilCreate, PerfilUpdate, PerfilOut,
    ConsideracionCreate, ConsideracionUpdate, ConsideracionOut,
    EntregableCreate, EntregableUpdate, EntregableOut,
    FueraAlcanceCreate, FueraAlcanceUpdate, FueraAlcanceOut,
)
from infrastructure.repositories import catalogo_repository as repo


# ── Torres ────────────────────────────────────────────────────────────────────

def list_torres(db: Session) -> list[TorreOut]:
    return [TorreOut.model_validate(t) for t in repo.get_torres(db)]


def create_torre(db: Session, data: TorreCreate) -> TorreOut:
    return TorreOut.model_validate(repo.create_torre(db, data.nombre))


def delete_torre(db: Session, torre_id: int) -> bool:
    return repo.delete_torre(db, torre_id)


# ── Perfiles ──────────────────────────────────────────────────────────────────

def list_perfiles(db: Session, torre_id: int | None = None) -> list[PerfilOut]:
    return [PerfilOut.model_validate(p) for p in repo.get_perfiles(db, torre_id)]


def create_perfil(db: Session, data: PerfilCreate) -> PerfilOut:
    return PerfilOut.model_validate(
        repo.create_perfil(db, data.torre_id, data.rol, data.descripcion)
    )


def update_perfil(db: Session, perfil_id: int, data: PerfilUpdate) -> PerfilOut | None:
    obj = repo.update_perfil(db, perfil_id, data.rol, data.descripcion)
    return PerfilOut.model_validate(obj) if obj else None


def delete_perfil(db: Session, perfil_id: int) -> bool:
    return repo.delete_perfil(db, perfil_id)


# ── Consideraciones ───────────────────────────────────────────────────────────

def list_consideraciones(db: Session, torre_id: int | None = None) -> list[ConsideracionOut]:
    return [ConsideracionOut.model_validate(c) for c in repo.get_consideraciones(db, torre_id)]


def create_consideracion(db: Session, data: ConsideracionCreate) -> ConsideracionOut:
    return ConsideracionOut.model_validate(
        repo.create_consideracion(
            db, data.texto, data.torre_id, data.es_general, data.orden
        )
    )


def update_consideracion(
    db: Session, consideracion_id: int, data: ConsideracionUpdate
) -> ConsideracionOut | None:
    obj = repo.update_consideracion(db, consideracion_id, data.texto, data.orden)
    return ConsideracionOut.model_validate(obj) if obj else None


def delete_consideracion(db: Session, consideracion_id: int) -> bool:
    return repo.delete_consideracion(db, consideracion_id)


# ── Entregables ───────────────────────────────────────────────────────────────

def list_entregables(db: Session, torre_id: int | None = None) -> list[EntregableOut]:
    return [EntregableOut.model_validate(e) for e in repo.get_entregables(db, torre_id)]


def create_entregable(db: Session, data: EntregableCreate) -> EntregableOut:
    return EntregableOut.model_validate(
        repo.create_entregable(db, data.torre_id, data.item, data.orden)
    )


def update_entregable(
    db: Session, ent_id: int, data: EntregableUpdate
) -> EntregableOut | None:
    obj = repo.update_entregable(db, ent_id, data.item, data.orden)
    return EntregableOut.model_validate(obj) if obj else None


def delete_entregable(db: Session, ent_id: int) -> bool:
    return repo.delete_entregable(db, ent_id)


# ── Fuera del Alcance ─────────────────────────────────────────────────────────

def list_fuera_alcance(db: Session, torre_id: int | None = None) -> list[FueraAlcanceOut]:
    return [FueraAlcanceOut.model_validate(f) for f in repo.get_fuera_alcance(db, torre_id)]


def create_fuera_alcance(db: Session, data: FueraAlcanceCreate) -> FueraAlcanceOut:
    return FueraAlcanceOut.model_validate(
        repo.create_fuera_alcance(db, data.torre_id, data.item, data.orden)
    )


def update_fuera_alcance(
    db: Session, fda_id: int, data: FueraAlcanceUpdate
) -> FueraAlcanceOut | None:
    obj = repo.update_fuera_alcance(db, fda_id, data.item, data.orden)
    return FueraAlcanceOut.model_validate(obj) if obj else None


def delete_fuera_alcance(db: Session, fda_id: int) -> bool:
    return repo.delete_fuera_alcance(db, fda_id)
