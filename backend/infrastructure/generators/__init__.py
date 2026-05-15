"""
Orquestador de generadores PPTX.
Recibe pptx_bytes + config + catalog_data y aplica los cuatro generadores en cadena.
"""
from infrastructure.generators import fda_perfiles, consideraciones, cronograma_entregables, as_is_to_be, roadmap, oferta_economica


def generate(pptx_bytes: bytes, config: dict, catalog_data: dict) -> bytes:
    pptx_bytes = fda_perfiles.edit(pptx_bytes, config, catalog_data)
    pptx_bytes = as_is_to_be.edit(pptx_bytes, config, catalog_data)
    pptx_bytes = roadmap.edit(pptx_bytes, config, catalog_data)
    pptx_bytes = consideraciones.edit(pptx_bytes, config, catalog_data)
    pptx_bytes = cronograma_entregables.edit(pptx_bytes, config, catalog_data)
    pptx_bytes = oferta_economica.edit(pptx_bytes, config, catalog_data)
    return pptx_bytes
