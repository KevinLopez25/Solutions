"""Pruebas del generador de tarjeta comercial (2 slides tras el slide 13)."""
import io
import posixpath
import re
import zipfile

from lxml import etree

from infrastructure.generators import tarjeta_comercial

P = "http://schemas.openxmlformats.org/presentationml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
SLIDE_CT = "application/vnd.openxmlformats-officedocument.presentationml.slide+xml"
LAYOUT_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout"
IMAGE_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/image"


def _slide_xml(num, pic_rid=None, hlink_rid=None, bad_rid=None, texto=None):
    """Slide realista: el layout SOLO se declara en el .rels, nunca en el XML."""
    pic = ""
    if pic_rid:
        pic = (
            '<p:pic><p:nvPicPr><p:cNvPr id="5" name="logo"/>'
            '<p:cNvPicPr/><p:nvPr/></p:nvPicPr>'
            f'<p:blipFill><a:blip r:embed="{pic_rid}"/>'
            '<a:stretch><a:fillRect/></a:stretch></p:blipFill>'
            '<p:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="1000" cy="1000"/></a:xfrm>'
            '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr></p:pic>'
        )
    rpr = ""
    if hlink_rid:
        rpr = f'<a:rPr><a:hlinkClick r:id="{hlink_rid}"/></a:rPr>'
    bad = ""
    if bad_rid:
        bad = f'<p:custDataLst><p:custData r:id="{bad_rid}"/></p:custDataLst>'
    txt = texto if texto is not None else f"Contenido {num}"
    return (
        f'<p:sld xmlns:p="{P}" xmlns:r="{R}" '
        'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
        '<p:cSld><p:spTree>'
        '<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
        '<p:grpSpPr/>'
        f'<p:sp><p:nvSpPr><p:cNvPr id="2" name="slide{num}-shape"/>'
        f'<p:cNvSpPr/><p:nvPr/>{bad}</p:nvSpPr>'
        '<p:spPr/><p:txBody><a:bodyPr/><a:lstStyle/>'
        f'<a:p><a:r>{rpr}<a:t>{txt}</a:t></a:r></a:p>'
        '</p:txBody></p:sp>'
        f'{pic}'
        '</p:spTree></p:cSld></p:sld>'
    )


def _rels_xml(entries: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<Relationships xmlns="{NS_REL}">{entries}</Relationships>'
    )


def _build_pptx(n_slides: int, metodologia_en: int | None = None) -> bytes:
    """Deck destino mínimo y válido. `metodologia_en` = número de slide que
    contiene el texto 'Metodología Ágil' (para probar la detección dinámica)."""
    overrides = "".join(
        f'<Override PartName="/ppt/slides/slide{i}.xml" ContentType="{SLIDE_CT}"/>'
        for i in range(1, n_slides + 1)
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<Types xmlns="{CT_NS}">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        f'{overrides}'
        '<Override PartName="/ppt/presentation.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>'
        '</Types>'
    )
    rel_entries = (
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>'
        + "".join(
            f'<Relationship Id="rId{i + 1}" Type="{R}/slide" Target="slides/slide{i}.xml"/>'
            for i in range(1, n_slides + 1)
        )
    )
    sld_ids = "".join(
        f'<p:sldId id="{i + 256}" r:id="rId{i + 2}"/>' for i in range(n_slides)
    )
    presentation = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<p:presentation xmlns:p="{P}" xmlns:r="{R}">'
        f'<p:sldIdLst>{sld_ids}</p:sldIdLst>'
        '<p:sldSz cx="9144000" cy="6858000"/></p:presentation>'
    )
    layout_entry = (
        f'<Relationship Id="rIdLayout" Type="{LAYOUT_REL}" '
        'Target="../slideLayouts/slideLayout1.xml"/>'
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types.encode())
        z.writestr("ppt/_rels/presentation.xml.rels", _rels_xml(rel_entries).encode())
        z.writestr("ppt/presentation.xml", presentation.encode())
        for i in range(1, n_slides + 1):
            texto = "Metodología Ágil" if i == metodologia_en else None
            z.writestr(f"ppt/slides/slide{i}.xml",
                       _slide_xml(i, texto=texto).encode())
            z.writestr(f"ppt/slides/_rels/slide{i}.xml.rels",
                       _rels_xml(layout_entry).encode())
    return buf.getvalue()


