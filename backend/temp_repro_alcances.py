import io
import zipfile
from pathlib import Path
from lxml import etree
import sys
sys.path.insert(0, r'c:\Users\kevinlopez\Documents\Solutions\backend')
from infrastructure.generators import generate

pptx_path = Path('templates/CS-FR-012-PROPUESTA_COMERCIAL_PERIFERIA_IT_CORP.pptx')
bytes_data = pptx_path.read_bytes()
config = {
    'excel_data': {
        'alcances': [
            {'torre': 'PMO', 'items': [{'titulo': 'Item 1', 'descripcion': 'Desc 1'}, {'titulo': 'Item 2', 'descripcion': 'Desc 2'}]}
        ]
    },
    'opciones': {'usar_ia_alcances': False},
    'roadmap_phases': [
        {'title': 'F1', 'highlight': 'H1', 'description': 'D1'},
        {'title': 'F2', 'highlight': 'H2', 'description': 'D2'},
        {'title': 'F3', 'highlight': 'H3', 'description': 'D3'},
        {'title': 'F4', 'highlight': 'H4', 'description': 'D4'},
    ],
}
result = generate(bytes_data, config, {})
with zipfile.ZipFile(io.BytesIO(result), 'r') as zout:
    paths = [n for n in zout.namelist() if n.startswith('ppt/slides/')]
    print('output slides', paths)
    for p in paths:
        if p.endswith('slide5.xml') or p.endswith('slide6.xml') or p.endswith('slide7.xml') or p.endswith('slide8.xml'):
            print('---', p)
            xml = zout.read(p)
            root = etree.fromstring(xml)
            texts = []
            for sp in root.findall('.//{http://schemas.openxmlformats.org/presentationml/2006/main}sp'):
                txb = sp.find('.//{http://schemas.openxmlformats.org/presentationml/2006/main}txBody')
                if txb is None:
                    continue
                txt = ''.join(t.text or '' for t in txb.findall('.//{http://schemas.openxmlformats.org/drawingml/2006/main}t')).strip()
                if txt:
                    texts.append(txt)
            print('texts:', texts)
