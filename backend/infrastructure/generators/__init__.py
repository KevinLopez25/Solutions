"""
Orquestador de generadores PPTX.
Recibe pptx_bytes + config + catalog_data y aplica los generadores en cadena.

Orden de ejecución:
  1. fda_perfiles         — Perfiles FDA
  2. as_is_to_be          — Análisis AS-IS / TO-BE
  3. roadmap              — Roadmap de fases
  4. consideraciones      — Consideraciones
  5. cronograma_entregables — Entregables por torre
  6. cronograma_preview   — Preview de imagen del cronograma (NUEVO)
  7. oferta_economica     — Tabla de oferta económica
"""
from infrastructure.generators import (
    fda_perfiles, consideraciones, cronograma_entregables, as_is_to_be,
    roadmap, oferta_economica, cronograma_preview
)


def generate(pptx_bytes: bytes, config: dict, catalog_data: dict) -> bytes:
    pptx_bytes = fda_perfiles.edit(pptx_bytes, config, catalog_data)
    pptx_bytes = as_is_to_be.edit(pptx_bytes, config, catalog_data)
    pptx_bytes = roadmap.edit(pptx_bytes, config, catalog_data)
    pptx_bytes = consideraciones.edit(pptx_bytes, config, catalog_data)
    pptx_bytes = cronograma_entregables.edit(pptx_bytes, config, catalog_data)
    pptx_bytes = cronograma_preview.edit(pptx_bytes, config, catalog_data)
    pptx_bytes = oferta_economica.edit(pptx_bytes, config, catalog_data)
    return pptx_bytes
