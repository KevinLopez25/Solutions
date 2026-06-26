from unittest.mock import patch

import pytest

from infrastructure.generators import generate


def test_generate_chains_generators():
    pptx = b'PK\x05\x06'  # zip vacío inválido; solo para chequear llamado en cadena
    config = {}
    catalog_data = {}

    calls = []

    def fake_edit(pptx_bytes, config, catalog_data):
        calls.append((pptx_bytes, config, catalog_data))
        return pptx_bytes

    modules = [
        'infrastructure.generators.fda_perfiles',
        'infrastructure.generators.as_is_to_be',
        'infrastructure.generators.roadmap',
        'infrastructure.generators.consideraciones',
        'infrastructure.generators.alcances',
        'infrastructure.generators.cronograma_entregables',
        'infrastructure.generators.cronograma_preview',
        'infrastructure.generators.oferta_economica',
    ]

    with patch('infrastructure.generators.fda_perfiles.edit', side_effect=fake_edit), \
         patch('infrastructure.generators.as_is_to_be.edit', side_effect=fake_edit), \
         patch('infrastructure.generators.roadmap.edit', side_effect=fake_edit), \
         patch('infrastructure.generators.consideraciones.edit', side_effect=fake_edit), \
         patch('infrastructure.generators.alcances.edit', side_effect=fake_edit), \
         patch('infrastructure.generators.cronograma_entregables.edit', side_effect=fake_edit), \
         patch('infrastructure.generators.cronograma_preview.edit', side_effect=fake_edit), \
         patch('infrastructure.generators.oferta_economica.edit', side_effect=fake_edit):
        result = generate(pptx, config, catalog_data)

    assert len(calls) == 8
    assert result == pptx
