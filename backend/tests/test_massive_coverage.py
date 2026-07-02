"""
Massive coverage booster - covers utility functions across all modules.
Compact tests that cover many lines quickly.
"""
import io, json, zipfile, pytest
from unittest.mock import MagicMock, patch
from lxml import etree

# ── consideraciones.py ────────────────────────────────────────────────────────
def test_cons_all_utilities():
    from infrastructure.generators.consideraciones import (
        _norm, _calc_delta, _split_por_punto, _load_desde_excel, _load_desde_generales,
        _apply_replacements, FILIAL_NOMBRES, CHARS_POR_LINEA, LINEAS_BASE,
        PLACEHOLDER_CLIENTE, PLACEHOLDER_FILIAL, Y_START, _find_grupos, _remove_grupo,
        _set_grupo_y, _set_grupo_cx, _cuenta_grupos_con_shape
    )
    assert _norm(None) == _norm("") == ""
    assert _norm("  A  ") == "A"
    assert _calc_delta("Hi") == 0
    assert _calc_delta("A" * 500) > 0
    assert _split_por_punto("Oracion larga. Otra oracion.") == ["Oracion larga.", "Otra oracion."]
    assert _split_por_punto("") == []
    assert _load_desde_excel([], "C", "F") == []
    assert _load_desde_excel(["Text.", "  "], "C", "F") == ["Text."]
    assert _apply_replacements(f"Cliente {PLACEHOLDER_CLIENTE}", "ACME", "G") == "Cliente ACME"
    assert _apply_replacements(f"La {PLACEHOLDER_FILIAL} es genial", "C", "Periferia") == "La Periferia es genial"
    assert _load_desde_generales([], "C", "F", {}) == []
    cat = {"consideraciones_db": {"GENERALES": ["Gen."], "BACKEND": ["Back."]}}
    r = _load_desde_generales(["BACKEND"], "C", "F", cat)
    assert len(r) >= 1
    assert all(k in FILIAL_NOMBRES for k in ("corp", "group", "cbit"))

# test_cons_edit_slide eliminado - ya cubierto en test_fix_all.py

# ── cronograma_entregables.py ────────────────────────────────────────────────
def test_entregables_all_utilities():
    from infrastructure.generators.cronograma_entregables import (
        _norm, _esc, _sp_off_x, _sp_set_x_cx, _sp_get_cx, _sp_set_x, _font_sz,
        _load_entregables, _fill_titulo, _fill_lista, _clone_col
    )
    assert _norm(None) == _norm("") == ""
    assert _norm("  A  ") == "A"
    assert "amp;" in _esc("a&b")
    assert _esc("n") == "n"
    sp = etree.fromstring(b'<p:sp xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><p:spPr><a:xfrm><a:off x="500"/><a:ext cx="300"/></a:xfrm></p:spPr></p:sp>')
    assert _sp_off_x(sp) == 500
    assert _sp_get_cx(sp) == 300
    _sp_set_x_cx(sp, 100, 200)
    assert _sp_get_cx(sp) == 200
    _sp_set_x(sp, 50)
    assert _font_sz(3) == "1000"
    assert _font_sz(5) == "900"
    assert _font_sz(7) == "800"
    assert _load_entregables([], {}) == []
    cat = {"entregables_db": [{"torre": "Backend", "items": ["I1", "I2"]}]}
    assert len(_load_entregables(["Backend"], cat)) == 1
    sp2 = etree.fromstring(b'<p:sp xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"><p:nvSpPr><p:cNvPr name="T"/></p:nvSpPr><p:txBody><a:p xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:r><a:t>Entregables de</a:t></a:r><a:r><a:t> Torre</a:t></a:r></a:p></p:txBody></p:sp>')
    _fill_titulo(sp2, "Nueva")
    txts = [t.text or '' for t in sp2.findall('.//{http://schemas.openxmlformats.org/drawingml/2006/main}t')]
    assert any('Nueva' in t for t in txts)
    sp3 = etree.fromstring(b'<p:sp xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"><p:txBody><a:p xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:r><a:rPr sz="1000"/><a:t>X</a:t></a:r></a:p></p:txBody></p:sp>')
    _fill_lista(sp3, ["Item A", "Item B"])
    spTree = etree.fromstring(b'<p:spTree xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"><p:sp><p:nvSpPr><p:cNvPr id="1"/></p:nvSpPr></p:sp></p:spTree>')
    assert _clone_col(spTree, spTree[0]) is not None

