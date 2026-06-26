import math
from unittest.mock import patch

import pytest

from infrastructure.generators import cronograma_image as cron_image


def test_generate_cronograma_image_raises_on_missing_activities():
    with pytest.raises(ValueError, match='No hay actividades'):
        cron_image.generate_cronograma_image({'actividades': []})


@pytest.mark.parametrize('total_semanas,people_per_act', [
    (1, 1),
    (2, 2),
    (4, 1),
    (8, 3),
    (12, 4),
])
@patch('infrastructure.generators.cronograma_image._render')
def test_generate_cronograma_image_computes_stats(mock_render, total_semanas, people_per_act):
    actividades = [
        {
            'torre': 'Torre ' + str(idx),
            'horas': total_semanas * people_per_act * 43,
            'personas': people_per_act,
        }
        for idx in range(3)
    ]

    mock_render.return_value = b'fake-png'

    result = cron_image.generate_cronograma_image({
        'actividades': actividades,
        'roles': [{'perfil': 'Dev Test', 'seniority': 'Sr', 'personas': people_per_act}],
        'nombre_proyecto': 'Proyecto Demo',
        'torre': 'Torre 1',
        'id_proyecto': 'ID-1',
        'fecha': '01 de enero de 2025',
    })

    assert result == b'fake-png'
    assert mock_render.called

    actividades_arg, roles_arg, semanas_arg, meta_arg = mock_render.call_args.args
    assert semanas_arg == total_semanas
    assert meta_arg['total_horas'] == sum(act['horas'] for act in actividades)


@patch('infrastructure.generators.cronograma_image._render')
def test_generate_cronograma_image_normalizes_roles(mock_render):
    mock_render.return_value = b''

    cron_image.generate_cronograma_image({
        'actividades': [{'torre': 'A', 'horas': 1, 'personas': 1}],
        'roles': [
            {'perfil': 'Developer', 'seniority': 'Mid', 'personas': 2},
            'Dev Fullstack',
        ],
    })

    roles = mock_render.call_args.args[1]
    assert roles[0]['perfil'] == 'Developer'
    assert roles[0]['seniority'] == 'Mid'
    assert roles[0]['personas'] == 2
    assert roles[1]['perfil'] == 'Dev Fullstack'
    assert roles[1]['seniority'] == ''
    assert roles[1]['personas'] == 1
