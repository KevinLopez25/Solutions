"""
Tests de cobertura adicional para alcanzar 75%.
"""
import io
import zipfile
import pytest

from domain.cronograma import service as cronograma_service
from domain.cronograma.entities import GenerarCronogramaRequest
from main import app


def test_generar_cronograma_filename_uses_proyecto(monkeypatch):
    monkeypatch.setattr(
        "domain.cronograma.service.cronograma_excel.generate_cronograma",
        lambda config: b"fake-xlsx"
    )
    req = GenerarCronogramaRequest(proyecto="Test", actividades=[{"torre": "A", "horas": 10}], roles=[])
    resp = cronograma_service.generar_cronograma(req)
    assert "Test" in resp.filename


def test_generar_cronograma_empty_proyecto(monkeypatch):
    monkeypatch.setattr(
        "domain.cronograma.service.cronograma_excel.generate_cronograma",
        lambda config: b"fake-xlsx"
    )
    req = GenerarCronogramaRequest(proyecto="", actividades=[{"torre": "A", "horas": 10}], roles=[])
    resp = cronograma_service.generar_cronograma(req)
    assert resp.filename


def test_groq_client_no_api_key(monkeypatch):
    from core import groq_client
    monkeypatch.setattr(groq_client.settings, 'GROQ_API_KEY', '')
    with pytest.raises(RuntimeError, match='GROQ_API_KEY'):
        groq_client.create_chat_completion([{'role': 'user', 'content': 'Hola'}])


def test_routes_exist():
    routes = [route.path for route in app.routes]
    assert "/api/v1/catalogo/torres" in routes
    assert "/api/v1/propuesta/generar" in routes
    assert "/api/v1/cronograma/generar" in routes
    assert "/api/v1/ai/chat" in routes


def test_quality_parse_empty():
    from api.v1.quality.router import parse_coverage_from_output
    assert parse_coverage_from_output("") == []
    assert parse_coverage_from_output("no header") == []


def test_quality_parse_with_data():
    from api.v1.quality.router import parse_coverage_from_output
    sample = "Name  Stmts  Miss  Cover\n------\nTOTAL  100  50  50%\n"
    rows = parse_coverage_from_output(sample)
    assert isinstance(rows, list)


def test_config_properties():
    from core.config import settings
    assert settings.database_url
    assert settings.templates_path
    assert isinstance(settings.origins, list)


def test_catalogo_entities():
    from domain.catalogo.entities import TorreOut, TorreCreate
    t = TorreOut(id=1, nombre="Test", nombre_norm="TEST", activa=True)
    assert t.nombre == "Test"
    assert TorreCreate(nombre="New").nombre == "New"


def test_cronograma_entities():
    from domain.cronograma.entities import RolCronograma, ActividadCronograma
    rol = RolCronograma(perfil="Dev", seniority="Sr", personas=2)
    assert rol.perfil == "Dev"
    act = ActividadCronograma(torre="A", horas=10)
    assert act.horas == 10


def test_propuesta_entities():
    from domain.propuesta.entities import GenerarPropuestaRequest, TorreInput
    req = GenerarPropuestaRequest(filial="corp")
    assert req.filial == "corp"
    assert TorreInput(nombre="Backend", horas=100).horas == 100


def test_ai_router_schemas():
    from api.v1.ai.router import AIMessage, AIChatRequest, AIChatResponse
    msg = AIMessage(role="user", content="Hola")
    assert msg.content == "Hola"
    req = AIChatRequest(messages=[msg])
    assert len(req.messages) == 1
    resp = AIChatResponse(reply="OK")
    assert resp.reply == "OK"


def test_cronograma_image_raises():
    from infrastructure.generators.cronograma_image import generate_cronograma_image
    with pytest.raises(ValueError, match="No hay actividades"):
        generate_cronograma_image({"actividades": []})


