import zipfile
from pathlib import Path
from infrastructure.generators.alcances import _find_alcances_slide, _get_slide_order

pptx = Path('templates/CS-FR-012-PROPUESTA_COMERCIAL_PERIFERIA_IT_CORP.pptx')
with zipfile.ZipFile(pptx, 'r') as zin:
    files = {n: zin.read(n) for n in zin.namelist()}
slides_order = _get_slide_order(pptx.read_bytes())
print('slide order:', slides_order)
print('found alcances slide:', _find_alcances_slide(files, slides_order))
