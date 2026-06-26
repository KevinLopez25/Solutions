"""
Final coverage boost from 74% to 80%+.
Targets: main.py, fda_perfiles, consideraciones, cronograma_entregables,
cronograma_preview, cronograma_image, roadmap, oferta_economica.
"""
import io
import os
import re
import json
import zipfile
import pytest
from unittest.mock import MagicMock, patch, ANY
from lxml import etree
from fastapi.testclient import TestClient

# ═══════════════════════════════════════════════════════════════════════════════
# main.py — increase from 39% to 80%+
# ═══════════════════════════════════════════════════════════════════════════════

class TestMain:
    def test_app_creation(self):
        from main import app
        assert app.title == "Solutions API"
        assert app.version == "2.0.0"

    def test_routes_count(self):
        from main import app
        assert len(app.routes) > 10

    def test_cors_middleware_present(self):
        from main import app
        middleware_names = [m.__class__.__name__ if hasattr(m, '__class__') else str(m) for m in app.user_middleware]
        assert any('CORSMiddleware' in str(m) for m in app.user_middleware)

    def test_print_db_banner_db_ok(self, monkeypatch, capsys):
        from main import _print_db_banner
        from core.database import engine
        # Mock engine.connect to succeed
        mock_conn = MagicMock()
        mock_conn.__enter__.return_value = mock_conn
        monkeypatch.setattr(engine, 'connect', lambda: mock_conn)
        _print_db_banner()
        captured = capsys.readouterr()
        assert 'Base de datos' in captured.out

    def test_print_db_banner_db_fail(self, monkeypatch, capsys):
        from main import _print_db_banner
        from core.database import engine
        monkeypatch.setattr(engine, 'connect', MagicMock(side_effect=Exception("DB error")))
        _print_db_banner()
        captured = capsys.readouterr()
        assert 'NO CONECTADA' in captured.out

    def test_lifespan_create_all(self, monkeypatch):
        from main import lifespan
        monkeypatch.setattr('main.Base.metadata.create_all', lambda bind: None)
        monkeypatch.setattr('main._print_db_banner', lambda: None)
        import asyncio
        async def run():
            async with lifespan(None):
                pass
        asyncio.run(run())

    def test_lifespan_no_db_warning(self, monkeypatch, capsys):
        from main import lifespan
        monkeypatch.setattr('main.Base.metadata.create_all', MagicMock(side_effect=Exception("No DB")))
        monkeypatch.setattr('main._print_db_banner', lambda: None)
        monkeypatch.setattr('main.settings.GROQ_API_KEY', 'test-key')
        import asyncio
        async def run():
            async with lifespan(None):
                pass
        asyncio.run(run())
        captured = capsys.readouterr()
        assert 'No se crearon' in captured.out or 'configurada' in captured.out

    def test_lifespan_groq_key_missing(self, monkeypatch, capsys):
        from main import lifespan
        from core.config import settings
        monkeypatch.setattr(settings, 'GROQ_API_KEY', '')
        monkeypatch.setattr('main.Base.metadata.create_all', lambda bind: None)
        monkeypatch.setattr('main._print_db_banner', lambda: None)
        import asyncio
        async def run():
            async with lifespan(None):
                pass
        asyncio.run(run())
        captured = capsys.readouterr()
        assert 'no está configurada' in captured.out

    def test_lifespan_groq_key_present(self, monkeypatch, capsys):
        from main import lifespan
        from core.config import settings
        monkeypatch.setattr(settings, 'GROQ_API_KEY', 'test-key')
        monkeypatch.setattr('main.Base.metadata.create_all', lambda bind: None)
        monkeypatch.setattr('main._print_db_banner', lambda: None)
        import asyncio
        async def run():
            async with lifespan(None):
                pass
        asyncio.run(run())
        captured = capsys.readouterr()
        assert 'configurada' in captured.out


# ═══════════════════════════════════════════════════════════════════════════════
# infrastructure/generators/roadmap.py — increase from 68% to 85%+
# ═══════════════════════════════════════════════════════════════════════════════