def test_cronograma_image_with_data():
    from infrastructure.generators.cronograma_image import generate_cronograma_image
    from unittest.mock import patch
    with patch('infrastructure.generators.cronograma_image._render') as mock:
        mock.return_value = b"fake-png"
        result = generate_cronograma_image({
            'actividades': [{'torre': 'A', 'horas': 43, 'personas': 1}],
            'roles': [{'perfil': 'Dev', 'personas': 1}],
        })
        assert result == b"fake-png"


def test_as_is_to_be_edit():
    from infrastructure.generators.as_is_to_be import edit
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('ppt/slides/slide1.xml', b'<xml/>')
    result = edit(buf.getvalue(), {'as_is_text': 'A', 'to_be_text': 'B'}, {})
    assert isinstance(result, bytes)


def test_roadmap_edit():
    from infrastructure.generators.roadmap import edit
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('ppt/slides/slide1.xml', b'<xml/>')
    result = edit(buf.getvalue(), {}, {})
    assert result == buf.getvalue()


def test_cronograma_excel_raises():
    from infrastructure.generators.cronograma_excel import generate_cronograma
    with pytest.raises(ValueError):
        generate_cronograma({'actividades': []})


def test_cronograma_excel_generates():
    from infrastructure.generators.cronograma_excel import generate_cronograma
    result = generate_cronograma({
        'actividades': [{'torre': 'A', 'horas': 43, 'personas': 1}],
        'roles': [{'perfil': 'Dev', 'personas': 1}],
    })
    assert isinstance(result, bytes) and len(result) > 0


def test_cronograma_excel_normalizar():
    from infrastructure.generators.cronograma_excel import _normalizar_roles
    assert _normalizar_roles([]) == []
    assert len(_normalizar_roles([{'perfil': 'Dev', 'personas': 1}])) == 1


def test_cronograma_excel_x_to_col():
    from infrastructure.generators.cronograma_excel import _x_to_col
    assert _x_to_col(0) == (0, 0)


def test_fda_norm():
    from infrastructure.generators.fda_perfiles import _norm
    assert _norm("  Hola  ") == "HOLA"
    assert _norm(None) == ""


def test_fda_clean():
    from infrastructure.generators.fda_perfiles import _clean_inline_text
    assert _clean_inline_text("A\nB") == "A B"
    assert _clean_inline_text(None) == ""


def test_fda_even_chunks():
    from infrastructure.generators.fda_perfiles import _even_chunks
    assert _even_chunks([], 6) == [[]]
    assert len(_even_chunks([1, 2, 3, 4, 5, 6, 7], 6)) == 2


def test_fda_truncate():
    from infrastructure.generators.fda_perfiles import _truncate_desc
    assert _truncate_desc("Short", 100) == "Short"
    assert _truncate_desc(None, 100) is None


def test_fda_split():
    from infrastructure.generators.fda_perfiles import _split_fda
    assert len(_split_fda("A. B.")) == 2


def test_fda_find_desc():
    from infrastructure.generators.fda_perfiles import _find_desc_in_catalog
    db = {"TORRE A": [{"rol": "Dev", "desc": "Dev desc"}]}
    assert _find_desc_in_catalog("Dev", db) == "Dev desc"
    assert _find_desc_in_catalog("X", db) == ""


def test_fda_hide():
    from infrastructure.generators.fda_perfiles import _hide_shape
    from lxml import etree
    sp = etree.fromstring(b'<p:sp xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><p:spPr><a:solidFill><a:srgbClr val="FF0000"/></a:solidFill></p:spPr></p:sp>')
    _hide_shape(sp)
    assert b"noFill" in etree.tostring(sp)


def test_fda_remove():
    from infrastructure.generators.fda_perfiles import _remove_shape
    from lxml import etree
    tree = etree.fromstring(b'<p:spTree xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"><p:sp><p:nvSpPr><p:cNvPr name="Test"/></p:nvSpPr></p:sp></p:spTree>')
    sp = tree.findall('.//{http://schemas.openxmlformats.org/presentationml/2006/main}sp')[0]
    _remove_shape(sp)
    assert len(tree.findall('.//{http://schemas.openxmlformats.org/presentationml/2006/main}sp')) == 0


