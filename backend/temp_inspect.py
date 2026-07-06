import zipfile, re
from pathlib import Path
from lxml import etree
A='http://schemas.openxmlformats.org/drawingml/2006/main'
P='http://schemas.openxmlformats.org/presentationml/2006/main'
path = Path('templates/CS-FR-012-PROPUESTA_COMERCIAL_PERIFERIA_IT_CORP.pptx')
with zipfile.ZipFile(path) as z:
    for s in ['ppt/slides/slide5.xml','ppt/slides/slide6.xml','ppt/slides/slide11.xml']:
        xml=z.read(s)
        root=etree.fromstring(xml)
        print('---', s)
        for sp in root.iter('{'+P+'}sp'):
            nvpr=sp.find('.//{'+P+'}cNvPr')
            name=nvpr.attrib.get('name','') if nvpr is not None else ''
            ph=sp.find('.//{'+P+'}ph')
            phtype=ph.attrib.get('type','') if ph is not None else ''
            phidx=ph.attrib.get('idx','') if ph is not None else ''
            txb=sp.find('.//{'+P+'}txBody')
            txt=''.join(t.text or '' for t in txb.findall('.//{'+A+'}t')) if txb is not None else ''
            if txt.strip() or name or phtype or phidx:
                print(' name=',repr(name),'type=',repr(phtype),'idx=',repr(phidx),'txt=',repr(txt.strip()))

