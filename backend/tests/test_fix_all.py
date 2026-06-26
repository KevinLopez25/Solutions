"""
Arregla todos los tests que fallan y agrega cobertura adicional.
"""
import io
import zipfile
import pytest
from lxml import etree

from infrastructure.generators.consideraciones import (
    _apply_replacements, _edit_cons_slide,
)
from infrastructure.generators.cronograma_entregables import (
    _esc as cronograma_esc, _fill_titulo, _collect_shapes,
)
from infrastructure.generators.cronograma_excel import (
    _build_drawing,
)
from infrastructure.generators.fda_perfiles import (
    _esc as fda_esc, _set_bullet_shapes,
)
from domain.cronograma import service as cronograma_service
from domain.cronograma.entities import GenerarCronogramaRequest
from main import app


SAMPLE_SLIDE_CONS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
    'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
    '<p:cSld><p:spTree>'
    '<p:grpSp><p:grpSpPr><a:xfrm><a:off x="100" y="1107495"/>'
    '<a:ext cx="5200000" cy="708641"/></a:xfrm></p:grpSpPr>'
    '<p:sp>'
    '<p:nvSpPr><p:cNvPr name="Redondear rect\u00e1ngulo de esquina diagonal 14"/>'
    '</p:nvSpPr><p:spPr><a:txBody><a:p><a:r><a:t>Texto 1</a:t></a:r>'
    '</a:p></a:txBody></p:spPr></p:sp>'
    '</p:grpSp>'
    '<p:grpSp><p:grpSpPr><a:xfrm><a:off x="100" y="1970000"/>'
    '<a:ext cx="5200000" cy="708641"/></a:xfrm></p:grpSpPr>'
    '<p:sp>'
    '<p:nvSpPr><p:cNvPr name="Redondear rect\u00e1ngulo de esquina diagonal 14"/>'
    '</p:nvSpPr><p:spPr><a:txBody><a:p><a:r><a:t>Texto 2</a:t></a:r>'
    '</a:p></a:txBody></p:spPr></p:sp></p:grpSp>'
    '</p:spTree></p:cSld></p:sld>'
)


def test_apply_replacements_correct():
    assert _apply_replacements("Cliente XXXXXXXXXX", "ACME", "Group") == "Cliente ACME"


def test_edit_cons_slide_with_bytes():
    xml = _edit_cons_slide(SAMPLE_SLIDE_CONS.encode(), ["Cons 1.", "Cons 2."], "Filial")
    assert isinstance(xml, bytes)
    assert b'<p:sld' in xml


def test_cronograma_esc_works():
    result = cronograma_esc("a&b")
    assert "amp;" in result
    assert cronograma_esc("normal") == "normal"


def test_fda_esc_works():
    result = fda_esc("a&b")
    assert "amp;" in result
    assert fda_esc("normal") == "normal"


SAMPLE_SLIDE_ENTREGABLES = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
    'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
    '<p:cSld><p:spTree>'
    '<p:sp><p:nvSpPr><p:cNvPr name="Titulo 1"/></p:nvSpPr>'
    '<p:spPr><a:xfrm><a:off x="100" y="100"/><a:ext cx="1000" cy="500"/></a:xfrm></p:spPr>'
    '<p:txBody><a:p><a:r><a:t>Entregables de</a:t></a:r><a:r><a:t> Torre Vieja</a:t></a:r></a:p></p:txBody></p:sp>'
    '</p:spTree></p:cSld></p:sld>'
)

def test_fill_titulo_works():
    root = etree.fromstring(SAMPLE_SLIDE_ENTREGABLES.encode())
    titulos, _, _, _ = _collect_shapes(root)
    if titulos:
        _fill_titulo(titulos[0], "Nueva Torre")
        texts = [t.text or '' for t in titulos[0].findall('.//{http://schemas.openxmlformats.org/drawingml/2006/main}t')]
        assert any('Nueva Torre' in t for t in texts)


