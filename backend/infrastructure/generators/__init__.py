"""
Orquestador de generadores PPTX.
Recibe pptx_bytes + config + catalog_data y aplica los tres generadores en cadena.
"""
from infrastructure.generators import fda_perfiles, consideraciones, cronograma_entregables


def generate(pptx_bytes: bytes, config: dict, catalog_data: dict) -> bytes:
    pptx_bytes = fda_perfiles.edit(pptx_bytes, config, catalog_data)
    pptx_bytes = consideraciones.edit(pptx_bytes, config, catalog_data)
    pptx_bytes = cronograma_entregables.edit(pptx_bytes, config, catalog_data)
    return pptx_bytes
