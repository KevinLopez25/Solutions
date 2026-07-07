import io
import zipfile
import re
from pathlib import Path
from infrastructure.generators import generate
from lxml import etree

A='http://schemas.openxmlformats.org/drawingml/2006/main'
P='http://schemas.openxmlformats.org/presentationml/2006/main'

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
    for slide in ['ppt/slides/slide5.xml', 'ppt/slides/slide6.xml']:
        print('===', slide, '===')
        if slide not in z.namelist():
            print('MISSING')
            continue
        xml = z.read(slide).decode('utf-8')
        texts = re.findall(r'<a:t>(.*?)</a:t>', xml, flags=re.DOTALL)
        print('text count', len(texts))
        for i,t in enumerate(texts):
            t2 = t.strip()
            if not t2: continue
            print(i, repr(t2))
        print('----')