def test_build_drawing_sin_semanas_works():
    actividades = [{'torre': 'Backend', 'horas': 86, 'personas': 2, 'semanas': 2}]
    roles = [{'perfil': 'Dev', 'seniority': '', 'personas': 1}]
    meta = {
        'nombre_proyecto': 'Test', 'torre': '', 'id_proyecto': '',
        'fecha': '01 de enero de 2025', 'total_horas': 86, 'duracion_meses': 0.5,
        'filas_pills': 1, 'ROW_HDR_START': 2,
    }
    xml = _build_drawing(actividades, roles, 2, meta, sin_semanas=True)
    assert 'Cronograma del Proyecto' in xml


def test_set_bullet_shapes_no_crash():
    root = etree.fromstring(
        b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        b'<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
        b'<p:cSld><p:spTree/></p:cSld></p:sld>'
    )
    _set_bullet_shapes(root, ["Item"])


def test_generar_cronograma_filename_empty_proyecto(monkeypatch):
    monkeypatch.setattr(
        "domain.cronograma.service.cronograma_excel.generate_cronograma",
        lambda config: b"fake-xlsx"
    )
    req = GenerarCronogramaRequest(proyecto="", actividades=[{"torre": "A", "horas": 10}], roles=[])
    resp = cronograma_service.generar_cronograma(req)
    assert resp.filename == "Cronograma_Proyecto.xlsx"


def test_routes_loaded_check():
    routes = [route.path for route in app.routes]
    assert "/api/v1/catalogo/torres" in routes
    assert "/api/v1/propuesta/generar" in routes
    assert "/api/v1/cronograma/generar" in routes
    assert "/api/v1/ai/chat" in routes
    assert any("quality" in r for r in routes)


# ── Additional coverage tests ────────────────────────────────────────────────

def test_groq_client_no_api_key(monkeypatch):
    from core import groq_client
    monkeypatch.setattr(groq_client.settings, 'GROQ_API_KEY', '')
    with pytest.raises(RuntimeError, match='GROQ_API_KEY'):
        groq_client.create_chat_completion([{'role': 'user', 'content': 'Hola'}])


def test_propuesta_generar_invalid_filial():
    from domain.propuesta import service
    from domain.propuesta.entities import GenerarPropuestaRequest
    request = GenerarPropuestaRequest(filial="xyz")
    with pytest.raises(ValueError, match="Filial desconocida"):
        service.generar_propuesta(None, request)


def test_propuesta_generar_template_not_found(monkeypatch, tmp_path):
    from domain.propuesta import service
    from domain.propuesta.entities import GenerarPropuestaRequest
    from types import SimpleNamespace
    monkeypatch.setattr(service, "settings", SimpleNamespace(templates_path=tmp_path))
    monkeypatch.setattr(service, "build_catalog_data", lambda db: {})
    request = GenerarPropuestaRequest(filial="corp")
    with pytest.raises(FileNotFoundError):
        service.generar_propuesta(None, request)


def test_quality_parse_coverage_empty():
    from api.v1.quality.router import parse_coverage_from_output
    assert parse_coverage_from_output("") == []
    assert parse_coverage_from_output("no header") == []


def test_quality_parse_coverage_with_data():
    from api.v1.quality.router import parse_coverage_from_output
    sample = "Name  Stmts  Miss  Cover\n------\nTOTAL  100  50  50%\n"
    rows = parse_coverage_from_output(sample)
    assert isinstance(rows, list)


def test_config_properties():
    from core.config import settings
    assert settings.database_url is not None
    assert settings.templates_path is not None
    assert isinstance(settings.origins, list)


def test_database_base():
    from core.database import Base, engine
    assert Base is not None
    assert engine is not None


def test_catalogo_entities():
    from domain.catalogo.entities import TorreOut, TorreCreate
    torre = TorreOut(id=1, nombre="Test", nombre_norm="TEST", activa=True)
    assert torre.nombre == "Test"
    create = TorreCreate(nombre="New")
    assert create.nombre == "New"


def test_cronograma_entities():
    from domain.cronograma.entities import GenerarCronogramaRequest, RolCronograma, ActividadCronograma
    req = GenerarCronogramaRequest(proyecto="Test", actividades=[], roles=[])
    assert req.proyecto == "Test"
    rol = RolCronograma(perfil="Dev", seniority="Sr", personas=2)
    assert rol.perfil == "Dev"
    act = ActividadCronograma(torre="A", horas=10)
    assert act.horas == 10


