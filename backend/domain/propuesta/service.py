"""
Servicio de dominio: orquesta la generación de propuestas PPTX.
"""
import base64
from pathlib import Path

from sqlalchemy.orm import Session

from core.config import settings
from domain.propuesta.entities import GenerarPropuestaRequest, GenerarPropuestaResponse
from infrastructure import generators as orchestrator
from infrastructure.repositories.catalogo_repository import build_catalog_data
from domain.ai.service import (
    generate_as_is_to_be,
    generate_roadmap_phases,
    fallback_roadmap_phases,
)
from domain.propuesta.logo_service import sanitize_pptx

FILIALES = {
    "corp":  "CS-FR-012-PROPUESTA_COMERCIAL_PERIFERIA_IT_CORP.pptx",
    "group": "CS-FR-005-PROPUESTA_COMERCIAL_PERIFERIA_IT_GROUP.pptx",
    "cbit":  "CS-FR-011-PROPUESTA_COMERCIAL_CBIT.pptx",
}


def generar_propuesta(
    db: Session, request: GenerarPropuestaRequest
) -> GenerarPropuestaResponse:
    filial = request.filial.lower()
    template_name = FILIALES.get(filial)
    if not template_name:
        raise ValueError(f"Filial desconocida: {filial}")

    template_path: Path = settings.templates_path / template_name
    if not template_path.exists():
        raise FileNotFoundError(f"Plantilla no encontrada: {template_name}")

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

    result_bytes = sanitize_pptx(orchestrator.generate(pptx_bytes, config, catalog_data))

    filename = f"Propuesta_Periferia_{filial.upper()}.pptx"
    return GenerarPropuestaResponse(
        filename=filename,
        content_b64=base64.b64encode(result_bytes).decode(),
    )
