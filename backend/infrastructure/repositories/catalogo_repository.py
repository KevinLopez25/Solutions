"""
Repositorio de catálogo: acceso a datos de torres, perfiles,
consideraciones, entregables y fuera_del_alcance.
"""
import re
import unicodedata
from sqlalchemy.orm import Session

from infrastructure.models.catalogo import (
    Torre, Perfil, Consideracion, Entregable, FueraDelAlcance,
)


def _norm(s: str) -> str:
    s = (s or "").strip().upper()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).strip()


# ── Torres ────────────────────────────────────────────────────────────────────

def get_torres(db: Session, solo_activas: bool = True) -> list[Torre]:
    q = db.query(Torre)
    if solo_activas:
        q = q.filter(Torre.activa)
    return q.order_by(Torre.nombre).all()


def get_torre_by_id(db: Session, torre_id: int) -> Torre | None:
    return db.query(Torre).filter(Torre.id == torre_id).first()


def get_torre_by_norm(db: Session, nombre: str) -> Torre | None:
    return db.query(Torre).filter(Torre.nombre_norm == _norm(nombre)).first()


def create_torre(db: Session, nombre: str) -> Torre:
    obj = Torre(nombre=nombre, nombre_norm=_norm(nombre))
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def update_torre(db: Session, torre_id: int, nombre: str) -> Torre | None:
    obj = get_torre_by_id(db, torre_id)
    if not obj:
        return None
    obj.nombre = nombre
    obj.nombre_norm = _norm(nombre)
    db.commit()
    db.refresh(obj)
    return obj


def delete_torre(db: Session, torre_id: int) -> bool:
    obj = get_torre_by_id(db, torre_id)
    if not obj:
        return False
    db.delete(obj)
    db.commit()
    return True


# ── Perfiles ──────────────────────────────────────────────────────────────────

def get_perfiles(db: Session, torre_id: int | None = None) -> list[Perfil]:
    q = db.query(Perfil).filter(Perfil.activo)
    if torre_id:
        q = q.filter(Perfil.torre_id == torre_id)
    return q.all()


def create_perfil(db: Session, torre_id: int, rol: str, descripcion: str) -> Perfil:
    obj = Perfil(torre_id=torre_id, rol=rol, descripcion=descripcion)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def update_perfil(db: Session, perfil_id: int, rol: str, descripcion: str) -> Perfil | None:
    obj = db.query(Perfil).filter(Perfil.id == perfil_id).first()
    if not obj:
        return None
    obj.rol = rol
    obj.descripcion = descripcion
    db.commit()
    db.refresh(obj)
    return obj


def delete_perfil(db: Session, perfil_id: int) -> bool:
    obj = db.query(Perfil).filter(Perfil.id == perfil_id).first()
    if not obj:
        return False
    db.delete(obj)
    db.commit()
    return True


# ── Consideraciones ───────────────────────────────────────────────────────────

def get_consideraciones(db: Session, torre_id: int | None = None) -> list[Consideracion]:
    q = db.query(Consideracion).filter(Consideracion.activa)
    if torre_id is not None:
        q = q.filter(
            (Consideracion.torre_id == torre_id) | (Consideracion.es_general)
        )
    return q.order_by(Consideracion.orden).all()