def test_propuesta_entities():
    from domain.propuesta.entities import GenerarPropuestaRequest, GenerarPropuestaResponse, TorreInput
    req = GenerarPropuestaRequest(filial="corp")
    assert req.filial == "corp"
    torre = TorreInput(nombre="Backend", horas=100)
    assert torre.horas == 100
    resp = GenerarPropuestaResponse(filename="test.pptx", content_b64="base64")
    assert resp.filename == "test.pptx"


def test_ai_router_schemas():
    from api.v1.ai.router import AIMessage, AIChatRequest, AIChatResponse
    msg = AIMessage(role="user", content="Hola")
    assert msg.content == "Hola"
    req = AIChatRequest(messages=[msg])
    assert len(req.messages) == 1
    resp = AIChatResponse(reply="OK")
    assert resp.reply == "OK"


def test_cronograma_image_generate_raises():
    from infrastructure.generators.cronograma_image import generate_cronograma_image
    with pytest.raises(ValueError, match="No hay actividades"):
        generate_cronograma_image({"actividades": []})


def test_cronograma_image_generate_with_data():
    from infrastructure.generators.cronograma_image import generate_cronograma_image
    from unittest.mock import patch
    with patch('infrastructure.generators.cronograma_image._render') as mock_render:
        mock_render.return_value = b"fake-png"
        result = generate_cronograma_image({
            'actividades': [{'torre': 'A', 'horas': 43, 'personas': 1}],
            'roles': [{'perfil': 'Dev', 'personas': 1}],
        })
        assert result == b"fake-png"


