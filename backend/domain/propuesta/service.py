"""
Servicio de dominio: orquesta la generación de propuestas PPTX.
"""
import base64
from pathlib import Path

from sqlalchemy.orm import Session

from core.config import settings
from domain.propuesta.entities import GenerarPropuestaRequest, GenerarPropuestaResponse
from infrastructure import generators as orchestrator
from infrastructure.repositories import catalogo_repository as repo
from infrastructure.repositories.catalogo_repository import build_catalog_data
from domain.ai.service import (
    generate_as_is_to_be,
    generate_roadmap_phases,
    fallback_roadmap_phases,
)

FILIALES = {
    "corp":  "CS-FR-012-PROPUESTA_COMERCIAL_PERIFERIA_IT_CORP.pptx",
    "group": "CS-FR-005-PROPUESTA_COMERCIAL_PERIFERIA_IT_GROUP.pptx",
    "cbit":  "CS-FR-011-PROPUESTA_COMERCIAL_CBIT.pptx",
}


def _normalize_text(value: str | None) -> str:
    return " ".join(str(value or "").strip().upper().split())


def _resolve_template_path(request: GenerarPropuestaRequest) -> Path:
    filial = str(request.filial or "").strip().lower()
    if not filial:
        raise ValueError("Filial inválida")

    requested_name = str(request.template_name or "").strip()
    section_name = str(request.template_section or "").strip().lower() or "default"

    candidates: list[Path] = []
    if requested_name:
        # Intentar con el nombre tal cual y también con extensión .pptx
        candidates.extend([
            settings.templates_path / filial / section_name / requested_name,
            settings.templates_path / filial / section_name / f"{requested_name}.pptx",
            settings.templates_path / filial / requested_name,
            settings.templates_path / filial / f"{requested_name}.pptx",
            settings.templates_path / requested_name,
            settings.templates_path / f"{requested_name}.pptx",
            Path(requested_name),
            Path(f"{requested_name}.pptx"),
        ])

    default_name = FILIALES.get(filial)
    if default_name:
        candidates.extend([
            settings.templates_path / filial / default_name,
            settings.templates_path / default_name,
        ])

    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate

    if requested_name:
        raise FileNotFoundError(f"Plantilla no encontrada: {requested_name}")

    raise FileNotFoundError(f"Plantilla no encontrada: {default_name or filial}")


def _catalog_torre_key(torre_name: str | None) -> str:
    if not torre_name:
        return ""
    return _normalize_text(torre_name).replace("TORRE ", "")


def _get_torre_candidates(excel_data: dict, request: GenerarPropuestaRequest) -> list[str]:
    names: list[str] = []
    for torre in excel_data.get('torres') or []:
        nombre = str(torre.get('nombre') or '').strip() if isinstance(torre, dict) else str(torre).strip()
        if nombre:
            names.append(nombre)
    for nombre in request.torres_seleccionadas or []:
        nombre = str(nombre).strip()
        if nombre and nombre not in names:
            names.append(nombre)
    return names


