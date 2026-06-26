import base64
import io
import json
import zipfile

import pytest

from domain.ai import service as ai_service


def _build_minimal_pptx_xml(text: str) -> bytes:
    xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
        'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
        '<p:cSld><p:spTree><p:sp><a:txBody><a:p><a:r><a:t>'
        f'{text}'
        '</a:t></a:r></a:p></a:txBody></p:sp></p:spTree></p:cSld></p:sld>'
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zout:
        zout.writestr('ppt/slides/slide1.xml', xml.encode('utf-8'))
    return buf.getvalue()


def test_find_json_object_extracts_json_from_text():
    value = ai_service._find_json_object('prefix {"foo": "bar"} suffix')

    assert value == {'foo': 'bar'}


def test_build_developer_prefix_replacements():
    extracted_text = 'java\nPython\nDesarrollador Go\n'
    replacements = ai_service._build_developer_prefix_replacements(extracted_text)

    assert {'from': 'java', 'to': 'Desarrollador java', 'exact': True} in replacements
    assert {'from': 'Python', 'to': 'Desarrollador Python', 'exact': True} in replacements
    assert all(r['from'] != 'Desarrollador Go' for r in replacements)


def test_apply_replacements_to_pptx_replaces_exact_paragraph():
    pptx = _build_minimal_pptx_xml('java')
    replacements = [{'from': 'java', 'to': 'Desarrollador java', 'exact': True}]

    modified = ai_service._apply_replacements_to_pptx(pptx, replacements)

    with zipfile.ZipFile(io.BytesIO(modified)) as z:
        slide_xml = z.read('ppt/slides/slide1.xml').decode('utf-8')

    assert 'Desarrollador java' in slide_xml


def test_chat_with_proposal_correction_path_applies_prefix():
    pptx = _build_minimal_pptx_xml('java')
    content_b64 = base64.b64encode(pptx).decode()
    messages = [{'role': 'user', 'content': 'Corrige los perfiles del PPTX'}]

    reply, modified_bytes = ai_service.chat_with_proposal(messages, base64.b64decode(content_b64))

    assert 'Corregí' in reply
    assert modified_bytes is not None
    with zipfile.ZipFile(io.BytesIO(modified_bytes)) as z:
        slide_xml = z.read('ppt/slides/slide1.xml').decode('utf-8')
    assert 'Desarrollador java' in slide_xml


def test_generate_as_is_to_be_uses_model_reply(monkeypatch):
    monkeypatch.setattr(ai_service, 'create_chat_completion', lambda conversation, max_tokens=512: '{"as_is":"Actual","to_be":"Futuro"}')

    as_is, to_be = ai_service.generate_as_is_to_be({'cliente': 'ACME'}, 'Estado actual')

    assert as_is == 'Actual'
    assert to_be == 'Futuro'


def test_generate_as_is_to_be_requires_description():
    with pytest.raises(ValueError, match='Descripción de AS-IS requerida'):
        ai_service.generate_as_is_to_be({}, '')


def test_generate_roadmap_phases_returns_four_phases(monkeypatch):
    response = '{"phases":[{"title":"Analizar","highlight":"Revisión","description":"Analiza requisitos."},'
    response += '{"title":"Diseñar","highlight":"Arquitectura","description":"Define solución."},'
    response += '{"title":"Construir","highlight":"Desarrollo","description":"Implementa módulos."},'
    response += '{"title":"Probar","highlight":"Validación","description":"Ejecuta pruebas."}]}'

    monkeypatch.setattr(ai_service, 'create_chat_completion', lambda conversation, max_tokens=512: response)

    phases = ai_service.generate_roadmap_phases({'proyecto': 'Demo', 'cliente': 'ACME'})

    assert len(phases) == 4
    assert phases[0]['title'] == 'Analizar'


def _build_pptx_with_slide1(slide_xml, rels_xml, media_files=None):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zout:
        zout.writestr('ppt/slides/slide1.xml', slide_xml.encode('utf-8'))
        zout.writestr('ppt/slides/_rels/slide1.xml.rels', rels_xml.encode('utf-8'))
        for name, data in (media_files or {}).items():
            zout.writestr(name, data)
    return buf.getvalue()