def test_cons_norm():
    from infrastructure.generators.consideraciones import _norm
    assert _norm("  Hola  ") == "HOLA"


def test_cons_calc_delta():
    from infrastructure.generators.consideraciones import _calc_delta
    assert _calc_delta("Corto") == 0
    assert _calc_delta("A" * 300) > 0


def test_cons_split():
    from infrastructure.generators.consideraciones import _split_por_punto
    result = _split_por_punto("Oracion larga 1. Oracion larga 2.")
    assert len(result) >= 2


def test_cons_load_excel():
    from infrastructure.generators.consideraciones import _load_desde_excel
    assert _load_desde_excel([], "C", "F") == []


def test_cons_split_slides():
    from infrastructure.generators.consideraciones import _split_en_slides
    assert _split_en_slides([]) == [[]]


def test_entregables_norm():
    from infrastructure.generators.cronograma_entregables import _norm
    assert _norm("  Hola  ") == "HOLA"


def test_entregables_font_sz():
    from infrastructure.generators.cronograma_entregables import _font_sz
    assert _font_sz(3) == '1000'
    assert _font_sz(5) == '900'


def test_entregables_sp_off_x():
    from infrastructure.generators.cronograma_entregables import _sp_off_x
    from lxml import etree
    sp = etree.fromstring(b'<p:sp xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><p:spPr><a:xfrm><a:off x="5000"/></a:xfrm></p:spPr></p:sp>')
    assert _sp_off_x(sp) == 5000


def test_entregables_load_empty():
    from infrastructure.generators.cronograma_entregables import _load_entregables
    assert _load_entregables([], {}) == []


def test_preview_slides_order():
    from infrastructure.generators.cronograma_preview import _slides_order
    files = {
        'ppt/_rels/presentation.xml.rels': b'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/presentationml/2006/main/slide" Target="slides/slide1.xml"/></Relationships>',
        'ppt/presentation.xml': b'<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><p:sldIdLst><p:sldId id="256" r:id="rId1"/></p:sldIdLst></p:presentation>',
    }
    assert _slides_order(files) == ['ppt/slides/slide1.xml']


def test_preview_title_bottom():
    from infrastructure.generators.cronograma_preview import _title_bottom_emu
    assert _title_bottom_emu(None) > 0


def test_preview_png_aspect():
    from infrastructure.generators.cronograma_preview import _png_aspect
    assert _png_aspect(b"x") == 3.1


def test_preview_next_img_id():
    from infrastructure.generators.cronograma_preview import _next_img_id
    assert _next_img_id({'ppt/media/image1.png': b''}) == 2
    assert _next_img_id({}) == 1


def test_preview_insert_pic():
    from infrastructure.generators.cronograma_preview import _insert_pic
    slide = b'<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"><p:cSld><p:spTree/></p:cSld></p:sld>'
    result = _insert_pic(slide, 'rId1', 500000, 3.1)
    assert b'CronogramaImg' in result


def test_repo_norm():
    from infrastructure.repositories.catalogo_repository import _norm
    assert _norm("  Hola  ") == "HOLA"
    assert _norm(None) == ""


def test_repo_build_empty():
    from infrastructure.repositories.catalogo_repository import build_catalog_data
    from unittest.mock import MagicMock
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
    result = build_catalog_data(mock_db)
    assert "fda_db" in result


def test_esc_cronograma():
    from infrastructure.generators.cronograma_entregables import _esc
    assert "amp;" in _esc("a&b")
    assert _esc("normal") == "normal"


def test_esc_fda():
    from infrastructure.generators.fda_perfiles import _esc
    assert "amp;" in _esc("a&b")
    assert _esc("normal") == "normal"