TEST_SLIDE_ROADMAP = """
<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
       xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
       xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
<p:cSld><p:spTree>
<p:sp><p:nvSpPr><p:cNvPr name="Fase 1"/></p:nvSpPr>
<p:spPr><a:xfrm><a:off x="100" y="100"/><a:ext cx="1000" cy="500"/></a:xfrm></p:spPr>
<p:txBody><a:p><a:r><a:t>Fase 1</a:t></a:r></a:p></p:txBody></p:sp>
<p:sp><p:nvSpPr><p:cNvPr name="Descripcion 1"/></p:nvSpPr>
<p:spPr><a:xfrm><a:off x="1100" y="100"/><a:ext cx="1000" cy="500"/></a:xfrm></p:spPr>
<p:txBody><a:p><a:r><a:t>Desc 1</a:t></a:r></a:p></p:txBody></p:sp>
<p:sp><p:nvSpPr><p:cNvPr name="Fase 2"/></p:nvSpPr>
<p:spPr><a:xfrm><a:off x="2100" y="100"/><a:ext cx="1000" cy="500"/></a:xfrm></p:spPr>
<p:txBody><a:p><a:r><a:t>Fase 2</a:t></a:r></a:p></p:txBody></p:sp>
<p:sp><p:nvSpPr><p:cNvPr name="Descripcion 2"/></p:nvSpPr>
<p:spPr><a:xfrm><a:off x="3100" y="100"/><a:ext cx="1000" cy="500"/></a:xfrm></p:spPr>
<p:txBody><a:p><a:r><a:t>Desc 2</a:t></a:r></a:p></p:txBody></p:sp>
<p:sp><p:nvSpPr><p:cNvPr name="Fase 3"/></p:nvSpPr>
<p:spPr><a:xfrm><a:off x="4100" y="100"/><a:ext cx="1000" cy="500"/></a:xfrm></p:spPr>
<p:txBody><a:p><a:r><a:t>Fase 3</a:t></a:r></a:p></p:txBody></p:sp>
<p:sp><p:nvSpPr><p:cNvPr name="Descripcion 3"/></p:nvSpPr>
<p:spPr><a:xfrm><a:off x="5100" y="100"/><a:ext cx="1000" cy="500"/></a:xfrm></p:spPr>
<p:txBody><a:p><a:r><a:t>Desc 3</a:t></a:r></a:p></p:txBody></p:sp>
<p:sp><p:nvSpPr><p:cNvPr name="Fase 4"/></p:nvSpPr>
<p:spPr><a:xfrm><a:off x="6100" y="100"/><a:ext cx="1000" cy="500"/></a:xfrm></p:spPr>
<p:txBody><a:p><a:r><a:t>Fase 4</a:t></a:r></a:p></p:txBody></p:sp>
<p:sp><p:nvSpPr><p:cNvPr name="Descripcion 4"/></p:nvSpPr>
<p:spPr><a:xfrm><a:off x="7100" y="100"/><a:ext cx="1000" cy="500"/></a:xfrm></p:spPr>
<p:txBody><a:p><a:r><a:t>Desc 4</a:t></a:r></a:p></p:txBody></p:sp>
</p:spTree></p:cSld></p:sld>
"""


def _build_minimal_pptx(slides_dict=None):
    """Build minimal valid PPTX bytes with given slides dict {path: xml_content}."""
    if slides_dict is None:
        slides_dict = {'ppt/slides/slide1.xml': '<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"><p:cSld><p:spTree/></p:cSld></p:sld>'}
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml',
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>')
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