def _ensure_catalog_item(
    db: Session,
    catalog_data: dict,
    request: GenerarPropuestaRequest,
    excel_data: dict,
    entity: str,
    value: str,
    tower_name: str | None = None,
    description: str | None = None,
    persist: bool = True,
):
    if entity == 'perfil':
        torre_name = tower_name or (excel_data.get('torres') or [{}])[0].get('nombre') if isinstance((excel_data.get('torres') or [{}])[0], dict) else None
        if not torre_name:
            torre_name = (request.torres_seleccionadas or [None])[0]
        torre = None
        if persist and torre_name:
            try:
                if db is not None:
                    torre = repo.get_torre_by_norm(db, torre_name)
                    if torre is None:
                        torre = repo.create_torre(db, torre_name)
            except Exception as exc:
                print(f"[PROPUESTA] No se pudo resolver/crear torre '{torre_name}': {exc}")
        key = _catalog_torre_key(torre_name)
        perf_db = catalog_data.setdefault('perf_db', {})
        target = perf_db.setdefault(key, [])
        if any(_normalize_text(item.get('rol')) == _normalize_text(value) for item in target):
            return None
        desc = description or "No se encontró este perfil en la base de datos"
        if persist:
            try:
                if torre is not None:
                    repo.create_perfil(db, torre.id, value, desc)
                else:
                    repo.create_perfil(db, 1, value, desc)
            except Exception as exc:
                print(f"[PROPUESTA] No se pudo persistir perfil '{value}': {exc}")
        target.append({'rol': value, 'desc': desc})
        return {'rol': value, 'desc': desc}

    if entity == 'consideracion':
        target = catalog_data.setdefault('consideraciones_db', {}).setdefault('GENERALES', [])
        if any(_normalize_text(item) == _normalize_text(value) for item in target):
            return None
        desc = description or 'No se encontró esta consideración en la base de datos'
        if persist:
            try:
                repo.create_consideracion(db, value, None, True, 0)
            except Exception as exc:
                print(f"[PROPUESTA] No se pudo persistir consideración '{value}': {exc}")
        target.append(value)
        return value

    if entity == 'entregable':
        torre_name = tower_name or (excel_data.get('torres') or [{}])[0].get('nombre') if isinstance((excel_data.get('torres') or [{}])[0], dict) else None
        if not torre_name:
            torre_name = (request.torres_seleccionadas or [None])[0]
        torre = None
        if persist and torre_name:
            try:
                if db is not None:
                    torre = repo.get_torre_by_norm(db, torre_name)
                    if torre is None:
                        torre = repo.create_torre(db, torre_name)
            except Exception as exc:
                print(f"[PROPUESTA] No se pudo resolver/crear torre '{torre_name}': {exc}")
        entries = catalog_data.setdefault('entregables_db', [])
        final_torre = torre_name or 'GENERAL'
        entry = next((item for item in entries if _normalize_text(item.get('torre')) == _normalize_text(final_torre)), None)
        if entry is None:
            entry = {'torre': final_torre, 'items': []}
            entries.append(entry)
        if any(_normalize_text(item) == _normalize_text(value) for item in entry.get('items', [])):
            return None
        desc = description or 'No se encontró este entregable en la base de datos'
        if persist:
            try:
                if torre is not None:
                    repo.create_entregable(db, torre.id, value, 0)
                else:
                    repo.create_entregable(db, 1, value, 0)
            except Exception as exc:
                print(f"[PROPUESTA] No se pudo persistir entregable '{value}': {exc}")
        entry.setdefault('items', []).append(value)
        return {'item': value, 'desc': desc}

    if entity == 'fda':
        torre_name = tower_name or (excel_data.get('torres') or [{}])[0].get('nombre') if isinstance((excel_data.get('torres') or [{}])[0], dict) else None
        if not torre_name:
            torre_name = (request.torres_seleccionadas or [None])[0]
        torre = None
        if persist and torre_name:
            try:
                if db is not None:
                    torre = repo.get_torre_by_norm(db, torre_name)
                    if torre is None:
                        torre = repo.create_torre(db, torre_name)
            except Exception as exc:
                print(f"[PROPUESTA] No se pudo resolver/crear torre '{torre_name}': {exc}")
        key = _catalog_torre_key(torre_name)
        fda_db = catalog_data.setdefault('fda_db', {})
        target = fda_db.setdefault(key, [])
        if any(_normalize_text(item) == _normalize_text(value) for item in target):
            return None
        desc = description or 'No se encontró este ítem fuera de alcance en la base de datos'
        if persist:
            try:
                if torre is not None:
                    repo.create_fuera_alcance(db, torre.id, value, 0)
                else:
                    repo.create_fuera_alcance(db, 1, value, 0)
            except Exception as exc:
                print(f"[PROPUESTA] No se pudo persistir fuera de alcance '{value}': {exc}")
        target.append(value)
        return value

    return None


