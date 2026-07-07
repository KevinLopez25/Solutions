import zipfile
import re
from pathlib import Path
from lxml import etree
A='http://schemas.openxmlformats.org/drawingml/2006/main'
P='http://schemas.openxmlformats.org/presentationml/2006/main'
for tpl in [
    'templates/CS-FR-012-PROPUESTA_COMERCIAL_PERIFERIA_IT_CORP.pptx',
    'templates/CS-FR-005-PROPUESTA_COMERCIAL_PERIFERIA_IT_GROUP.pptx',
    'templates/CS-FR-011-PROPUESTA_COMERCIAL_CBIT.pptx',
]:
    path = Path(tpl)
    print('===', tpl, '===')
    with zipfile.ZipFile(path, 'r') as z:
        slides = sorted(
            [n for n in z.namelist() if n.startswith('ppt/slides/slide') and n.endswith('.xml')],
            key=lambda s: int(re.search(r'slide(\d+)', s).group(1)),
        )
        print('slide files:', slides)
        for slide in slides:
            xml = z.read(slide)
            root = etree.fromstring(xml)
            titles = []
            for sp in root.iter('{'+P+'}sp'):
                ph = sp.find('.//{'+P+'}ph')
                if ph is not None:
                    txb = sp.find('.//{'+P+'}txBody')
                    txt = ''.join(t.text or '' for t in txb.findall('.//{'+A+'}t')) if txb is not None else ''
                    titles.append(txt.strip())
            if titles:
                print(' ', slide, titles)