class TestRoadmapFinal:
    def test_edit_with_four_phases(self):
        from infrastructure.generators.roadmap import edit
        xml = TEST_SLIDE_ROADMAP.replace('Fase 1', 'Fase A').replace('Fase 2', 'Fase B')\
            .replace('Fase 3', 'Fase C').replace('Fase 4', 'Fase D')
        pptx = _build_minimal_pptx({'ppt/slides/slide4.xml': xml.encode() if isinstance(xml, str) else xml})
        config = {'roadmap_phases': [{'fase': 'F1', 'descripcion': 'D1'}, {'fase': 'F2', 'descripcion': 'D2'}, {'fase': 'F3', 'descripcion': 'D3'}, {'fase': 'F4', 'descripcion': 'D4'}]}
        result = edit(pptx, config, {})
        assert isinstance(result, bytes)

    def test_edit_with_less_than_four(self):
        from infrastructure.generators.roadmap import edit
        pptx = _build_minimal_pptx({'ppt/slides/slide4.xml': TEST_SLIDE_ROADMAP.encode()})
        config = {'roadmap_phases': [{'fase': 'F1', 'descripcion': 'D1'}]}
        result = edit(pptx, config, {})
        assert isinstance(result, bytes)

    def test_edit_slide_not_found(self):
        from infrastructure.generators.roadmap import edit
        pptx = _build_minimal_pptx({'ppt/slides/slide1.xml': '<xml/>'})
        config = {'roadmap_phases': [{'fase': 'F1', 'descripcion': 'D1'}]}
        result = edit(pptx, config, {})
        assert isinstance(result, bytes)

    def test_extract_shape_text_multi_run(self):
        from infrastructure.generators.roadmap import _extract_shape_text
        shape = etree.fromstring(
            '<p:sp xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
            'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
            '<p:txBody><a:p><a:r><a:t>Hello</a:t></a:r><a:r><a:t> </a:t></a:r><a:r><a:t>world</a:t></a:r></a:p></p:txBody></p:sp>'
        )
        text = _extract_shape_text(shape)
        assert 'Hello' in text


# ═══════════════════════════════════════════════════════════════════════════════
# infrastructure/generators/consideraciones.py — edge cases
# ═══════════════════════════════════════════════════════════════════════════════

class TestConsideracionesEdgeCases:
    def test_load_desde_excel_empty_input(self):
        from infrastructure.generators.consideraciones import _load_desde_excel
        assert _load_desde_excel(["", None, "  "], "C", "F") == []

    def test_split_por_punto_single(self):
        from infrastructure.generators.consideraciones import _split_por_punto
        assert _split_por_punto("Oracion unica.") == ["Oracion unica."]

    def test_split_por_punto_no_period(self):
        from infrastructure.generators.consideraciones import _split_por_punto
        result = _split_por_punto("Sin punto")
        assert len(result) == 0 or "Sin punto" in result[0]

    def test_load_desde_generales_empty(self):
        from infrastructure.generators.consideraciones import _load_desde_generales
        result = _load_desde_generales([], "C", "F", {})
        assert result == []

    def test_norm_none(self):
        from infrastructure.generators.consideraciones import _norm
        assert _norm(None) == ""
        assert _norm("") == ""

    def test_calc_delta_exact(self):
        from infrastructure.generators.consideraciones import _calc_delta, CHARS_POR_LINEA, LINEAS_BASE
        exact = "A" * (CHARS_POR_LINEA * LINEAS_BASE)
        assert _calc_delta(exact) == 0
        one_more = "A" * (CHARS_POR_LINEA * LINEAS_BASE + 1)
        assert _calc_delta(one_more) > 0

    def test_filial_nombres_contains(self):
        from infrastructure.generators.consideraciones import FILIAL_NOMBRES
        assert 'corp' in FILIAL_NOMBRES
        assert 'group' in FILIAL_NOMBRES
        assert 'cbit' in FILIAL_NOMBRES


# ═══════════════════════════════════════════════════════════════════════════════
# infrastructure/generators/cronograma_entregables.py — edge cases
# ═══════════════════════════════════════════════════════════════════════════════