def _slide_count(pptx_bytes: bytes) -> int:
    with zipfile.ZipFile(io.BytesIO(pptx_bytes)) as z:
        return sum(1 for n in z.namelist()
                   if n.startswith("ppt/slides/slide") and n.endswith(".xml"))


def _order_of(pptx_bytes: bytes) -> list[int]:
    with zipfile.ZipFile(io.BytesIO(pptx_bytes)) as z:
        rels_root = etree.fromstring(z.read("ppt/_rels/presentation.xml.rels"))
        rid_map = {r.attrib["Id"]: r.attrib["Target"]
                   for r in rels_root.findall(f"{{{NS_REL}}}Relationship")}
        prs = etree.fromstring(z.read("ppt/presentation.xml"))
        ns = {"p": P, "r": R}
        return [
            int(re.search(r"slide(\d+)", rid_map[s.attrib[f"{{{R}}}id"]]).group(1))
            for s in prs.find(".//p:sldIdLst", ns)
        ]


def _slide_present(pptx_bytes: bytes, fragment: str) -> bool:
    with zipfile.ZipFile(io.BytesIO(pptx_bytes)) as z:
        for n in z.namelist():
            if n.startswith("ppt/slides/slide") and n.endswith(".xml"):
                if fragment.encode() in z.read(n):
                    return True
    return False


def _patch_settings(monkeypatch, tmp_path):
    from core import config as core_config

    class FakeSettings:
        templates_path = tmp_path

    monkeypatch.setattr(core_config, "settings", FakeSettings())


# ═══════════════════════════ tests básicos ═══════════════════════════

def test_sin_tarjeta_devuelve_igual():
    pptx = _build_pptx(22, metodologia_en=19)
    assert tarjeta_comercial.edit(pptx, {}, {}) == pptx


def test_inserta_dos_slides_tras_metodologia(tmp_path, monkeypatch):
    """Los 2 slides van justo después del slide de 'Metodología Ágil'."""
    _patch_settings(monkeypatch, tmp_path)
    destino = _build_pptx(22, metodologia_en=19)
    carpeta = tmp_path / "tarjetas_comerciales"
    carpeta.mkdir()
    (carpeta / "Pepito Perez.pptx").write_bytes(_build_pptx(2))

    out = tarjeta_comercial.edit(
        destino, {"tarjeta_comercial": "Pepito Perez"}, {})

    assert _slide_count(out) == 24
    order = _order_of(out)
    assert order[18] == 19                    # Metodología Ágil intacta
    assert sorted(order[19:21]) == [23, 24]   # los 2 nuevos, justo después
    assert _slide_present(out, "Metodolog")


def test_fallback_sin_metodologia(tmp_path, monkeypatch):
    """Sin slide de Metodología Ágil: usa la posición de respaldo (slide 19)."""
    _patch_settings(monkeypatch, tmp_path)
    destino = _build_pptx(25)
    carpeta = tmp_path / "tarjetas_comerciales"
    carpeta.mkdir()
    (carpeta / "Pepito Perez.pptx").write_bytes(_build_pptx(2))

    out = tarjeta_comercial.edit(
        destino, {"tarjeta_comercial": "Pepito Perez"}, {})

    order = _order_of(out)
    assert order[18] == 19
    assert sorted(order[19:21]) == [26, 27]


