"""
Tests para infrastructure/generators/cronograma_preview.py
"""
import io
import zipfile
import pytest
from unittest.mock import patch, MagicMock
from lxml import etree

from infrastructure.generators.cronograma_preview import (
    _slides_order, _find_by_title, _title_bottom_emu,
    _png_aspect, _register_ct, _add_rel, _insert_pic,
    _next_img_id, edit,
)


SAMPLE_SLIDE = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
    'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
    '<p:cSld><p:spTree>'
    '<p:sp><p:nvSpPr><p:cNvPr name="Title 1"/></p:nvSpPr>'
    '<p:spPr><a:xfrm><a:off x="100" y="100"/><a:ext cx="1000" cy="500"/></a:xfrm></p:spPr>'
    '<p:txBody><a:p><a:r><a:t>Cronograma del Proyecto</a:t></a:r></a:p></p:txBody></p:sp>'
    '</p:spTree></p:cSld></p:sld>'
)


def _build_pptx(slide_xml_map):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zout:
        rels_xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' \
                   '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        for i, (path, _) in enumerate(slide_xml_map.items(), 1):
            rels_xml += f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/presentationml/2006/main/slide" Target="{path.replace("ppt/", "")}"/>'
        rels_xml += '</Relationships>'
        zout.writestr('ppt/_rels/presentation.xml.rels', rels_xml.encode())
        sld_ids = ''.join(f'<p:sldId id="{256 + i}" r:id="rId{i + 1}"/>' for i in range(len(slide_xml_map)))
        prs_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            f'<p:sldIdLst>{sld_ids}</p:sldIdLst></p:presentation>'
        )
        zout.writestr('ppt/presentation.xml', prs_xml.encode())
        zout.writestr('[Content_Types].xml',
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>')
        for path, xml in slide_xml_map.items():
            zout.writestr(path, xml.encode() if isinstance(xml, str) else xml)
    return buf.getvalue()


class TestSlidesOrder:
    def test_slides_order(self):
        files = {
            'ppt/_rels/presentation.xml.rels': (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/presentationml/2006/main/slide" Target="slides/slide1.xml"/>'
                '</Relationships>'
            ).encode(),
            'ppt/presentation.xml': (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
                'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
                '<p:sldIdLst><p:sldId id="256" r:id="rId1"/></p:sldIdLst></p:presentation>'
            ).encode(),
        }
        order = _slides_order(files)
        assert order == ['ppt/slides/slide1.xml']


class TestFindByTitle:
    def test_find_by_title_found(self):
        files = {'ppt/slides/slide1.xml': SAMPLE_SLIDE.encode()}
        result = _find_by_title(files, ['ppt/slides/slide1.xml'], 'cronograma')
        assert result == 'ppt/slides/slide1.xml'

    def test_find_by_title_not_found(self):
        other_slide = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
            '<p:cSld><p:spTree/></p:cSld></p:sld>'
        )
        files = {'ppt/slides/slide1.xml': other_slide.encode()}
        result = _find_by_title(files, ['ppt/slides/slide1.xml'], 'nonexistent')
        assert result is None


class TestTitleBottomEmu:
    def test_title_bottom_emu_with_ph(self):
        slide = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
            'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
            '<p:cSld><p:spTree>'
            '<p:sp><p:nvSpPr><p:cNvPr name="Title"/></p:nvSpPr>'
            '<p:spPr><a:xfrm><a:off x="100" y="200"/><a:ext cx="1000" cy="500"/></a:xfrm></p:spPr>'
            '<p:txBody><a:p><a:r><a:t>Title</a:t></a:r></a:p></p:txBody></p:sp>'
            '</p:spTree></p:cSld></p:sld>'
        )
        bottom = _title_bottom_emu(slide.encode())
        assert bottom > 0

    def test_title_bottom_emu_fallback(self):
        bottom = _title_bottom_emu(None)
        assert bottom > 0


class TestPngAspect:
    def test_png_aspect_fallback(self):
        ratio = _png_aspect(b"not a png")
        assert ratio == 3.1


class TestRegisterCt:
    def test_register_ct_adds_png(self):
        files = {
            '[Content_Types].xml': (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>'
            ).encode()
        }
        _register_ct(files)
        assert b'image/png' in files['[Content_Types].xml']


class TestAddRel:
    def test_add_rel(self):
        pptx = _build_pptx({'ppt/slides/slide1.xml': SAMPLE_SLIDE})
        with zipfile.ZipFile(io.BytesIO(pptx)) as z:
            files = {n: z.read(n) for n in z.namelist()}
        rid = _add_rel(files, 'ppt/slides/slide1.xml', 'image1.png')
        assert rid.startswith('rId')


class TestNextImgId:
    def test_next_img_id(self):
        files = {'ppt/media/image1.png': b'', 'ppt/media/image5.png': b''}
        assert _next_img_id(files) == 6

    def test_next_img_id_no_images(self):
        assert _next_img_id({}) == 1


class TestInsertPic:
    def test_insert_pic(self):
        result = _insert_pic(SAMPLE_SLIDE.encode(), 'rId1', 500000, 3.1)
        assert b'CronogramaImg' in result


class TestEdit:
    def test_edit_no_activities_returns_original(self):
        pptx = _build_pptx({'ppt/slides/slide1.xml': SAMPLE_SLIDE})
        result = edit(pptx, {})
        assert result == pptx

    @patch('infrastructure.generators.cronograma_preview._png_aspect')
    @patch('infrastructure.generators.cronograma_preview.generate_cronograma_image')
    def test_edit_with_data(self, mock_gen, mock_aspect):
        mock_gen.return_value = b"fake-png"
        mock_aspect.return_value = 3.1
        pptx = _build_pptx({'ppt/slides/slide1.xml': SAMPLE_SLIDE})
        config = {
            'actividades': [{'torre': 'A', 'horas': 40, 'personas': 1}],
            'roles': [{'perfil': 'Dev', 'personas': 1}],
            'excel_data': {'proyecto': 'Test', 'actividades': [], 'perfiles': []},
        }
        result = edit(pptx, config)
        assert isinstance(result, bytes)

    @patch('infrastructure.generators.cronograma_preview._png_aspect')
    @patch('infrastructure.generators.cronograma_preview.generate_cronograma_image')
    def test_edit_with_excel_data(self, mock_gen, mock_aspect):
        mock_gen.return_value = b"fake-png"
        mock_aspect.return_value = 3.1
        pptx = _build_pptx({'ppt/slides/slide1.xml': SAMPLE_SLIDE})
        config = {
            'actividades': [],
            'roles': [],
            'excel_data': {
                'proyecto': 'Test',
                'actividades': [{'torre': 'A', 'horas': 40, 'personas': 1}],
                'perfiles': [{'perfil': 'Dev', 'personas': 1}],
            },
        }
        result = edit(pptx, config)
        assert isinstance(result, bytes)