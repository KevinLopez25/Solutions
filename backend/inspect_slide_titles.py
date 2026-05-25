import zipfile
import re
from lxml import etree

root = 'templates/CS-FR-012-PROPUESTA_COMERCIAL_PERIFERIA_IT_CORP.pptx'
with zipfile.ZipFile(root) as z:
    slides = [n for n in z.namelist() if n.startswith('ppt/slides/slide') and n.endswith('.xml')]
    slides.sort(key=lambda s: int(re.search(r'slide(\d+)', s).group(1)))
    print('slides', slides)
    for s in slides[:15]:
        data = z.read(s)
        rootx = etree.fromstring(data)
        texts = []
        for sp in rootx.findall('.//{http://schemas.openxmlformats.org/presentationml/2006/main}sp'):
            ph = sp.find('.//{http://schemas.openxmlformats.org/presentationml/2006/main}ph')
            if ph is not None:
                txt = ' '.join([t.text for t in sp.findall('.//{http://schemas.openxmlformats.org/drawingml/2006/main}t') if t.text])
                texts.append((s, dict(ph.attrib), txt))
        if texts:
            print('----', s)
            for t in texts:
                print(t)