def test_replace_logo_in_pptx_replaces_picture_within_logo_area():
    slide_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
        'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<p:cSld><p:spTree>'
        '<p:sp><p:nvSpPr><p:cNvPr id="1" name="Rectángulo redondeado 1"/></p:nvSpPr>'
        '<p:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="1000000" cy="1000000"/></a:xfrm></p:spPr>'
        '</p:sp>'
        '<p:pic><p:nvPicPr><p:cNvPr id="2" name="Logo imagen"/></p:nvPicPr>'
        '<p:blipFill><a:blip r:embed="rId1"/></p:blipFill>'
        '<p:spPr><a:xfrm><a:off x="100" y="100"/><a:ext cx="100" cy="100"/></a:xfrm></p:spPr>'
        '</p:pic>'
        '</p:spTree></p:cSld></p:sld>'
    )
    rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="../media/logo.png"/>'
        '</Relationships>'
    )
    pptx = _build_pptx_with_slide1(slide_xml, rels_xml, {'ppt/media/logo.png': b'old-logo'})

    updated = ai_service.replace_logo_in_pptx(pptx, b'new-logo', 'image/png')

    with zipfile.ZipFile(io.BytesIO(updated)) as z:
        assert z.read('ppt/media/logo.png') == b'new-logo'


def test_replace_logo_in_pptx_adds_media_and_relationship_when_no_picture():
    slide_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
        'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<p:cSld><p:spTree>'
        '<p:sp><p:nvSpPr><p:cNvPr id="1" name="Rectángulo redondeado logo"/></p:nvSpPr>'
        '<p:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="1000000" cy="1000000"/></a:xfrm></p:spPr>'
        '</p:sp>'
        '</p:spTree></p:cSld></p:sld>'
    )
    rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>'
    )
    pptx = _build_pptx_with_slide1(slide_xml, rels_xml)

    updated = ai_service.replace_logo_in_pptx(pptx, b'fallback-logo', 'image/png')

    with zipfile.ZipFile(io.BytesIO(updated)) as z:
        assert z.read('ppt/media/logo_custom.png') == b'fallback-logo'
        rels = z.read('ppt/slides/_rels/slide1.xml.rels').decode('utf-8')
        assert 'Target="../media/logo_custom.png"' in rels


def test_review_and_modify_proposal_applies_replacements(monkeypatch):
    pptx = _build_minimal_pptx_xml('java')
    content_b64 = base64.b64encode(pptx).decode()

    monkeypatch.setattr(ai_service, 'create_chat_completion', lambda conversation, max_tokens=4096: '{"replacements": [{"from": "java", "to": "Dev java"}]}')

    reply, modified_b64 = ai_service.review_and_modify_proposal([], content_b64, 'Corrige los perfiles')

    assert 'replacements' in reply
    assert modified_b64 is not None
    modified = base64.b64decode(modified_b64)
    with zipfile.ZipFile(io.BytesIO(modified)) as z:
        slide_xml = z.read('ppt/slides/slide1.xml').decode('utf-8')
    assert 'Dev java' in slide_xml


def test_review_and_modify_proposal_raises_for_invalid_json(monkeypatch):
    pptx = _build_minimal_pptx_xml('java')
    content_b64 = base64.b64encode(pptx).decode()

    monkeypatch.setattr(ai_service, 'create_chat_completion', lambda conversation, max_tokens=4096: 'no json')

    with pytest.raises(RuntimeError, match='No se pudo interpretar la respuesta de IA como JSON'):
        ai_service.review_and_modify_proposal([], content_b64, 'Corrige los perfiles')


def test_generate_as_is_to_be_raises_when_response_missing_fields(monkeypatch):
    monkeypatch.setattr(ai_service, 'create_chat_completion', lambda conversation, max_tokens=512: '{"as_is": "", "to_be": ""}')

    with pytest.raises(RuntimeError, match='La IA no devolvió AS-IS y TO-BE válidos'):
        ai_service.generate_as_is_to_be({'cliente': 'ACME'}, 'Estado actual')


def test_generate_roadmap_phases_raises_when_incomplete_response(monkeypatch):
    monkeypatch.setattr(ai_service, 'create_chat_completion', lambda conversation, max_tokens=512: '{"phases": [{"title": "Analizar", "highlight": "", "description": ""}, {"title": "", "highlight": "", "description": ""}, {"title": "", "highlight": "", "description": ""}, {"title": "", "highlight": "", "description": ""}]}')

    with pytest.raises(RuntimeError, match='La IA devolvió fases de roadmap con campos incompletos'):
        ai_service.generate_roadmap_phases({'proyecto': 'Demo'})


def test_find_json_object_raises_when_json_unparseable():
    with pytest.raises(json.JSONDecodeError):
        ai_service._find_json_object('no json here')


