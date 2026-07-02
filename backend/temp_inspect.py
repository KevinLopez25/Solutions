import zipfile
from lxml import etree
from pathlib import Path
path = Path('templates/CS-FR-012-PROPUESTA_COMERCIAL_PERIFERIA_IT_CORP.pptx')
with zipfile.ZipFile(path) as z:
    slides = [n for n in z.namelist() if n.startswith('ppt/slides/slide')]
    with open('inspect_slides.txt', 'w', encoding='utf-8') as out:
        out.write(str(slides) + '\n')
        for s in slides:
            data = z.read(s)
            root = etree.fromstring(data)
            texts = []
            for tx in root.findall('.//{http://schemas.openxmlformats.org/presentationml/2006/main}sp//{http://schemas.openxmlformats.org/presentationml/2006/main}txBody'):
                txt = ''.join(t.text or '' for t in tx.findall('.//{http://schemas.openxmlformats.org/drawingml/2006/main}t')).strip()
                if txt:
                    texts.append(txt)
            out.write('--- ' + s + '\n')
            for t in texts:
                out.write('   ' + t + '\n')
