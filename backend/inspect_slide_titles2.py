import zipfile
import re
from lxml import etree
root='templates/CS-FR-012-PROPUESTA_COMERCIAL_PERIFERIA_IT_CORP.pptx'
with zipfile.ZipFile(root) as z:
    for s in ['ppt/slides/slide9.xml','ppt/slides/slide12.xml']:
        print('====', s)
        data = z.read(s)
        rootx = etree.fromstring(data)
        for tag in ['sp','graphicFrame','cxnSp','pic']:
            for el in rootx.findall(f'.//{{http://schemas.openxmlformats.org/presentationml/2006/main}}{tag}'):
                ph = el.find('.//{http://schemas.openxmlformats.org/presentationml/2006/main}ph')
                texts = [t.text for t in el.findall('.//{http://schemas.openxmlformats.org/drawingml/2006/main}t') if t.text]
                if texts:
                    print(tag, 'ph=', dict(ph.attrib) if ph is not None else None, 'text=', ' | '.join(texts))
