import zipfile
from lxml import etree
path = r'C:\Users\camilo.perez\Desktop\Solutions\backend\templates\CS-FR-012-PROPUESTA_COMERCIAL_PERIFERIA_IT_CORP.pptx'
with zipfile.ZipFile(path) as z:
    slide_paths = [n for n in z.namelist() if n.startswith('ppt/slides/slide') and n.endswith('.xml')]
    print('slides', slide_paths)
    for p in slide_paths:
        xml = etree.fromstring(z.read(p))
        names = [el.attrib.get('name','') for el in xml.findall('.//{http://schemas.openxmlformats.org/presentationml/2006/main}cNvPr') if el.attrib.get('name')]
        if 'Rectángulo 10' in names or 'CuadroTexto 32' in names or any('Fuera del Alcance' in (el.text or '') for el in xml.findall('.//{http://schemas.openxmlformats.org/drawingml/2006/main}t')):
            print('\n===', p)
            print('has rect 10:', 'Rectángulo 10' in names)
            print('has cuadro 32:', 'CuadroTexto 32' in names)
            print('shape names count', len(names))
            for n in names[:120]:
                if n.startswith('Rectángulo') or n.startswith('CuadroTexto') or n.startswith('Título') or n.startswith('Fuente'):
                    print(n)
            print('texts:')
            for t in xml.findall('.//{http://schemas.openxmlformats.org/drawingml/2006/main}t')[:50]:
                print(repr(t.text))
