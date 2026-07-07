import base64
import io
import zipfile
from pathlib import Path
from lxml import etree
from infrastructure.generators import generate

pptx_path = Path('templates/CS-FR-012-PROPUESTA_COMERCIAL_PERIFERIA_IT_CORP.pptx')
with open(pptx_path, 'rb') as f:
    pptx_bytes = f.read()

config = {
    'roadmap_phases': [
        {'title': 'Fase 1', 'highlight': 'Inicio', 'description': 'Descripción 1'},
        {'title': 'Fase 2', 'highlight': 'Plan', 'description': 'Descripción 2'},
        {'title': 'Fase 3', 'highlight': 'Ejecución', 'description': 'Descripción 3'},
        {'title': 'Fase 4', 'highlight': 'Cierre', 'description': 'Descripción 4'},
    ],
    'excel_data': {
        'alcances': [
            {'torre': 'Torre A', 'items': [{'titulo': 'Item 1', 'descripcion': 'Desc 1'}]}
        ]
    },
    'opciones': {'usar_ia_alcances': False},
}
result = generate(pptx_bytes, config, {})
with zipfile.ZipFile(io.BytesIO(result), 'r') as z:
    for slide in ['ppt/slides/slide5.xml','ppt/slides/slide6.xml','ppt/slides/slide21.xml']:
        if slide in z.namelist():
            xml = z.read(slide).decode('utf-8')
            print('===', slide, '===')
            print(xml[:2000])
            print('----')
