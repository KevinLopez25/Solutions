import io, zipfile
from lxml import etree
from infrastructure.generators.roadmap import edit

TEST_SLIDE_ROADMAP = '''
<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
       xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
       xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
<p:cSld><p:spTree>
<p:sp><p:nvSpPr><p:cNvPr name="Fase 1"/></p:nvSpPr>
<p:spPr><a:xfrm><a:off x="100" y="100"/><a:ext cx="1000" cy="500"/></a:xfrm></p:spPr>
<p:txBody><a:p><a:r><a:t>XXXXXXX</a:t></a:r></a:p></p:txBody></p:sp>
<p:sp><p:nvSpPr><p:cNvPr name="Fase 2"/></p:nvSpPr>
<p:spPr><a:xfrm><a:off x="2100" y="100"/><a:ext cx="1000" cy="500"/></a:xfrm></p:spPr>
<p:txBody><a:p><a:r><a:t>XXXXXXX</a:t></a:r></a:p></p:txBody></p:sp>
<p:sp><p:nvSpPr><p:cNvPr name="Fase 3"/></p:nvSpPr>
<p:spPr><a:xfrm><a:off x="4100" y="100"/><a:ext cx="1000" cy="500"/></a:xfrm></p:spPr>
<p:txBody><a:p><a:r><a:t>XXXXXXX</a:t></a:r></a:p></p:txBody></p:sp>
<p:sp><p:nvSpPr><p:cNvPr name="Fase 4"/></p:nvSpPr>
<p:spPr><a:xfrm><a:off x="6100" y="100"/><a:ext cx="1000" cy="500"/></a:xfrm></p:spPr>
<p:txBody><a:p><a:r><a:t>XXXXXXX</a:t></a:r></a:p></p:txBody></p:sp>
</p:spTree></p:cSld></p:sld>
'''

def _build_minimal_pptx(slides_dict=None):
    if slides_dict is None:
        slides_dict = {'ppt/slides/slide1.xml': '<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"><p:cSld><p:spTree/></p:cSld></p:sld>'}
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml','<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>')
        rels = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        i = 1
        for path in slides_dict:
            slide_name = path.replace('ppt/', '')
            rels += f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="{slide_name}"/>'
            i += 1
        rels += '</Relationships>'
        z.writestr('ppt/_rels/presentation.xml.rels', rels)
        prs = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><p:sldIdLst>'
        i = 1
        for path in slides_dict:
            prs += f'<p:sldId id="{256 + i}" r:id="rId{i}"/>'
            i += 1
        prs += '</p:sldIdLst></p:presentation>'
        z.writestr('ppt/presentation.xml', prs)
        for path, content in slides_dict.items():
            z.writestr(path, content)
    return buf.getvalue()

pptx = _build_minimal_pptx({'ppt/slides/slide4.xml': TEST_SLIDE_ROADMAP})
config = {'roadmap_phases': [{'title': 'T1', 'highlight': 'H1', 'description': 'D1'}, {'title': 'T2', 'highlight': 'H2', 'description': 'D2'}, {'title': 'T3', 'highlight': 'H3', 'description': 'D3'}, {'title': 'T4', 'highlight': 'H4', 'description': 'D4'}]}
res = edit(pptx, config, {})
print('result bytes:', isinstance(res, bytes), 'len=', len(res))