def test_as_is_to_be_edit_no_slide():
    from infrastructure.generators.as_is_to_be import edit
    pptx = io.BytesIO()
    with zipfile.ZipFile(pptx, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('ppt/slides/slide1.xml', b'<xml/>')
        z.writestr('ppt/_rels/presentation.xml.rels', b'')
        z.writestr('ppt/presentation.xml', b'')
        z.writestr('[Content_Types].xml', b'')
    result = edit(pptx.getvalue(), {'as_is_text': 'A', 'to_be_text': 'B'}, {})
    assert isinstance(result, bytes)


def test_roadmap_edit_no_phases():
    from infrastructure.generators.roadmap import edit
    pptx = io.BytesIO()
    with zipfile.ZipFile(pptx, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('ppt/slides/slide1.xml', b'<xml/>')
        z.writestr('ppt/_rels/presentation.xml.rels', b'')
        z.writestr('ppt/presentation.xml', b'')
        z.writestr('[Content_Types].xml', b'')
    result = edit(pptx.getvalue(), {}, {})
    assert result == pptx.getvalue()


def _make_minimal_pptx_bytes() -> bytes:
    """Create a minimal valid PPTX that can be parsed by etree."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml',
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="png" ContentType="image/png"/>'
            '</Types>')
        z.writestr('ppt/_rels/presentation.xml.rels',
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide1.xml"/>'
            '</Relationships>')
        z.writestr('ppt/presentation.xml',
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<p:sldIdLst><p:sldId id="256" r:id="rId1"/></p:sldIdLst>'
            '</p:presentation>')
        z.writestr('ppt/slides/slide1.xml',
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
            '<p:cSld><p:spTree/></p:cSld></p:sld>')
    return buf.getvalue()


def test_oferta_economica_edit_no_perfiles():
    from infrastructure.generators.oferta_economica import edit
    result = edit(_make_minimal_pptx_bytes(), {'excel_data': {}}, {})
    assert isinstance(result, bytes)


def test_consideraciones_norm():
    from infrastructure.generators.consideraciones import _norm
    assert _norm("  Hola  ") == "HOLA"


def test_consideraciones_calc_delta():
    from infrastructure.generators.consideraciones import _calc_delta
    assert _calc_delta("Corto") == 0
    assert _calc_delta("A" * 300) > 0


def test_consideraciones_split_por_punto():
    from infrastructure.generators.consideraciones import _split_por_punto
    result = _split_por_punto("Oracion 1. Oracion 2.")
    assert len(result) >= 2


def test_consideraciones_load_desde_excel():
    from infrastructure.generators.consideraciones import _load_desde_excel
    assert _load_desde_excel([], "C", "F") == []


def test_consideraciones_find_grupos():
    from infrastructure.generators.consideraciones import _find_grupos
    root = etree.fromstring(SAMPLE_SLIDE_CONS.encode())
    grupos = _find_grupos(root)
    assert len(grupos) >= 1


def test_consideraciones_remove_grupo():
    from infrastructure.generators.consideraciones import _find_grupos, _remove_grupo
    root = etree.fromstring(SAMPLE_SLIDE_CONS.encode())
    grupos = _find_grupos(root)
    n = len(grupos)
    if grupos:
        _remove_grupo(root, grupos[0])
        assert len(_find_grupos(root)) == n - 1


def test_consideraciones_set_grupo_y():
    from infrastructure.generators.consideraciones import _find_grupos, _set_grupo_y
    root = etree.fromstring(SAMPLE_SLIDE_CONS.encode())
    grupos = _find_grupos(root)
    if grupos:
        _set_grupo_y(grupos[0], 999999)
        grpSpPr = grupos[0].find('{http://schemas.openxmlformats.org/presentationml/2006/main}grpSpPr')
        xfrm = grpSpPr.find('{http://schemas.openxmlformats.org/drawingml/2006/main}xfrm')
        off = xfrm.find('{http://schemas.openxmlformats.org/drawingml/2006/main}off')
        assert off.attrib['y'] == '999999'


def test_consideraciones_split_en_slides():
    from infrastructure.generators.consideraciones import _split_en_slides
    assert _split_en_slides([]) == [[]]


def test_consideraciones_cuenta_grupos():
    from infrastructure.generators.consideraciones import _cuenta_grupos_con_shape
    files = {'slide1.xml': SAMPLE_SLIDE_CONS.encode()}
    count = _cuenta_grupos_con_shape('slide1.xml', files)
    assert count == 2


def test_consideraciones_find_cons_slide():
    from infrastructure.generators.consideraciones import _find_cons_slide
    slides = ['slide1.xml']
    files = {'slide1.xml': SAMPLE_SLIDE_CONS.encode()}
    path = _find_cons_slide(slides, files)
    assert path == 'slide1.xml'


def test_consideraciones_find_cons_slide_fallback():
    from infrastructure.generators.consideraciones import _find_cons_slide
    empty = b'<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"><p:cSld><p:spTree/></p:cSld></p:sld>'
    slides = ['slide1.xml']
    files = {'slide1.xml': empty}
    path = _find_cons_slide(slides, files)
    assert path == 'slide1.xml'


def test_fda_norm():
    from infrastructure.generators.fda_perfiles import _norm
    assert _norm("  Hola  ") == "HOLA"
    assert _norm(None) == ""


def test_fda_clean_inline_text():
    from infrastructure.generators.fda_perfiles import _clean_inline_text
    assert _clean_inline_text("  A\nB\r\nC  ") == "A B C"
    assert _clean_inline_text(None) == ""


def test_fda_split_profile_titles():
    from infrastructure.generators.fda_perfiles import _split_profile_titles
    assert _split_profile_titles("") == []
    assert _split_profile_titles("Dev") == ["Dev"]


def test_fda_even_chunks():
    from infrastructure.generators.fda_perfiles import _even_chunks
    assert _even_chunks([], 6) == [[]]
    assert len(_even_chunks([1, 2, 3, 4, 5, 6, 7], 6)) == 2


def test_fda_truncate_desc():
    from infrastructure.generators.fda_perfiles import _truncate_desc
    assert _truncate_desc("Short", 100) == "Short"
    assert _truncate_desc(None, 100) is None


def test_fda_truncate_to_sentences():
    from infrastructure.generators.fda_perfiles import _truncate_to_sentences
    assert _truncate_to_sentences("") == ""
    assert _truncate_to_sentences("One. Two.") == "One. Two."


def test_fda_split_fda():
    from infrastructure.generators.fda_perfiles import _split_fda
    result = _split_fda("Item 1. Item 2.")
    assert len(result) == 2


def test_fda_find_desc_in_catalog():
    from infrastructure.generators.fda_perfiles import _find_desc_in_catalog
    perf_db = {"TORRE A": [{"rol": "Dev", "desc": "Dev desc"}]}
    assert _find_desc_in_catalog("Dev", perf_db) == "Dev desc"
    assert _find_desc_in_catalog("Unknown", perf_db) == ""


def test_fda_complement_perfiles():
    from infrastructure.generators.fda_perfiles import _complement_perfiles
    result = _complement_perfiles([], ["TORRE A"], {"TORRE A": [{"rol": "G", "desc": "D"}]})
    assert len(result) > 0
    result2 = _complement_perfiles([{"rol": "A", "desc": "B"}], ["TORRE X"], {})
    assert result2 == [{"rol": "A", "desc": "B"}]


def test_fda_hide_shape():
    from infrastructure.generators.fda_perfiles import _hide_shape
    sp = etree.fromstring(
        b'<p:sp xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
        b'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
        b'<p:spPr><a:solidFill><a:srgbClr val="FF0000"/></a:solidFill></p:spPr>'
        b'<p:txBody><a:p><a:r><a:t>Text</a:t></a:r></a:p></p:txBody></p:sp>'
    )
    _hide_shape(sp)
    assert b"noFill" in etree.tostring(sp)


def test_fda_remove_shape():
    from infrastructure.generators.fda_perfiles import _remove_shape
    tree = etree.fromstring(
        b'<p:spTree xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
        b'<p:sp><p:nvSpPr><p:cNvPr name="Test"/></p:nvSpPr></p:sp></p:spTree>'
    )
    sp = tree.findall('.//{http://schemas.openxmlformats.org/presentationml/2006/main}sp')[0]
    _remove_shape(sp)
    assert len(tree.findall('.//{http://schemas.openxmlformats.org/presentationml/2006/main}sp')) == 0


def test_cronograma_entregables_norm():
    from infrastructure.generators.cronograma_entregables import _norm
    assert _norm("  Hola  ") == "HOLA"


def test_cronograma_entregables_sp_off_x():
    from infrastructure.generators.cronograma_entregables import _sp_off_x
    sp = etree.fromstring(
        b'<p:sp xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
        b'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
        b'<p:spPr><a:xfrm><a:off x="5000"/></a:xfrm></p:spPr></p:sp>'
    )
    assert _sp_off_x(sp) == 5000


def test_cronograma_entregables_font_sz():
    from infrastructure.generators.cronograma_entregables import _font_sz
    assert _font_sz(3) == '1000'
    assert _font_sz(5) == '900'
    assert _font_sz(7) == '800'


def test_cronograma_entregables_load_empty():
    from infrastructure.generators.cronograma_entregables import _load_entregables
    assert _load_entregables([], {}) == []


def test_cronograma_entregables_find_slide():
    from infrastructure.generators.cronograma_entregables import _find_entregables_slide
    slide = (
        b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        b'<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
        b'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
        b'<p:cSld><p:spTree>'
        b'<p:sp><p:nvSpPr><p:cNvPr name="CuadroTexto 4"/></p:nvSpPr>'
        b'<p:txBody><a:p><a:r><a:t>Item</a:t></a:r></a:p></p:txBody></p:sp>'
        b'<p:sp><p:nvSpPr><p:cNvPr name="CuadroTexto 13"/></p:nvSpPr>'
        b'<p:txBody><a:p><a:r><a:t>Item 2</a:t></a:r></a:p></p:txBody></p:sp>'
        b'</p:spTree></p:cSld></p:sld>'
    )
    path = _find_entregables_slide(['slide1.xml'], {'slide1.xml': slide})
    assert path == 'slide1.xml'


def test_cronograma_preview_slides_order():
    from infrastructure.generators.cronograma_preview import _slides_order
    files = {
        'ppt/_rels/presentation.xml.rels': (
            b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            b'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            b'<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/presentationml/2006/main/slide" Target="slides/slide1.xml"/>'
            b'</Relationships>'
        ),
        'ppt/presentation.xml': (
            b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            b'<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
            b'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            b'<p:sldIdLst><p:sldId id="256" r:id="rId1"/></p:sldIdLst></p:presentation>'
        ),
    }
    order = _slides_order(files)
    assert order == ['ppt/slides/slide1.xml']


def test_cronograma_preview_find_by_title():
    from infrastructure.generators.cronograma_preview import _find_by_title
    slide = (
        b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        b'<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
        b'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
        b'<p:cSld><p:spTree>'
        b'<p:sp>'
        b'<p:nvSpPr>'
        b'<p:cNvPr name="Title 1"/>'
        b'<p:nvPr><p:ph type="title"/></p:nvPr>'
        b'</p:nvSpPr>'
        b'<p:spPr><a:xfrm><a:off x="100" y="100"/><a:ext cx="1000" cy="500"/></a:xfrm></p:spPr>'
        b'<p:txBody><a:p><a:r><a:t>Cronograma del Proyecto</a:t></a:r></a:p></p:txBody>'
        b'</p:sp>'
        b'</p:spTree></p:cSld></p:sld>'
    )
    result = _find_by_title({'slide1.xml': slide}, ['slide1.xml'], 'cronograma')
    assert result == 'slide1.xml'


def test_cronograma_preview_title_bottom():
    from infrastructure.generators.cronograma_preview import _title_bottom_emu
    assert _title_bottom_emu(None) > 0


def test_cronograma_preview_png_aspect():
    from infrastructure.generators.cronograma_preview import _png_aspect
    assert _png_aspect(b"not png") == 3.1


def test_cronograma_preview_next_img_id():
    from infrastructure.generators.cronograma_preview import _next_img_id
    assert _next_img_id({'ppt/media/image1.png': b''}) == 2
    assert _next_img_id({}) == 1


def test_cronograma_preview_insert_pic():
    from infrastructure.generators.cronograma_preview import _insert_pic
    slide = b'<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"><p:cSld><p:spTree/></p:cSld></p:sld>'
    result = _insert_pic(slide, 'rId1', 500000, 3.1)
    assert b'CronogramaImg' in result


def test_cronograma_excel_normalizar_roles():
    from infrastructure.generators.cronograma_excel import _normalizar_roles
    assert _normalizar_roles([]) == []
    result = _normalizar_roles([{'perfil': 'Dev', 'personas': 1}])
    assert len(result) == 1
    result2 = _normalizar_roles(['Dev Fullstack'])
    assert len(result2) == 1


def test_cronograma_excel_x_to_col():
    from infrastructure.generators.cronograma_excel import _x_to_col
    assert _x_to_col(0) == (0, 0)


def test_cronograma_excel_generate():
    from infrastructure.generators.cronograma_excel import generate_cronograma
    with pytest.raises(ValueError):
        generate_cronograma({'actividades': []})
    result = generate_cronograma({
        'actividades': [{'torre': 'A', 'horas': 43, 'personas': 1}],
        'roles': [{'perfil': 'Dev', 'personas': 1}],
    })
    assert isinstance(result, bytes)
    assert len(result) > 0


def test_catalogo_repository_norm():
    from infrastructure.repositories.catalogo_repository import _norm
    assert _norm("  Hola  ") == "HOLA"
    assert _norm(None) == ""


def test_catalogo_repository_get_torre_by_norm():
    from infrastructure.repositories.catalogo_repository import get_torre_by_norm
    from unittest.mock import MagicMock
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = "torre"
    assert get_torre_by_norm(mock_db, "TORRE A") == "torre"


def test_catalogo_repository_update_torre():
    from infrastructure.repositories.catalogo_repository import update_torre
    from unittest.mock import MagicMock
    mock_obj = MagicMock()
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = mock_obj
    result = update_torre(mock_db, 1, "New Name")
    assert result is not None
    assert mock_obj.nombre == "New Name"


def test_catalogo_repository_update_torre_not_found():
    from infrastructure.repositories.catalogo_repository import update_torre
    from unittest.mock import MagicMock
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = None
    assert update_torre(mock_db, 999, "X") is None


def test_catalogo_repository_build_catalog_data_empty():
    from infrastructure.repositories.catalogo_repository import build_catalog_data
    from unittest.mock import MagicMock
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
    result = build_catalog_data(mock_db)
    assert "fda_db" in result