def test_deck_mas_corto_agrega_al_final(tmp_path, monkeypatch):
    """Si el deck es más corto que la posición, se agregan al final."""
    _patch_settings(monkeypatch, tmp_path)
    destino = _build_pptx(10)
    carpeta = tmp_path / "tarjetas_comerciales"
    carpeta.mkdir()
    (carpeta / "Pepito Perez.pptx").write_bytes(_build_pptx(2))

    out = tarjeta_comercial.edit(
        destino, {"tarjeta_comercial": "Pepito Perez"}, {})

    order = _order_of(out)
    assert len(order) == 12
    assert sorted(order[10:12]) == [11, 12]


def test_busca_por_fragmento(tmp_path, monkeypatch):
    _patch_settings(monkeypatch, tmp_path)
    destino = _build_pptx(22, metodologia_en=19)
    carpeta = tmp_path / "tarjetas_comerciales"
    carpeta.mkdir()
    (carpeta / "Pepito Perez.pptx").write_bytes(_build_pptx(2))

    out = tarjeta_comercial.edit(destino, {"tarjeta_comercial": "pepi"}, {})
    assert _slide_count(out) == 24


def test_busca_en_carpeta_del_pais(tmp_path, monkeypatch):
    _patch_settings(monkeypatch, tmp_path)
    destino = _build_pptx(22, metodologia_en=19)
    base = tmp_path / "tarjetas_comerciales"
    (base / "colombia").mkdir(parents=True)
    (base / "colombia" / "Ana Ruiz.pptx").write_bytes(_build_pptx(2))
    (base / "peru").mkdir()
    (base / "peru" / "Otro Comercial.pptx").write_bytes(_build_pptx(2))

    out = tarjeta_comercial.edit(destino, {
        "tarjeta_comercial": "Ana Ruiz",
        "tarjeta_comercial_pais": "colombia",
    }, {})

    assert _slide_count(out) == 24
    assert _order_of(out)[18] == 19


# ══════════ test anti-corrupción: relaciones 100% resueltas ══════════

def _build_card_pptx() -> bytes:
    """
    Tarjeta realista de 2 slides:
      slide1: imagen (rId100), hyperlink externo (rId101) y una referencia
              huérfana a notesSlide (rId102: rel declarada SIN parte física).
      slide2: plano.
    """
    s1 = _slide_xml(1, pic_rid="rId100", hlink_rid="rId101", bad_rid="rId102")
    s2 = _slide_xml(2)
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<Types xmlns="{CT_NS}">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        f'<Override PartName="/ppt/slides/slide1.xml" ContentType="{SLIDE_CT}"/>'
        f'<Override PartName="/ppt/slides/slide2.xml" ContentType="{SLIDE_CT}"/>'
        '<Override PartName="/ppt/presentation.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>'
        '</Types>'
    )
    prs_rels = _rels_xml(
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>'
        f'<Relationship Id="rId2" Type="{R}/slide" Target="slides/slide1.xml"/>'
        f'<Relationship Id="rId3" Type="{R}/slide" Target="slides/slide2.xml"/>'
    )
    presentation = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<p:presentation xmlns:p="{P}" xmlns:r="{R}">'
        '<p:sldIdLst><p:sldId id="256" r:id="rId2"/><p:sldId id="257" r:id="rId3"/></p:sldIdLst>'
        '<p:sldSz cx="12192000" cy="6858000"/></p:presentation>'
    )
    layout = (f'<Relationship Id="rIdLayout" Type="{LAYOUT_REL}" '
              'Target="../slideLayouts/slideLayout1.xml"/>')
    rels1 = _rels_xml(
        layout
        + f'<Relationship Id="rId100" Type="{R}/image" Target="../media/logo_tarjeta.png"/>'
        + f'<Relationship Id="rId101" Type="{R}/hyperlink" Target="https://www.periferia.com" TargetMode="External"/>'
        + f'<Relationship Id="rId102" Type="{R}/notesSlide" Target="../notesSlides/notesSlide1.xml"/>'
    )
    rels2 = _rels_xml(layout)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types.encode())
        z.writestr("ppt/_rels/presentation.xml.rels", prs_rels.encode())
        z.writestr("ppt/presentation.xml", presentation.encode())
        z.writestr("ppt/slides/slide1.xml", s1.encode())
        z.writestr("ppt/slides/slide2.xml", s2.encode())
        z.writestr("ppt/slides/_rels/slide1.xml.rels", rels1.encode())
        z.writestr("ppt/slides/_rels/slide2.xml.rels", rels2.encode())
        z.writestr("ppt/media/logo_tarjeta.png", b"\x89PNG\r\n\x1a\nfakepng")
    return buf.getvalue()


