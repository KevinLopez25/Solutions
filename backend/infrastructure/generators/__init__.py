""" Orquestador de generadores PPTX.
Recibe pptx_bytes + config + catalog_data y aplica los generadores en cadena.

Orden de ejecucion:
  1. fda_perfiles           - Perfiles FDA
  2. as_is_to_be            - Analisis AS-IS / TO-BE
  3. roadmap                - Roadmap de fases
  4. consideraciones        - Consideraciones
  5. alcances               - Alcances por torre (regla o IA)
  6. cronograma_entregables - Entregables por torre
  7. cronograma_preview     - Preview de imagen del cronograma
  8. oferta_economica       - Tabla de oferta economica
  9. tarjeta_comercial      - Tarjeta comercial (2 slides tras slide 13) SIEMPRE AL FINAL
"""
from infrastructure.generators import (
    fda_perfiles, consideraciones, cronograma_entregables, as_is_to_be,
    roadmap, oferta_economica, cronograma_preview, alcances, tarjeta_comercial
)


def generate(pptx_bytes: bytes, config: dict, catalog_data: dict) -> bytes:
    pptx_bytes = fda_perfiles.edit(pptx_bytes, config, catalog_data)
    pptx_bytes = as_is_to_be.edit(pptx_bytes, config, catalog_data)
    pptx_bytes = roadmap.edit(pptx_bytes, config, catalog_data)
    pptx_bytes = consideraciones.edit(pptx_bytes, config, catalog_data)
    pptx_bytes = alcances.edit(pptx_bytes, config, catalog_data)
    pptx_bytes = cronograma_entregables.edit(pptx_bytes, config, catalog_data)
    pptx_bytes = cronograma_preview.edit(pptx_bytes, config, catalog_data)
    pptx_bytes = oferta_economica.edit(pptx_bytes, config, catalog_data)
    # La tarjeta comercial SIEMPRE al final.
    pptx_bytes = tarjeta_comercial.edit(pptx_bytes, config, catalog_data)
    return pptx_bytes
