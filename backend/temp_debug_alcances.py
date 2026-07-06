import zipfile
from pathlib import Path
from lxml import etree
import sys
sys.path.insert(0, r'c:\Users\kevinlopez\Documents\Solutions\backend')
from infrastructure.generators.alcances import _find_alcances_slide, _get_slide_order, _make_overflow_xml

pptx = Path('templates/CS-FR-012-PROPUESTA_COMERCIAL_PERIFERIA_IT_CORP.pptx')

with zipfile.ZipFile(pptx, 'r') as zin:
    files = {n: zin.read(n) for n in zin.namelist()}
slides_order = _get_slide_order(pptx.read_bytes())
print('slide order:', slides_order)
print('found alcances slide:', _find_alcances_slide(files, slides_order))
xml = files[_find_alcances_slide(files, slides_order)]
new_xml = _make_overflow_xml(xml, 'TORRE', [{'titulo': 'A', 'texto': 'B'}])
root = etree.fromstring(new_xml)
print('overflow text shapes:')
for sp in root.findall('.//{http://schemas.openxmlformats.org/presentationml/2006/main}sp'):
    txb = sp.find('.//{http://schemas.openxmlformats.org/presentationml/2006/main}txBody')
    if txb is None:
        continue
    txt = ''.join(t.text or '' for t in txb.findall('.//{http://schemas.openxmlformats.org/drawingml/2006/main}t')).strip()
    if txt:
        print('  ', repr(txt))