def _read(dest_bytes: bytes, name: str) -> bytes:
    with zipfile.ZipFile(io.BytesIO(dest_bytes)) as z:
        return z.read(name)


def test_tarjeta_sin_reparacion(tmp_path, monkeypatch):
    """
    Regression del bug 'PowerPoint pide reparar y pierde las imágenes':
      1. El slide nuevo SIEMPRE tiene relación slideLayout (los slides reales
         no traen <p:sldLayoutId> en el XML).
      2. No queda NINGUNA referencia r:* sin relación en el slide nuevo.
      3. Cada imagen apunta a un media existente en el deck destino.
      4. El hyperlink externo se conserva; la rel huérfana (notesSlide) se va.
      5. El media se copió y existe el Default png en [Content_Types].xml.
    """
    _patch_settings(monkeypatch, tmp_path)
    destino = _build_pptx(15)
    base = tmp_path / "tarjetas_comerciales" / "colombia"
    base.mkdir(parents=True)
    (base / "Pepito Perez.pptx").write_bytes(_build_card_pptx())

    out = tarjeta_comercial.edit(destino, {
        "tarjeta_comercial": "Pepito Perez",
        "tarjeta_comercial_pais": "colombia",
    }, {})

    assert _slide_count(out) == 17
    order = _order_of(out)
    nuevos = [order[13], order[14]]

    for num in nuevos:
        rels = etree.fromstring(
            _read(out, f"ppt/slides/_rels/slide{num}.xml.rels"))
        slide_xml = etree.fromstring(
            _read(out, f"ppt/slides/slide{num}.xml"))
        ids = {r.get("Id"): r for r in rels.findall(f"{{{NS_REL}}}Relationship")}

        # 1) Relación slideLayout SIEMPRE presente.
        assert any(r.get("Type") == LAYOUT_REL for r in ids.values()), num

        # 2) Cero referencias r:* huérfanas en el XML.
        for el in slide_xml.iter():
            for key, val in el.attrib.items():
                if key.startswith("{%s}" % R):
                    assert val in ids, f"ref huerfana {val} en slide{num}"

        # 3) Cada imagen apunta a un media existente en el deck.
        names = set()
        with zipfile.ZipFile(io.BytesIO(out)) as z:
            names = set(z.namelist())
        for r in ids.values():
            if r.get("Type") == IMAGE_REL:
                target = posixpath.normpath("ppt/slides/" + (r.get("Target") or ""))
                assert target in names, target

    # 4) Hyperlink externo conservado; notesSlide huérfano eliminado.
    s_rels = _read(out, f"ppt/slides/_rels/slide{nuevos[0]}.xml.rels").decode()
    assert "hyperlink" in s_rels and 'TargetMode="External"' in s_rels
    assert "notesSlide" not in s_rels

    # 5) Media copiado + Default png registrado.
    with zipfile.ZipFile(io.BytesIO(out)) as z:
        media = [n for n in z.namelist()
                 if n.startswith("ppt/media/tarjeta_PEPITO_PEREZ_1_")]
    assert media, "no se copio la imagen de la tarjeta"
    assert 'Extension="png"' in _read(out, "[Content_Types].xml").decode()