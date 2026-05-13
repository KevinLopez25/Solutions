import io
import zipfile

from lxml import etree

PPTX_NS = {
    'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
    'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
}

SLIDE_PATH = 'ppt/slides/slide5.xml'


def _extract_shape_text(shape):
    texts = [t.text or '' for t in shape.findall('.//a:t', namespaces=PPTX_NS)]
    return '\n'.join(texts).strip()


def _clear_shape_text(shape):
    tx_body = shape.find('.//p:txBody', namespaces=PPTX_NS)
    if tx_body is None:
        return
    for child in list(tx_body):
        if child.tag == f'{{{PPTX_NS["a"]}}}p':
            tx_body.remove(child)


def _set_title_text(shape, text: str):
    if shape is None:
        return
    tx_body = shape.find('.//p:txBody', namespaces=PPTX_NS)
    if tx_body is None:
        return

    for child in list(tx_body):
        if child.tag == f'{{{PPTX_NS["a"]}}}p':
            tx_body.remove(child)

    lines = [line.strip() for line in str(text or '').splitlines() if line.strip()]
    if not lines:
        lines = ['']
    for line in lines:
        p = etree.SubElement(tx_body, f'{{{PPTX_NS["a"]}}}p')
        r = etree.SubElement(p, f'{{{PPTX_NS["a"]}}}r')
        t = etree.SubElement(r, f'{{{PPTX_NS["a"]}}}t')
        t.text = line


def _set_shape_text(shape, text: str, bold: bool = False, size: int = 900):
    if shape is None:
        return
    tx_body = shape.find('.//p:txBody', namespaces=PPTX_NS)
    if tx_body is None:
        return

    for child in list(tx_body):
        if child.tag == f'{{{PPTX_NS["a"]}}}p':
            tx_body.remove(child)

    lines = [line.strip() for line in str(text or '').splitlines() if line.strip()]
    if not lines:
        lines = ['']

    for line in lines:
        p = etree.SubElement(tx_body, f'{{{PPTX_NS["a"]}}}p')
        r = etree.SubElement(p, f'{{{PPTX_NS["a"]}}}r')
        r_pr = etree.SubElement(r, f'{{{PPTX_NS["a"]}}}rPr')
        r_pr.set('sz', str(size))
        if bold:
            r_pr.set('b', '1')
        r_fonts = etree.SubElement(r_pr, f'{{{PPTX_NS["a"]}}}rFonts')
        r_fonts.set('ascii', 'Calibri')
        r_fonts.set('hAnsi', 'Calibri')
        r_fonts.set('cs', 'Calibri')
        t = etree.SubElement(r, f'{{{PPTX_NS["a"]}}}t')
        t.text = line


def edit(pptx_bytes: bytes, config: dict, catalog_data: dict) -> bytes:
    roadmap_phases = config.get('roadmap_phases')
    if not roadmap_phases or not isinstance(roadmap_phases, list) or len(roadmap_phases) != 4:
        return pptx_bytes

    with zipfile.ZipFile(io.BytesIO(pptx_bytes), mode='r') as zin:
        files = {name: zin.read(name) for name in zin.namelist()}

    if SLIDE_PATH not in files:
        return pptx_bytes

    root = etree.fromstring(files[SLIDE_PATH])
    shapes = root.findall('.//p:sp', namespaces=PPTX_NS)
    phase_title_indices = [idx for idx, shape in enumerate(shapes) if _extract_shape_text(shape).strip() == 'XXXXXXX']
    if len(phase_title_indices) < 4:
        return pptx_bytes

    for phase_index, title_idx in enumerate(phase_title_indices[:4]):
        phase = roadmap_phases[phase_index]
        title_shape = shapes[title_idx]

        body_shapes = []
        for next_idx in range(title_idx + 1, len(shapes)):
            if len(body_shapes) == 2:
                break
            text = _extract_shape_text(shapes[next_idx]).strip()
            if not text or text in {'START', 'FINISH', 'XXXXXXX'}:
                continue
            body_shapes.append(shapes[next_idx])

        if len(body_shapes) != 2:
            return pptx_bytes

        body_shape_1, body_shape_2 = body_shapes

        _set_title_text(title_shape, phase.get('title', ''))
        _set_shape_text(body_shape_1, phase.get('highlight', ''), bold=True, size=900)
        _set_shape_text(body_shape_2, phase.get('description', ''), bold=False, size=900)

    files[SLIDE_PATH] = etree.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True)

    with io.BytesIO() as out:
        with zipfile.ZipFile(out, mode='w', compression=zipfile.ZIP_DEFLATED) as zout:
            for name, data in files.items():
                zout.writestr(name, data)
        return out.getvalue()
