"""Edita la diapositiva AS-IS / TO-BE del PPTX de propuesta."""
import io
import zipfile

from lxml import etree

PPTX_NS = {
    'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
    'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
}


AS_IS_MARKERS = {'AS-IS', 'As-Is', 'as-is', 'AS IS', 'As Is'}
TO_BE_MARKERS = {'To', '-Be', 'To -Be', 'TO-BE', 'To-Be', 'to-be', 'To Be', 'TO BE'}


def _extract_shape_text(shape):
    return ''.join([t.text or '' for t in shape.findall('.//a:t', namespaces=PPTX_NS)])


def _set_shape_text(shape, text):
    if shape is None:
        return

    tx_body = shape.find('p:txBody', namespaces=PPTX_NS)
    if tx_body is None:
        return

    for paragraph in list(tx_body.findall('a:p', namespaces=PPTX_NS)):
        tx_body.remove(paragraph)

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        lines = ['']

    for line in lines:
        a_p = etree.SubElement(tx_body, f'{{{PPTX_NS["a"]}}}p')
        a_r = etree.SubElement(a_p, f'{{{PPTX_NS["a"]}}}r')
        r_pr = etree.SubElement(a_r, f'{{{PPTX_NS["a"]}}}rPr')
        r_pr.set('lang', 'es-ES')
        r_pr.set('sz', '900')
        a_t = etree.SubElement(a_r, f'{{{PPTX_NS["a"]}}}t')
        a_t.text = line


def _find_previous_body_shape(shapes, current_index):
    for idx in range(current_index - 1, -1, -1):
        candidate = shapes[idx]
        name_elem = candidate.find('.//p:cNvPr', namespaces=PPTX_NS)
        name = name_elem.get('name', '') if name_elem is not None else ''
        text = _extract_shape_text(candidate).strip()
        if not text:
            continue
        if 'Rectángulo' in name or 'Redondear rectángulo' in name:
            if len(text) > 20 and text not in {'AS-IS', 'To', '-Be', 'To -Be', 'TO-BE', 'To-Be'}:
                return candidate
    return None


def _build_pptx_bytes(files):
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as zout:
        for name, data in files.items():
            zout.writestr(name, data)
    return out.getvalue()


def edit(pptx_bytes, config, catalog_data=None):
    as_is_text = str(config.get('as_is_text', '') or '').strip()
    to_be_text = str(config.get('to_be_text', '') or '').strip()
    if not as_is_text and not to_be_text:
        return pptx_bytes

    with zipfile.ZipFile(io.BytesIO(pptx_bytes), 'r') as zin:
        files = {name: zin.read(name) for name in zin.namelist()}

    slide_path = 'ppt/slides/slide4.xml'
    if slide_path not in files:
        return pptx_bytes

    root = etree.fromstring(files[slide_path])
    shapes = root.findall('.//p:sp', namespaces=PPTX_NS)

    for index, shape in enumerate(shapes):
        text = _extract_shape_text(shape).strip()
        if text in AS_IS_MARKERS:
            target = _find_previous_body_shape(shapes, index)
            _set_shape_text(target, as_is_text)
        elif text in TO_BE_MARKERS:
            target = _find_previous_body_shape(shapes, index)
            _set_shape_text(target, to_be_text)

    files[slide_path] = etree.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True)
    return _build_pptx_bytes(files)