def _enrich_catalog_from_request(
    db: Session,
    catalog_data: dict,
    request: GenerarPropuestaRequest,
    excel_data: dict,
):
    """
    Enriquece el catálogo con los datos del Excel del cliente.
    
    DIFERENCIA CLAVE: NO llama a la IA durante la generación del documento.
    Si un ítem ya existe en la BD, conserva su descripción original.
    Si NO existe, lo guarda con un placeholder para que el usuario
    luego le pida al asistente IA que complete las descripciones desde el chat.
    """
    if not excel_data:
        return catalog_data

    PLACEHOLDER = 'Solicita al asistente IA que complete esta descripción'
    torre_candidates = _get_torre_candidates(excel_data, request)

    perfiles = excel_data.get('perfiles') or []
    for perfil_item in perfiles:
        if isinstance(perfil_item, dict):
            perfil_name = perfil_item.get('perfil') or perfil_item.get('rol') or ''
            torre_name = perfil_item.get('torre') or (torre_candidates[0] if torre_candidates else None)
        else:
            perfil_name = str(perfil_item).strip()
            torre_name = torre_candidates[0] if torre_candidates else None
        if not perfil_name:
            continue
        _ensure_catalog_item(
            db, catalog_data, request, excel_data,
            'perfil', perfil_name, torre_name,
            description=PLACEHOLDER, persist=True,
        )

    consideraciones = excel_data.get('consideraciones') or []
    for texto in consideraciones:
        texto = str(texto).strip()
        if not texto:
            continue
        _ensure_catalog_item(
            db, catalog_data, request, excel_data,
            'consideracion', texto,
            torre_candidates[0] if torre_candidates else None,
            description=PLACEHOLDER, persist=True,
        )

    entregables_groups = excel_data.get('entregables') or []
    for group in entregables_groups:
        torre_name = None
        items = []
        if isinstance(group, dict):
            torre_name = group.get('torre') or (torre_candidates[0] if torre_candidates else None)
            items = group.get('items') or []
        else:
            items = [group]
        for item in items:
            item = str(item).strip()
            if not item:
                continue
            _ensure_catalog_item(
                db, catalog_data, request, excel_data,
                'entregable', item, torre_name,
                description=PLACEHOLDER, persist=True,
            )

    fda_items = excel_data.get('fda') or []
    for item in fda_items:
        item = str(item).strip()
        if not item:
            continue
        _ensure_catalog_item(
            db, catalog_data, request, excel_data,
            'fda', item, torre_candidates[0] if torre_candidates else None,
            description=PLACEHOLDER, persist=True,
        )

    return catalog_data


def generar_propuesta(
    db: Session, request: GenerarPropuestaRequest
) -> GenerarPropuestaResponse:
    filial = request.filial.lower()
    if filial not in FILIALES:
        raise ValueError(f"Filial desconocida: {filial}")

    template_path = _resolve_template_path(request)
    pptx_bytes = template_path.read_bytes()
    catalog_data = build_catalog_data(db)

    config = request.model_dump()
    excel_data = config.get('excel_data', {}) or {}
    if request.actividades and not excel_data.get('actividades'):
        excel_data['actividades'] = [
            a.model_dump() if hasattr(a, 'model_dump') else dict(a)
            for a in request.actividades
        ]
    if request.roles and not excel_data.get('perfiles'):
        excel_data['perfiles'] = [
            r.model_dump() if hasattr(r, 'model_dump') else dict(r)
            for r in request.roles
        ]
    if not excel_data.get('torres') and request.torres_seleccionadas:
        excel_data['torres'] = [
            {'nombre': str(t).strip(), 'horas': 0, 'personas': 1}
            for t in request.torres_seleccionadas
            if str(t).strip()
        ]
    config['excel_data'] = excel_data
    _enrich_catalog_from_request(db, catalog_data, request, excel_data)

    if request.incluir_as_is_to_be:
        try:
            as_is_text, to_be_text = generate_as_is_to_be(config.get('excel_data', {}), request.as_is_description)
            config['as_is_text'] = as_is_text
            config['to_be_text'] = to_be_text
        except Exception as exc:
            print(f"[PROPUESTA] No se pudo generar AS-IS/TO-BE: {exc}")
            config['as_is_text'] = ''
            config['to_be_text'] = ''

    try:
        roadmap_phases = generate_roadmap_phases(config.get('excel_data', {}))
        if not roadmap_phases or not isinstance(roadmap_phases, list) or len(roadmap_phases) != 4:
            raise RuntimeError('Roadmap inválido o incompleto')
        config['roadmap_phases'] = roadmap_phases
    except Exception as exc:
        print(f"[PROPUESTA] No se pudo generar roadmap: {exc}")
        try:
            config['roadmap_phases'] = fallback_roadmap_phases(config.get('excel_data', {}))
            print("[PROPUESTA] Se generó roadmap de fallback.")
        except Exception as fallback_exc:
            print(f"[PROPUESTA] Fallback de roadmap también falló: {fallback_exc}")
            config['roadmap_phases'] = []

    result_bytes = orchestrator.generate(pptx_bytes, config, catalog_data)

    filename = f"Propuesta_Periferia_{filial.upper()}.pptx"
    return GenerarPropuestaResponse(
        filename=filename,
        content_b64=base64.b64encode(result_bytes).decode(),
    )