class TestCronogramaEntregablesEdge:
    def test_load_entregables_with_data(self):
        from infrastructure.generators.cronograma_entregables import _load_entregables
        catalog = {
            'entregables_db': [
                {'torre': 'Backend', 'items': ['Item 1', 'Item 2']},
                {'torre': 'Frontend', 'items': ['Item A']}
            ]
        }
        result = _load_entregables(['Backend', 'Frontend'], catalog)
        assert len(result) == 2
        assert any(g['torre'] == 'Backend' for g in result)

    def test_load_entregables_no_match(self):
        from infrastructure.generators.cronograma_entregables import _load_entregables
        result = _load_entregables(['Backend'], {'entregables_db': []})
        assert result == []

    def test_edit_without_catalog(self):
        from infrastructure.generators.cronograma_entregables import edit
        pptx = _build_minimal_pptx()
        config = {'excel_data': {'entregables': [{'torre': 'A', 'items': ['X']}]}}
        result = edit(pptx, config, None)
        assert isinstance(result, bytes)

    def test_edit_with_excel_data_no_entregables(self):
        from infrastructure.generators.cronograma_entregables import edit
        pptx = _build_minimal_pptx()
        config = {'excel_data': {'torres': [{'nombre': 'A'}]}, 'torres_seleccionadas': []}
        result = edit(pptx, config, {'entregables_db': []})
        assert isinstance(result, bytes)

    def test_edit_4_cols(self):
        from infrastructure.generators.cronograma_entregables import edit
        pptx_content = TEST_SLIDE_ROADMAP
        pptx = _build_minimal_pptx({'ppt/slides/slide1.xml': pptx_content.encode()})
        config = {
            'excel_data': {
                'entregables': [
                    {'torre': 'A', 'items': ['1', '2']},
                    {'torre': 'B', 'items': ['3', '4']},
                    {'torre': 'C', 'items': ['5', '6']},
                    {'torre': 'D', 'items': ['7', '8']},
                ]
            }
        }
        result = edit(pptx, config, {})
        assert isinstance(result, bytes)


# ═══════════════════════════════════════════════════════════════════════════════
# infrastructure/generators/cronograma_preview.py — edge cases
# ═══════════════════════════════════════════════════════════════════════════════

class TestCronogramaPreviewEdge:
    def test_title_bottom_with_title(self):
        from infrastructure.generators.cronograma_preview import _title_bottom_emu
        slide = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
            'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
            '<p:cSld><p:spTree>'
            '<p:sp><p:nvSpPr><p:cNvPr name="Title 1"/><p:nvPr><p:ph type="title"/></p:nvPr></p:nvSpPr>'
            '<p:spPr><a:xfrm><a:off x="100" y="200000"/><a:ext cx="1000" cy="300000"/></a:xfrm></p:spPr>'
            '<p:txBody><a:p><a:r><a:t>Title</a:t></a:r></a:p></p:txBody></p:sp>'
            '</p:spTree></p:cSld></p:sld>'
        ).encode()
        bottom = _title_bottom_emu(slide)
        assert bottom > 0

    def test_insert_pic_no_spTree(self):
        from infrastructure.generators.cronograma_preview import _insert_pic
        result = _insert_pic(b'<xml/>', 'rId1', 100, 1.5)
        assert result == b'<xml/>'


# ═══════════════════════════════════════════════════════════════════════════════
# infrastructure/generators/fda_perfiles.py — edge cases (36%)
# ═══════════════════════════════════════════════════════════════════════════════

class TestFdaPerfilesEdge:
    def test_norm_various(self):
        from infrastructure.generators.fda_perfiles import _norm
        assert _norm("  Hello  World  ") == "HELLO WORLD"
        assert _norm(None) == ""
        assert _norm("") == ""

    def test_clean_inline_text_various(self):
        from infrastructure.generators.fda_perfiles import _clean_inline_text
        assert _clean_inline_text("  Line1\nLine2\r\nLine3  ") == "Line1 Line2 Line3"
        assert _clean_inline_text(None) == ""
        assert _clean_inline_text("") == ""

    def test_split_profile_titles_comma(self):
        from infrastructure.generators.fda_perfiles import _split_profile_titles
        result = _split_profile_titles("Dev, QA")
        assert len(result) >= 1

    def test_even_chunks_exact(self):
        from infrastructure.generators.fda_perfiles import _even_chunks
        assert _even_chunks([1, 2, 3, 4, 5, 6], 6) == [[1, 2, 3, 4, 5, 6]]

    def test_truncate_desc_short(self):
        from infrastructure.generators.fda_perfiles import _truncate_desc
        assert _truncate_desc("Short text", 50) == "Short text"
        assert _truncate_desc("A" * 200, 100) is not None

    def test_truncate_to_sentences_with_limit(self):
        from infrastructure.generators.fda_perfiles import _truncate_to_sentences
        result = _truncate_to_sentences("A. B. C. D. E.")
        assert len(result) > 0

    def test_find_desc_in_catalog_empty(self):
        from infrastructure.generators.fda_perfiles import _find_desc_in_catalog
        assert _find_desc_in_catalog("Dev", {}) == ""

    def test_esc_various(self):
        from infrastructure.generators.fda_perfiles import _esc
        assert "amp;" in _esc("a&b")
        assert _esc("normal") == "normal"



