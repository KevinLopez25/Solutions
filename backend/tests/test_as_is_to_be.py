import io
import zipfile

from lxml import etree

from infrastructure.generators import as_is_to_be


def _build_pptx(files):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zout:
        for name, data in files.items():
            zout.writestr(name, data)
    return buf.getvalue()


def test_edit_returns_same_bytes_if_slide_missing():
    pptx = _build_pptx({'ppt/slides/slide1.xml': b'<xml/>'})
    updated = as_is_to_be.edit(pptx, {'as_is_text': 'Algo', 'to_be_text': 'Algo'})
    assert updated == pptx


def test_edit_sets_as_is_and_to_be_text():
    slide_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
        'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
        '<p:cSld><p:spTree>'
        '<p:sp><p:nvSpPr><p:cNvPr id="1" name="Rectángulo cuerpo AS-IS"/></p:nvSpPr>'
        '<p:txBody><a:p><a:r><a:t>Texto largo que será reemplazado para AS-IS y contiene más de veinte caracteres.</a:t></a:r></a:p></p:txBody>'
        '</p:sp>'
        '<p:sp><p:nvSpPr><p:cNvPr id="2" name="AS-IS"/></p:nvSpPr><p:txBody><a:p><a:r><a:t>AS-IS</a:t></a:r></a:p></p:txBody></p:sp>'
        '<p:sp><p:nvSpPr><p:cNvPr id="3" name="Rectángulo cuerpo TO-BE"/></p:nvSpPr>'
        '<p:txBody><a:p><a:r><a:t>Otro texto largo que se reemplazará con TO-BE y también supera veinte caracteres.</a:t></a:r></a:p></p:txBody>'
        '</p:sp>'
        '<p:sp><p:nvSpPr><p:cNvPr id="4" name="TO-BE"/></p:nvSpPr><p:txBody><a:p><a:r><a:t>TO-BE</a:t></a:r></a:p></p:txBody></p:sp>'
        '</p:spTree></p:cSld></p:sld>'
    )
    pptx = _build_pptx({'ppt/slides/slide4.xml': slide_xml})

    updated = as_is_to_be.edit(
        pptx,
        {'as_is_text': 'Estado actual mejorado', 'to_be_text': 'Estado futuro optimizado'},
    )

    with zipfile.ZipFile(io.BytesIO(updated)) as z:
        slide = z.read('ppt/slides/slide4.xml').decode('utf-8')

    assert 'Estado actual mejorado' in slide
    assert 'Estado futuro optimizado' in slide