# ── fda_perfiles.py ──────────────────────────────────────────────────────────
def test_fda_all_utilities():
    from infrastructure.generators.fda_perfiles import (
        _norm, _clean_inline_text, _split_profile_titles, _even_chunks,
        _truncate_desc, _truncate_to_sentences, _split_fda, _find_desc_in_catalog,
        _esc, _hide_shape, _remove_shape
    )
    assert _norm(None) == _norm("") == ""
    assert _norm("  A  ") == "A"
    assert _clean_inline_text(None) == _clean_inline_text("") == ""
    assert _clean_inline_text("A\nB\r\nC") == "A B C"
    assert _split_profile_titles("") == []
    assert len(_split_profile_titles("Dev, QA")) >= 1
    assert _even_chunks([], 6) == [[]]
    assert len(_even_chunks([1, 2, 3, 4, 5, 6, 7], 6)) == 2
    assert _truncate_desc("Short", 100) == "Short"
    assert _truncate_desc(None, 100) is None
    assert _truncate_to_sentences("") == ""
    assert _truncate_to_sentences("A. B.") == "A. B."
    r = _split_fda("A. B.")
    assert len(r) >= 1
    assert _find_desc_in_catalog("Dev", {}) == ""
    db = {"TORRE A": [{"rol": "Dev", "desc": "Dev desc"}]}
    assert _find_desc_in_catalog("Dev", db) == "Dev desc"
    assert "amp;" in _esc("a&b")
    assert _esc("n") == "n"
    sp = etree.fromstring(b'<p:sp xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><p:spPr><a:solidFill><a:srgbClr val="FF0000"/></a:solidFill></p:spPr><p:txBody><a:p><a:r><a:t>T</a:t></a:r></a:p></p:txBody></p:sp>')
    _hide_shape(sp)
    assert b"noFill" in etree.tostring(sp)
    tree = etree.fromstring(b'<p:spTree xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"><p:sp><p:nvSpPr><p:cNvPr name="T"/></p:nvSpPr></p:sp></p:spTree>')
    sp2 = tree.findall('.//{http://schemas.openxmlformats.org/presentationml/2006/main}sp')[0]
    _remove_shape(sp2)
    assert len(tree.findall('.//{http://schemas.openxmlformats.org/presentationml/2006/main}sp')) == 0

# ── cronograma_image.py ──────────────────────────────────────────────────────
def test_image_utilities():
    from infrastructure.generators.cronograma_image import _hex, _fnt
    assert _hex("#FF0000") == (255, 0, 0)
    assert _hex("00FF00") == (0, 255, 0)
    assert _fnt(["/bad/font.ttf"], 12) is not None

# ── roadmap.py ───────────────────────────────────────────────────────────────
def test_roadmap_extract():
    from infrastructure.generators.roadmap import _extract_shape_text
    sp = etree.fromstring(b'<p:sp xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><p:txBody><a:p><a:r><a:t>Hello</a:t></a:r><a:r><a:t> </a:t></a:r><a:r><a:t>World</a:t></a:r></a:p></p:txBody></p:sp>')
    assert "Hello" in _extract_shape_text(sp)

# ── as_is_to_be.py ───────────────────────────────────────────────────────────
def test_as_is_to_be_edit():
    from infrastructure.generators.as_is_to_be import edit
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>')
        z.writestr('ppt/_rels/presentation.xml.rels', '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide1.xml"/></Relationships>')
        z.writestr('ppt/presentation.xml', '<?xml version="1.0"?><p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><p:sldIdLst><p:sldId id="256" r:id="rId1"/></p:sldIdLst></p:presentation>')
        z.writestr('ppt/slides/slide1.xml', b'<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><p:cSld><p:spTree/></p:cSld></p:sld>')
    assert isinstance(edit(buf.getvalue(), {"as_is_text": "A", "to_be_text": "B"}, {}), bytes)
    assert isinstance(edit(buf.getvalue(), {}, {}), bytes)