def create_consideracion(
    db: Session, texto: str, torre_id: int | None, es_general: bool, orden: int = 0
) -> Consideracion:
    obj = Consideracion(
        torre_id=torre_id, texto=texto, es_general=es_general, orden=orden
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def update_consideracion(
    db: Session, consideracion_id: int, texto: str, orden: int
) -> Consideracion | None:
    obj = db.query(Consideracion).filter(Consideracion.id == consideracion_id).first()
    if not obj:
        return None
    obj.texto = texto
    obj.orden = orden
    db.commit()
    db.refresh(obj)
    return obj


def delete_consideracion(db: Session, consideracion_id: int) -> bool:
    obj = db.query(Consideracion).filter(Consideracion.id == consideracion_id).first()
    if not obj:
        return False
    db.delete(obj)
    db.commit()
    return True


# ── Entregables ───────────────────────────────────────────────────────────────

def get_entregables(db: Session, torre_id: int | None = None) -> list[Entregable]:
    q = db.query(Entregable).filter(Entregable.activo)
    if torre_id:
        q = q.filter(Entregable.torre_id == torre_id)
    return q.order_by(Entregable.orden).all()


def create_entregable(db: Session, torre_id: int, item: str, orden: int = 0) -> Entregable:
    obj = Entregable(torre_id=torre_id, item=item, orden=orden)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def update_entregable(db: Session, ent_id: int, item: str, orden: int) -> Entregable | None:
    obj = db.query(Entregable).filter(Entregable.id == ent_id).first()
    if not obj:
        return None
    obj.item = item
    obj.orden = orden
    db.commit()
    db.refresh(obj)
    return obj


def delete_entregable(db: Session, ent_id: int) -> bool:
    obj = db.query(Entregable).filter(Entregable.id == ent_id).first()
    if not obj:
        return False
    db.delete(obj)
    db.commit()
    return True


# ── Fuera del Alcance ─────────────────────────────────────────────────────────

def get_fuera_alcance(db: Session, torre_id: int | None = None) -> list[FueraDelAlcance]:
    q = db.query(FueraDelAlcance).filter(FueraDelAlcance.activo)
    if torre_id:
        q = q.filter(FueraDelAlcance.torre_id == torre_id)
    return q.order_by(FueraDelAlcance.orden).all()


def create_fuera_alcance(db: Session, torre_id: int, item: str, orden: int = 0) -> FueraDelAlcance:
    obj = FueraDelAlcance(torre_id=torre_id, item=item, orden=orden)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def update_fuera_alcance(db: Session, fda_id: int, item: str, orden: int) -> FueraDelAlcance | None:
    obj = db.query(FueraDelAlcance).filter(FueraDelAlcance.id == fda_id).first()
    if not obj:
        return None
    obj.item = item
    obj.orden = orden
    db.commit()
    db.refresh(obj)
    return obj


def delete_fuera_alcance(db: Session, fda_id: int) -> bool:
    obj = db.query(FueraDelAlcance).filter(FueraDelAlcance.id == fda_id).first()
    if not obj:
        return False
    db.delete(obj)
    db.commit()
    return True


# ── Carga del catálogo completo para los generadores ─────────────────────────

def build_catalog_data(db: Session) -> dict:
    """
    Construye el diccionario de catálogo que consumen los generadores PPTX.
    Reemplaza _load_generales() / _load_desde_generales() / _load_entregables().
    """
    fda_db: dict[str, list[str]] = {}
    perf_db: dict[str, list[dict]] = {}
    consid_db: dict[str, list[str]] = {}
    entregables_list: list[dict] = []

    torres = get_torres(db, solo_activas=True)
    torre_map = {t.id: t for t in torres}

    for fda in get_fuera_alcance(db):
        t = torre_map.get(fda.torre_id)
        if t:
            fda_db.setdefault(t.nombre_norm, []).append(fda.item)

    for p in get_perfiles(db):
        t = torre_map.get(p.torre_id)
        if t:
            key = t.nombre_norm.replace("TORRE ", "")
            perf_db.setdefault(key, []).append({"rol": p.rol, "desc": p.descripcion})

    for c in get_consideraciones(db):
        if c.es_general:
            consid_db.setdefault("GENERALES", []).append(c.texto)
        elif c.torre_id and c.torre_id in torre_map:
            t = torre_map[c.torre_id]
            consid_db.setdefault(t.nombre_norm, []).append(c.texto)

    for t in torres:
        items = [e.item for e in get_entregables(db, torre_id=t.id)]
        if items:
            entregables_list.append({"torre": t.nombre, "items": items})

    return {
        "fda_db": fda_db,
        "perf_db": perf_db,
        "consideraciones_db": consid_db,
        "entregables_db": entregables_list,
    }