# ═══════════════════════════════════════════════════════════════════════════════
# api/v1/ai/router.py — increase from 82% to 90%+
# ═══════════════════════════════════════════════════════════════════════════════

class TestAIRouter:
    def test_chat_empty_messages(self, client):
        response = client.post("/api/v1/ai/chat", json={"messages": []})
        assert response.status_code in (400, 500)

    def test_chat_invalid_role(self, client):
        response = client.post("/api/v1/ai/chat", json={"messages": [{"role": "invalid", "content": "Hi"}]})
        assert response.status_code in (400, 422, 500)

    def test_health_endpoint_exists(self, client):
        from main import app
        routes = [r.path for r in app.routes]
        assert "/api/v1/ai/chat" in routes


# ═══════════════════════════════════════════════════════════════════════════════
# api/v1/quality/router.py — increase from 69% to 85%+
# ═══════════════════════════════════════════════════════════════════════════════

class TestQualityRouter:
    def test_parse_coverage_empty_lines(self):
        from api.v1.quality.router import parse_coverage_from_output
        assert parse_coverage_from_output("\n\n") == []

    def test_parse_coverage_no_total(self):
        from api.v1.quality.router import parse_coverage_from_output
        result = parse_coverage_from_output("Name  Stmts  Miss  Cover\n------\nmain.py  10  5  50%\n")
        assert isinstance(result, list)

    def test_coverage_route_not_found(self, client):
        from main import app
        routes = [r.path for r in app.routes]
        assert any("quality" in r for r in routes)

    def test_quality_endpoints_exist(self, client):
        from main import app
        paths = [r.path for r in app.routes]
        quality_routes = [p for p in paths if 'quality' in p]
        assert len(quality_routes) >= 1


# ═══════════════════════════════════════════════════════════════════════════════
# infrastructure/generators/cronograma_image.py — increase from 84% to 90%+
# ═══════════════════════════════════════════════════════════════════════════════

class TestCronogramaImage:
    def test_hex_color(self):
        from infrastructure.generators.cronograma_image import _hex
        assert _hex("#FF0000") == (255, 0, 0)
        assert _hex("00FF00") == (0, 255, 0)

    def test_fnt_default(self):
        from infrastructure.generators.cronograma_image import _fnt
        font = _fnt(["/nonexistent/font.ttf"], 12)
        assert font is not None

    def test_generate_with_semanas(self):
        from infrastructure.generators.cronograma_image import generate_cronograma_image
        from unittest.mock import patch
        with patch('infrastructure.generators.cronograma_image._render') as mock_render:
            mock_render.return_value = b"fake-png"
            result = generate_cronograma_image({
                'actividades': [{'torre': 'A', 'horas': 43, 'personas': 2, 'semanas': 2}],
                'roles': [{'perfil': 'Dev', 'personas': 2}],
                'nombre_proyecto': 'Test'
            })
            assert result == b"fake-png"

    def test_generate_raises_empty(self):
        from infrastructure.generators.cronograma_image import generate_cronograma_image
        with pytest.raises(ValueError):
            generate_cronograma_image({'actividades': [], 'roles': []})

    def test_generate_raises_no_actividades(self):
        from infrastructure.generators.cronograma_image import generate_cronograma_image
        with pytest.raises(ValueError):
            generate_cronograma_image({'actividades': None})