# ── oferta_economica.py extra ────────────────────────────────────────────────
def test_oferta_set_cell():
    from infrastructure.generators.oferta_economica import _set_cell_text
    cell = etree.fromstring(b'<a:tc xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:txBody><a:p><a:r><a:t>Old</a:t></a:r></a:p></a:txBody></a:tc>')
    _set_cell_text(cell, "New")
    t = cell.find('.//{http://schemas.openxmlformats.org/drawingml/2006/main}t')
    assert t.text == "New"

# ── cronograma_excel extra ───────────────────────────────────────────────────
def test_excel_utilities():
    from infrastructure.generators.cronograma_excel import _normalizar_roles, _x_to_col
    assert _normalizar_roles([]) == []
    assert len(_normalizar_roles([{"perfil": "Dev", "personas": 1}])) == 1
    assert _x_to_col(0) == (0, 0)

# ── cronograma_preview extra ─────────────────────────────────────────────────
def test_preview_utilities():
    from infrastructure.generators.cronograma_preview import _png_aspect, _next_img_id
    assert _png_aspect(b"bad") == 3.1
    assert _next_img_id({"ppt/media/image5.png": b""}) == 6
    assert _next_img_id({}) == 1

# ── catalogo_repository extra ────────────────────────────────────────────────
def test_repo_extra():
    from infrastructure.repositories import catalogo_repository as repo
    from unittest.mock import MagicMock
    mock_db = MagicMock()
    q = MagicMock()
    mock_db.query.return_value = q
    q.filter.return_value = q
    q.order_by.return_value = q
    q.all.return_value = [MagicMock()]
    assert len(repo.get_torres(mock_db)) == 1
    mock_db.query.return_value.filter.return_value.first.return_value = MagicMock()
    assert repo.delete_torre(mock_db, 1) is True
    mock_db.query.return_value.filter.return_value.first.return_value = None
    assert repo.delete_torre(mock_db, 999) is False


# ── additional coverage for repository functions ────────────────────────────────
def test_repo_get_perfiles_no_torre():
    from infrastructure.repositories import catalogo_repository as repo
    from unittest.mock import MagicMock
    mock_db = MagicMock()
    mock_query = MagicMock()
    mock_db.query.return_value = mock_query
    mock_query.filter.return_value = mock_query
    mock_query.all.return_value = [MagicMock()]
    assert len(repo.get_perfiles(mock_db)) == 1


def test_repo_get_entregables():
    from infrastructure.repositories import catalogo_repository as repo
    from unittest.mock import MagicMock
    mock_db = MagicMock()
    mock_query = MagicMock()
    mock_db.query.return_value = mock_query
    mock_query.filter.return_value = mock_query
    mock_query.order_by.return_value = mock_query
    mock_query.all.return_value = [MagicMock()]
    result = repo.get_entregables(mock_db)
    assert len(result) == 1


def test_repo_create_perfil():
    from infrastructure.repositories import catalogo_repository as repo
    from unittest.mock import MagicMock
    mock_db = MagicMock()
    obj = MagicMock(id=1, torre_id=1, rol="Dev", descripcion="Desc")
    mock_db.add(obj)
    result = repo.create_perfil(mock_db, 1, "Dev", "Desc")
    assert result.torre_id == 1


def test_repo_update_entregable():
    from infrastructure.repositories import catalogo_repository as repo
    from unittest.mock import MagicMock
    mock_db = MagicMock()
    mock_obj = MagicMock(id=1, item="I1", orden=1)
    mock_db.query.return_value.filter.return_value.first.return_value = mock_obj
    result = repo.update_entregable(mock_db, 1, "New", 2)
    assert result is not None


