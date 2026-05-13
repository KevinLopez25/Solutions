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
from domain.ai.service import generate_as_is_to_be, generate_roadmap_phases

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
    if request.incluir_as_is_to_be:
        as_is_text, to_be_text = generate_as_is_to_be(config.get('excel_data', {}), request.as_is_description)
        config['as_is_text'] = as_is_text
        config['to_be_text'] = to_be_text

    roadmap_phases = generate_roadmap_phases(config.get('excel_data', {}))
    if roadmap_phases:
        config['roadmap_phases'] = roadmap_phases

    result_bytes = orchestrator.generate(pptx_bytes, config, catalog_data)

    filename = f"Propuesta_Periferia_{filial.upper()}.pptx"
    return GenerarPropuestaResponse(
        filename=filename,
        content_b64=base64.b64encode(result_bytes).decode(),
    )