def test_extract_pptx_text_returns_paragraphs_from_slides():
    xml1 = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
            'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
            '<p:cSld><p:spTree><p:sp><a:txBody><a:p><a:r><a:t>Hola</a:t></a:r></a:p></a:txBody></p:sp></p:spTree></p:cSld></p:sld>')
    xml2 = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
            'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
            '<p:cSld><p:spTree><p:sp><a:txBody><a:p><a:r><a:t>Mundo</a:t></a:r></a:p></a:txBody></p:sp></p:spTree></p:cSld></p:sld>')
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zout:
        zout.writestr('ppt/slides/slide1.xml', xml1.encode('utf-8'))
        zout.writestr('ppt/slides/slide2.xml', xml2.encode('utf-8'))

    extracted = ai_service._extract_pptx_text(buf.getvalue())

    assert 'Slide 1:' in extracted
    assert 'Hola' in extracted
    assert 'Slide 2:' in extracted
    assert 'Mundo' in extracted


def test_is_correction_request_detects_profile_correction():
    messages = [{'role': 'user', 'content': 'Por favor corrige los perfiles del PPTX'}]
    assert ai_service._is_correction_request(messages)


def test_is_correction_request_returns_false_for_irrelevant_message():
    messages = [{'role': 'user', 'content': '¿Cuál es el estado del proyecto?'}]
    assert not ai_service._is_correction_request(messages)


def test_build_excel_context_formats_full_excel_data():
    context = ai_service._build_excel_context({
        'cliente': 'ACME',
        'proyecto': 'Demo',
        'filename': 'estimacion.xlsx',
        'torres': [{'nombre': 'IA', 'horas': 10, 'personas': 2}],
        'perfiles': [{'perfil': 'java', 'torre': 'IA'}],
        'entregables': [{'torre': 'IA', 'items': ['Entregable1', 'Entregable2']}],
        'consideraciones': ['Nota 1'],
        'fda': ['FDA 1'],
    })

    assert 'Cliente: ACME' in context
    assert 'Proyecto: Demo' in context
    assert 'Torres: 1 torres, 10 horas totales.' in context
    assert '- java (IA)' in context
    assert 'Entregables: 1 grupos.' in context
    assert 'Consideraciones: Nota 1' in context
    assert 'FDA: FDA 1' in context


def test_build_roadmap_context_formats_full_data():
    context = ai_service._build_roadmap_context({
        'proyecto': 'Demo',
        'cliente': 'ACME',
        'torres': [{'nombre': 'IA', 'horas': 20, 'personas': 2}],
        'perfiles': [{'perfil': 'python', 'torre': 'IA'}],
        'entregables': [{'torre': 'IA', 'items': ['Entregable1']}],
        'consideraciones': ['Nota 1'],
        'fda': ['FDA 1'],
    })

    assert 'Proyecto: Demo' in context
    assert 'Cliente: ACME' in context
    assert 'Torres o áreas: 1' in context
    assert '- IA: 20 hrs, 2 personas' in context
    assert 'Perfiles: 1 roles.' in context
    assert 'Entregables: 1 grupos.' in context


def test_clean_roadmap_phase_strips_empty_values():
    cleaned = ai_service._clean_roadmap_phase({
        'title': '  ',
        'highlight': None,
        'description': ' Desc ',
    })

    assert cleaned == {'title': '', 'highlight': '', 'description': 'Desc'}


def test_generate_as_is_to_be_raises_on_missing_description():
    with pytest.raises(ValueError, match='Descripción de AS-IS requerida'):
        ai_service.generate_as_is_to_be({'cliente': 'ACME'}, '')


def test_generate_roadmap_phases_raises_on_invalid_response(monkeypatch):
    monkeypatch.setattr(ai_service, 'create_chat_completion', lambda conversation, max_tokens=512: '{"phases": []}')

    with pytest.raises(RuntimeError, match='La IA no devolvió un roadmap válido de 4 fases'):
        ai_service.generate_roadmap_phases({'proyecto': 'Demo'})


def test_chat_with_proposal_passes_to_ai_when_not_correction(monkeypatch):
    pptx = _build_minimal_pptx_xml('java')
    monkeypatch.setattr(ai_service, 'create_chat_completion', lambda conv, max_tokens=600: 'OK respuesta')

    reply, modified = ai_service.chat_with_proposal([{'role': 'user', 'content': '¿Qué dice el PPTX?'}], pptx)

    assert reply == 'OK respuesta'
    assert modified is None