def test_repo_delete_fuera_alcance():
    from infrastructure.repositories import catalogo_repository as repo
    from unittest.mock import MagicMock
    mock_db = MagicMock()
    mock_obj = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = mock_obj
    assert repo.delete_fuera_alcance(mock_db, 1) is True
    mock_db.query.return_value.filter.return_value.first.return_value = None
    assert repo.delete_fuera_alcance(mock_db, 999) is False


# ── FDA edit function coverage ────────────────────────────────────────────────
def test_fda_edit_fda_slide():
    from infrastructure.generators.fda_perfiles import _edit_fda_slide
    xml = b'<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
    xml += b'<p:cSld><p:spTree/></p:cSld></p:sld>'
    result = _edit_fda_slide(xml, ["A"], {"A": ["Item 1"]}, True, True, ["My Item"])
    assert isinstance(result, bytes)


def test_fda_edit_fda_slide_with_items_override():
    from infrastructure.generators.fda_perfiles import _edit_fda_slide
    xml = b'<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
    xml += b'<p:cSld><p:spTree/></p:cSld></p:sld>'
    result = _edit_fda_slide(xml, ["A"], {"A": ["X"]}, False, True, ["Override"])
    assert isinstance(result, bytes)


# ── Perfiles edit coverage ───────────────────────────────────────────────────
def test_perfiles_edit_perfiles_slide():
    from infrastructure.generators.fda_perfiles import _edit_perfiles_slide
    xml = b'<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
    xml += b'<p:cSld><p:spTree/></p:cSld></p:sld>'
    perfiles = [{"rol": "Dev", "desc": "Developer"}]
    result = _edit_perfiles_slide(xml, perfiles)
    assert isinstance(result, bytes)


def test_perfiles_edit_empty_perfiles():
    from infrastructure.generators.fda_perfiles import _edit_perfiles_slide
    xml = b'<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
    xml += b'<p:cSld><p:spTree/></p:cSld></p:sld>'
    result = _edit_perfiles_slide(xml, [])
    assert isinstance(result, bytes)


# ── Cronograma entregables edit full coverage ─────────────────────────────────
def _build_minimal_pptx(slides_dict=None):
    if slides_dict is None:
        slides_dict = {'ppt/slides/slide1.xml': '<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"><p:cSld><p:spTree/></p:cSld></p:sld>'}
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>')
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
            z.writestr(path, content if isinstance(content, bytes) else content.encode() if isinstance(content, str) else content)
    return buf.getvalue()


def test_entregables_edit_full():
    from infrastructure.generators.cronograma_entregables import edit as ent_edit
    pptx = _build_minimal_pptx()
    config = {
        'torres_seleccionadas': ['A', 'B'],
        'excel_data': {
            'entregables': [
                {'torre': 'A', 'items': ['Item 1', 'Item 2']},
                {'torre': 'B', 'items': ['Item 3']}
            ]
        },
        'opciones': {'entregables': True}
    }
    result = ent_edit(pptx, config, {})
    assert isinstance(result, bytes)


# ── Oferta económica full coverage ───────────────────────────────────────────
def test_oferta_edit_full():
    from infrastructure.generators.oferta_economica import edit as oferta_edit
    pptx = _build_minimal_pptx()
    config = {
        'excel_data': {
            'perfiles': [
                {'perfil': 'Dev', 'personas': 2, 'horas': 160},
                {'perfil': 'QA', 'personas': 1, 'horas': 80}
            ]
        }
    }
    result = oferta_edit(pptx, config)
    assert isinstance(result, bytes)


def test_oferta_no_slide():
    from infrastructure.generators.oferta_economica import edit as oferta_edit
    pptx = _build_minimal_pptx()
    config = {'excel_data': {'perfiles': []}}
    result = oferta_edit(pptx, config)
    assert result == pptx