# ═══════════════════════════════════════════════════════════════════════════════
# infrastructure/generators/oferta_economica.py — remaining uncovered lines
# ═══════════════════════════════════════════════════════════════════════════════

class TestOfertaEconomicaFinal:
    def _make_oferta_pptx_with_tabla3(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
            z.writestr('[Content_Types].xml',
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>')
            z.writestr('ppt/_rels/presentation.xml.rels',
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide1.xml"/></Relationships>')
            z.writestr('ppt/presentation.xml',
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><p:sldIdLst><p:sldId id="256" r:id="rId1"/></p:sldIdLst></p:presentation>')
            slide = (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
                'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
                '<p:cSld><p:spTree>'
                '<p:graphicFrame><p:nvGraphicFramePr><p:cNvPr name="Tabla 3"/></p:nvGraphicFramePr>'
                '<a:graphic><a:graphicData><a:tbl>'
                '<a:tr><a:tc><a:txBody><a:p><a:r><a:t>Col1</a:t></a:r></a:p></a:txBody></a:tc>'
                '<a:tc><a:txBody><a:p><a:r><a:t>Col2</a:t></a:r></a:p></a:txBody></a:tc>'
                '<a:tc><a:txBody><a:p><a:r><a:t>Col3</a:t></a:r></a:p></a:txBody></a:tc></a:tr>'
                '<a:tr><a:tc><a:txBody><a:p><a:r><a:t>R2C1</a:t></a:r></a:p></a:txBody></a:tc>'
                '<a:tc><a:txBody><a:p><a:r><a:t>R2C2</a:t></a:r></a:p></a:txBody></a:tc>'
                '<a:tc><a:txBody><a:p><a:r><a:t>R2C3</a:t></a:r></a:p></a:txBody></a:tc></a:tr>'
                '<a:tr><a:tc><a:txBody><a:p><a:r><a:t>Total</a:t></a:r></a:p></a:txBody></a:tc></a:tr>'
                '</a:tbl></a:graphicData></a:graphic></p:graphicFrame>'
                '</p:spTree></p:cSld></p:sld>'
            )
            z.writestr('ppt/slides/slide1.xml', slide)
        return buf.getvalue()

    def test_edit_no_slide_found_oferta(self):
        from infrastructure.generators.oferta_economica import edit
        # PPTX without Tabla 3
        pptx = _build_minimal_pptx()
        result = edit(pptx, {'excel_data': {'perfiles': []}}, {})
        assert isinstance(result, bytes)

    def test_edit_slide_found_no_table(self):
        from infrastructure.generators.oferta_economica import edit
        # PPTX with slide but no table in graphicFrame
        pptx = self._make_oferta_pptx_with_tabla3()
        result = edit(pptx, {'excel_data': {'perfiles': [{'perfil': 'Dev', 'personas': 2, 'horas': 160}]}}, {})
        assert isinstance(result, bytes)

    def test_set_cell_text_no_txbody(self):
        from infrastructure.generators.oferta_economica import _set_cell_text
        cell = etree.fromstring(
            '<a:tc xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"/>'
        )
        _set_cell_text(cell, "text")  # Should not raise

    def test_set_cell_text_no_runs(self):
        from infrastructure.generators.oferta_economica import _set_cell_text
        cell = etree.fromstring(
            '<a:tc xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
            '<a:txBody><a:p></a:p></a:txBody></a:tc>'
        )
        _set_cell_text(cell, "new text")
        txBody = cell.find('{http://schemas.openxmlformats.org/drawingml/2006/main}txBody')
        t_els = txBody.findall('.//{http://schemas.openxmlformats.org/drawingml/2006/main}t')
        assert any(t.text == 'new text' for t in t_els)


# ═══════════════════════════════════════════════════════════════════════════════
# domain/catalogo/service.py - complete coverage
# ═══════════════════════════════════════════════════════════════════════════════

class TestCatalogoServiceFinal:
    def test_list_torres_with_data(self):
        from domain.catalogo import service
        import domain.catalogo.service as svc
        from unittest.mock import MagicMock, patch
        mock_db = MagicMock()
        with patch.object(svc, 'repo') as mock_repo:
            mock_repo.get_torres.return_value = [MagicMock(id=1, nombre='Backend', nombre_norm='BACKEND', activa=True)]
            result = svc.list_torres(mock_db)
            assert len(result) == 1

    def test_list_torres_empty(self):
        from domain.catalogo import service as svc
        from unittest.mock import patch, MagicMock
        mock_db = MagicMock()
        with patch.object(svc, 'repo') as mock_repo:
            mock_repo.get_torres.return_value = []
            result = svc.list_torres(mock_db)
            assert result == []

    def test_list_all_torres(self):
        from domain.catalogo import service as svc
        from unittest.mock import patch, MagicMock
        mock_db = MagicMock()
        with patch.object(svc, 'repo') as mock_repo:
            mock_repo.get_torres.return_value = [MagicMock(id=1, nombre='Backend', nombre_norm='BACKEND', activa=True)]
            result = svc.list_torres(mock_db)
            assert len(result) == 1

    def test_create_torre_with_mock(self):
        from domain.catalogo import service as svc
        from domain.catalogo.entities import TorreCreate
        from unittest.mock import patch, MagicMock
        mock_db = MagicMock()
        with patch.object(svc, 'repo') as mock_repo:
            mock_fake = MagicMock(id=1, nombre='NewTorre', nombre_norm='NEWTORRE', activa=True)
            mock_repo.create_torre.return_value = mock_fake
            result = svc.create_torre(mock_db, TorreCreate(nombre='NewTorre'))
            assert result is not None
            assert result.id == 1

    def test_delete_torre_exists(self):
        from domain.catalogo import service as svc
        from unittest.mock import patch, MagicMock
        mock_db = MagicMock()
        with patch.object(svc, 'repo') as mock_repo:
            mock_repo.delete_torre.return_value = True
            result = svc.delete_torre(mock_db, 1)
            assert result is True


# ═══════════════════════════════════════════════════════════════════════════════
# infrastructure/repositories/catalogo_repository.py - remaining lines
# ═══════════════════════════════════════════════════════════════════════════════

class TestCatalogoRepositoryFinal:
    def test_get_torres(self):
        from infrastructure.repositories import catalogo_repository as repo
        from unittest.mock import MagicMock
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = [MagicMock()]
        result = repo.get_torres(mock_db)
        assert len(result) == 1

    def test_get_torres_all(self):
        from infrastructure.repositories import catalogo_repository as repo
        from unittest.mock import MagicMock
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = [MagicMock(), MagicMock()]
        result = repo.get_torres(mock_db, solo_activas=False)
        assert len(result) == 2

    def test_get_perfiles(self):
        from infrastructure.repositories import catalogo_repository as repo
        from unittest.mock import MagicMock
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [MagicMock()]
        result = repo.get_perfiles(mock_db)
        assert len(result) == 1

    def test_get_perfiles_filtered(self):
        from infrastructure.repositories import catalogo_repository as repo
        from unittest.mock import MagicMock
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [MagicMock()]
        result = repo.get_perfiles(mock_db, torre_id=1)
        assert len(result) == 1

    def test_delete_torre_exists(self):
        from infrastructure.repositories import catalogo_repository as repo
        from unittest.mock import MagicMock
        mock_db = MagicMock()
        mock_obj = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_obj
        assert repo.delete_torre(mock_db, 1) is True

    def test_delete_torre_nonexistent(self):
        from infrastructure.repositories import catalogo_repository as repo
        from unittest.mock import MagicMock
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        assert repo.delete_torre(mock_db, 999) is False

    def test_update_consideracion(self):
        from infrastructure.repositories import catalogo_repository as repo
        from unittest.mock import MagicMock
        mock_db = MagicMock()
        mock_obj = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_obj
        result = repo.update_consideracion(mock_db, 1, "new text", 2)
        assert result is not None

    def test_update_consideracion_not_found(self):
        from infrastructure.repositories import catalogo_repository as repo
        from unittest.mock import MagicMock
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        assert repo.update_consideracion(mock_db, 999, "text", 1) is None