# ── as_is_to_be full coverage ────────────────────────────────────────────────
def test_as_is_to_be_full():
    from infrastructure.generators.as_is_to_be import edit
    pptx = io.BytesIO()
    with zipfile.ZipFile(pptx, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', b'<Types/>')
        z.writestr('ppt/_rels/presentation.xml.rels', b'<Relationships/>')
        z.writestr('ppt/presentation.xml', '<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"><p:sldIdLst><p:sldId id="256" r:id="rId1"/></p:sldIdLst></p:presentation>')
        z.writestr('ppt/slides/slide1.xml', '<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><p:cSld><p:spTree><p:sp><p:txBody><a:p><a:r><a:t>XXXXXX</a:t></a:r></a:p></p:txBody></p:sp><p:sp><p:txBody><a:p><a:r><a:t>YYYYYY</a:t></a:r></a:p></p:txBody></p:sp></p:spTree></p:cSld></p:sld>')
    result = edit(pptx.getvalue(), {'as_is_text': 'OLD', 'to_be_text': 'NEW'}, {})
    assert isinstance(result, bytes)


# ── Test generate orchestrator ───────────────────────────────────────────────
def test_generators_generate():
    from infrastructure.generators import generate
    pptx = _build_minimal_pptx()
    with patch('infrastructure.generators.fda_perfiles.edit', return_value=pptx):
        with patch('infrastructure.generators.as_is_to_be.edit', return_value=pptx):
            with patch('infrastructure.generators.roadmap.edit', return_value=pptx):
                with patch('infrastructure.generators.consideraciones.edit', return_value=pptx):
                    with patch('infrastructure.generators.cronograma_entregables.edit', return_value=pptx):
                        with patch('infrastructure.generators.cronograma_preview.edit', return_value=pptx):
                            with patch('infrastructure.generators.oferta_economica.edit', return_value=pptx):
                                result = generate(pptx, {'torres_seleccionadas': ['A']}, {})
                                assert isinstance(result, bytes)


# ── Roadmap tests comprehensivos ──────────────────────────────────────────────
def test_roadmap_set_title_text():
    from infrastructure.generators.roadmap import _set_title_text, _clear_shape_text
    sp = etree.fromstring(b'<p:sp xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><p:txBody><a:p><a:r><a:t>Test</a:t></a:r></a:p></p:txBody></p:sp>')
    _set_title_text(sp, "New Title")
    assert "New" in str(etree.tostring(sp))


def test_roadmap_set_shape_text():
    from infrastructure.generators.roadmap import _set_shape_text
    sp = etree.fromstring(b'<p:sp xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><p:txBody><a:p><a:r><a:t>Test</a:t></a:r></a:p></p:txBody></p:sp>')
    _set_shape_text(sp, "New Text", bold=True, size=800)
    assert "New" in str(etree.tostring(sp))


def test_roadmap_edit_full():
    from infrastructure.generators.roadmap import edit
    buf = io.BytesIO()
    xml = (b'<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
           b'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
           b'<p:cSld><p:spTree>'
           b'<p:sp><p:txBody><a:p><a:r><a:t>XXXXXXX</a:t></a:r></a:p></p:txBody></p:sp>'
           b'<p:sp><p:txBody><a:p><a:r><a:t>Desc1</a:t></a:r></a:p></p:txBody></p:sp>'
           b'<p:sp><p:txBody><a:p><a:r><a:t>Desc2</a:t></a:r></a:p></p:txBody></p:sp>'
           b'<p:sp><p:txBody><a:p><a:r><a:t>XXXXXXX</a:t></a:r></a:p></p:txBody></p:sp>'
           b'<p:sp><p:txBody><a:p><a:r><a:t>Desc3</a:t></a:r></a:p></p:txBody></p:sp>'
           b'<p:sp><p:txBody><a:p><a:r><a:t>Desc4</a:t></a:r></a:p></p:txBody></p:sp>'
           b'<p:sp><p:txBody><a:p><a:r><a:t>XXXXXXX</a:t></a:r></a:p></p:txBody></p:sp>'
           b'<p:sp><p:txBody><a:p><a:r><a:t>Desc5</a:t></a:r></a:p></p:txBody></p:sp>'
           b'<p:sp><p:txBody><a:p><a:r><a:t>XXXXXXX</a:t></a:r></a:p></p:txBody></p:sp>'
           b'<p:sp><p:txBody><a:p><a:r><a:t>Desc6</a:t></a:r></a:p></p:txBody></p:sp>'
           b'<p:sp><p:txBody><a:p><a:r><a:t>Desc7</a:t></a:r></a:p></p:txBody></p:sp>'
           b'</p:spTree></p:cSld></p:sld>')
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('ppt/slides/slide5.xml', xml)
        z.writestr('[Content_Types].xml', b'<Types/>')
    result = edit(buf.getvalue(), {'roadmap_phases': [
        {'title': 'T1', 'highlight': 'H1', 'description': 'D1'},
        {'title': 'T2', 'highlight': 'H2', 'description': 'D2'},
        {'title': 'T3', 'highlight': 'H3', 'description': 'D3'},
        {'title': 'T4', 'highlight': 'H4', 'description': 'D4'}
    ]}, {})
    assert isinstance(result, bytes)


# ── Test build_catalog_data completo ───────────────────────────────────────────
def test_repo_build_catalog_data():
    from infrastructure.repositories.catalogo_repository import build_catalog_data
    from unittest.mock import MagicMock
    mock_db = MagicMock()
    mock_torre = MagicMock(id=1, nombre="Backend", nombre_norm="BACKEND")
    mock_perfil = MagicMock(torre_id=1, rol="Dev", descripcion="Dev desc")
    mock_fda = MagicMock(torre_id=1, item="FDA item")
    mock_cons = MagicMock(es_general=True, texto="Consideracion", torre_id=None)
    mock_ent = MagicMock(torre_id=1, item="Entregable")
    
    # Mock query for Torre
    torre_q = MagicMock()
    torre_q.order_by.return_value.all.return_value = [mock_torre]
    
    # Mock query for Perfil
    perf_q = MagicMock()
    perf_q.filter.return_value.all.return_value = [mock_perfil]
    
    # Mock query for fda
    fda_q = MagicMock()
    fda_q.filter.return_value.order_by.return_value.all.return_value = [mock_fda]
    
    # Mock query for consideraciones
    cons_q = MagicMock()
    cons_q.filter.return_value.order_by.return_value.all.return_value = [mock_cons]
    
    # Mock query for entregables
    ent_q = MagicMock()
    ent_q.filter.return_value.order_by.return_value.all.return_value = [mock_ent]
    
    def mock_query(model):
        from infrastructure.models.catalogo import Torre, Perfil, FueraDelAlcance, Consideracion, Entregable
        if model == Perfil:
            return perf_q
        elif model == FueraDelAlcance:
            return fda_q
        elif model == Consideracion:
            return cons_q
        elif model == Entregable:
            return ent_q
        return torre_q
    
    mock_db.query.side_effect = mock_query
    result = build_catalog_data(mock_db)
    assert "fda_db" in result


# ── Test _get_slide_order ─────────────────────────────────────────────────────
def test_get_slide_order_consideraciones():
    from infrastructure.generators.consideraciones import _get_slide_order
    pptx = io.BytesIO()
    with zipfile.ZipFile(pptx, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('ppt/presentation.xml', '<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><p:sldIdLst><p:sldId id="256" r:id="rId1"/><p:sldId id="257" r:id="rId2"/></p:sldIdLst></p:presentation>')
        z.writestr('ppt/_rels/presentation.xml.rels', '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Target="slides/slide1.xml"/><Relationship Id="rId2" Target="slides/slide2.xml"/></Relationships>')
    result = _get_slide_order(pptx.getvalue())
    assert isinstance(result, list)


# ── Test _find_by_title cronograma_preview ───────────────────────────────────
def test_preview_find_by_title():
    from infrastructure.generators.cronograma_preview import _find_by_title
    slide = (
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


# ── Test _add_rel cronograma_preview ───────────────────────────────────────────
def test_preview_add_rel():
    from infrastructure.generators.cronograma_preview import _add_rel
    files = {
        'ppt/slides/slide1.xml': b'<p:sld/>',
        'ppt/_rels/slide1.xml.rels': b'<Relationships/>'
    }
    rid = _add_rel(files, 'ppt/slides/slide1.xml', 'image.png')
    assert rid is not None