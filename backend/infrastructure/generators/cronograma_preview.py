"""
infrastructure/generators/cronograma_preview.py  v4

Inserta la imagen PNG del cronograma en el slide cuyo TÍTULO contenga
"Cronograma" (búsqueda estricta: solo en placeholder de título o shape
en el 30% superior del slide).

Fixes en esta versión:
  - Búsqueda ESTRICTA: solo en ph type=title/ctrTitle o idx=0 (nunca en
    placeholders de cuerpo). Evita falsos positivos como "Entregables"
    que lista "Cronograma" como ítem.
  - Fallback de 2 etapas: (1) shape en zona superior sin ser body,
    (2) índice 11 como último recurso.
  - Aspect ratio calculado dinámicamente desde el PNG real (PIL).
  - Imagen posicionada justo bajo el borde inferior real del título,
    ocupando el máximo ancho útil del slide.
  - Calidad máxima: se inserta el PNG a resolución nativa (SCALE=4).
"""

import io
import os
import re
import zipfile
from lxml import etree

try:
    from PIL import Image as _PILImage
    _HAS_PIL = True
except ImportError:
    _HAS_PIL = False

from infrastructure.generators.cronograma_image import generate_cronograma_image

# ── Namespaces ────────────────────────────────────────────────────────────────
NS_P   = "http://schemas.openxmlformats.org/presentationml/2006/main"
NS_A   = "http://schemas.openxmlformats.org/drawingml/2006/main"
NS_R   = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
NS_CT  = "http://schemas.openxmlformats.org/package/2006/content-types"
REL_IMAGE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/image"

# Dimensiones estándar slide PowerPoint en EMU
SLIDE_W = 9_144_000
SLIDE_H = 6_858_000

# Tipos de placeholder que constituyen el título principal del slide
_TITLE_PH  = {"title", "ctrtitle", "centeredtitle"}
# Tipos que son claramente cuerpo/contenido (nunca son título)
_BODY_PH   = {"body", "obj", "subtitle", "dt", "ftr", "sldnum",
               "pic", "tbl", "chart", "dgm", "media"}


# ── Entry point ───────────────────────────────────────────────────────────────
def edit(pptx_bytes: bytes, config: dict, catalog_data=None) -> bytes:
    excel_data  = config.get("excel_data", {})
    actividades = config.get("actividades") or excel_data.get("actividades", [])
    roles       = config.get("roles")       or excel_data.get("perfiles", [])

    if not actividades or not roles:
        _log(f"Sin datos — act:{len(actividades)} roles:{len(roles)}. Se omite.")
        return pptx_bytes

    actividades = [a.model_dump() if hasattr(a, "model_dump") else dict(a)
                   for a in actividades]
    roles = [r.model_dump() if hasattr(r, "model_dump") else dict(r)
             for r in roles]

    cfg = {
        "actividades":     actividades,
        "roles":           roles,
        "nombre_proyecto": excel_data.get("proyecto",
                           config.get("nombre_proyecto", "Proyecto")),
        "torre":           config.get("torre", ""),
        "id_proyecto":     config.get("id_proyecto", ""),
        "fecha":           config.get("fecha", ""),
        "horas_semanales": config.get("horas_semanales", 42),
    }

    # ── Generar PNG ───────────────────────────────────────────────────────
    try:
        _log("Generando PNG del cronograma…")
        png_bytes = generate_cronograma_image(cfg)
        _log(f"PNG generado: {len(png_bytes)} bytes")
    except Exception as e:
        _log(f"Error generando PNG: {e}")
        import traceback; traceback.print_exc()
        return pptx_bytes

    # ── Calcular aspect ratio real desde el PNG ───────────────────────────
    aspect_w_over_h = _png_aspect(png_bytes)
    _log(f"Aspect ratio PNG: {aspect_w_over_h:.3f}")

    # ── Leer ZIP ──────────────────────────────────────────────────────────
    try:
        with zipfile.ZipFile(io.BytesIO(pptx_bytes)) as z:
            files = {n: z.read(n) for n in z.namelist()}
    except Exception as e:
        _log(f"Error leyendo ZIP: {e}"); return pptx_bytes

    try:
        slides = _slides_order(files)
        _log(f"Total slides: {len(slides)}")

        # ── Localizar slide por título ─────────────────────────────────
        target = _find_by_title(files, slides, "cronograma")
        if not target:
            idx    = 11 if len(slides) > 11 else len(slides) - 1
            target = slides[idx]
            _log(f"No encontrado por título → fallback slide {idx+1}: {target}")
        else:
            _log(f"Slide objetivo: {target}")

        # ── Detectar borde inferior del título ─────────────────────────
        title_bottom = _title_bottom_emu(files.get(target, b""))
        _log(f"title_bottom: {title_bottom} EMU  "
             f"({title_bottom/SLIDE_H*100:.1f}% del alto)")

        # ── Insertar imagen ────────────────────────────────────────────
        mid   = _next_img_id(files)
        iname = f"image{mid}.png"
        files[f"ppt/media/{iname}"] = png_bytes
        _register_ct(files)
        rid = _add_rel(files, target, iname)
        _log(f"Relación: {rid} → {iname}")

        files[target] = _insert_pic(files[target], rid,
                                    title_bottom, aspect_w_over_h)
        _log("Imagen insertada correctamente.")

        out = io.BytesIO()
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
            for n, d in files.items():
                z.writestr(n, d)
        return out.getvalue()

    except Exception as e:
        _log(f"Error insertando imagen: {e}")
        import traceback; traceback.print_exc()
        return pptx_bytes


# ── Orden de slides ───────────────────────────────────────────────────────────
def _slides_order(files: dict) -> list:
    rels    = etree.fromstring(files.get("ppt/_rels/presentation.xml.rels", b""))
    prs     = etree.fromstring(files.get("ppt/presentation.xml", b""))
    rid_map = {r.attrib["Id"]: r.attrib["Target"]
               for r in rels.findall(f"{{{NS_REL}}}Relationship")}
    out = []
    for sld in prs.findall(f".//{{{NS_P}}}sldId"):
        rid = sld.attrib.get(f"{{{NS_R}}}id", "")
        tgt = rid_map.get(rid, "")
        if tgt:
            out.append(tgt if tgt.startswith("ppt/") else "ppt/" + tgt)
    return out


# ── Búsqueda ESTRICTA por título ──────────────────────────────────────────────
def _find_by_title(files: dict, slides: list, keyword: str) -> str | None:
    """
    Busca 'keyword' SOLO en:
      1. Placeholders con type ∈ {title, ctrTitle, centeredTitle}
      2. Placeholder con idx=0 y type vacío (título sin tipo explícito)
      3. Shape libre (sin ph) cuya posición Y < 30% del alto del slide
         y que no sea placeholder de cuerpo.

    NO busca en placeholders de cuerpo/contenido, evitando falsos
    positivos como slides de "Entregables" que listen "Cronograma".
    """
    kw = keyword.lower()

    for path in slides:
        raw = files.get(path, b"")
        try:
            root = etree.fromstring(raw)
        except Exception:
            continue

        for sp in root.findall(f".//{{{NS_P}}}sp"):
            ph     = sp.find(f".//{{{NS_P}}}ph")
            ph_type = ""
            ph_idx  = "-1"
            if ph is not None:
                ph_type = ph.attrib.get("type", "").lower()
                ph_idx  = ph.attrib.get("idx",  "-1")

            # Determinar si es candidato a título
            is_explicit_title = ph_type in _TITLE_PH
            is_idx0_title     = (ph is not None
                                 and ph_type == ""
                                 and ph_idx in ("0", ""))
            is_free_shape_top = (ph is None and _shape_y_fraction(sp) < 0.30)

            # Excluir explícitamente cuerpos
            is_body = ph_type in _BODY_PH or (
                ph is not None and ph_idx not in ("0", "", "-1")
            )

            if is_body:
                continue
            if not (is_explicit_title or is_idx0_title or is_free_shape_top):
                continue

            texts = " ".join(t.text or "" for t in sp.iter(f"{{{NS_A}}}t")).lower()
            if kw in texts:
                _log(f"  '{texts.strip()[:60]}' → {path}")
                return path

    return None


def _shape_y_fraction(sp) -> float:
    """Devuelve la posición Y de la shape como fracción del alto del slide."""
    off = sp.find(f".//{{{NS_A}}}off")
    if off is None:
        return 1.0
    try:
        return int(off.attrib.get("y", SLIDE_H)) / SLIDE_H
    except (ValueError, TypeError):
        return 1.0


# ── Borde inferior real del título ───────────────────────────────────────────
def _title_bottom_emu(slide_xml: bytes) -> int:
    """
    Lee la geometría del placeholder de título y retorna su Y + cy en EMU.
    - Si el título tiene xfrm propio → lo usa.
    - Si el título hereda del layout (sin xfrm) → usa fallback conservador.
    - El valor devuelto se limita a máximo 35% del alto del slide para
      evitar que un decorado grande aplaste la imagen.
    Fallback: 22% del alto del slide.
    """
    MAX_TITLE_FRAC = 0.35          # nunca más del 35% para el título
    fallback       = int(SLIDE_H * 0.22)
    cap            = int(SLIDE_H * MAX_TITLE_FRAC)

    if not slide_xml:
        return fallback
    try:
        root = etree.fromstring(slide_xml)
        for sp in root.findall(f".//{{{NS_P}}}sp"):
            ph = sp.find(f".//{{{NS_P}}}ph")
            if ph is None:
                continue
            pt = ph.attrib.get("type", "").lower()
            pi = ph.attrib.get("idx",  "-1")
            if not (pt in _TITLE_PH or (pt == "" and pi in ("0", ""))):
                continue
            xfrm = sp.find(f".//{{{NS_A}}}xfrm")
            if xfrm is None:
                # Placeholder hereda geometría del layout → usar fallback
                return fallback
            off = xfrm.find(f"{{{NS_A}}}off")
            ext = xfrm.find(f"{{{NS_A}}}ext")
            if off is not None and ext is not None:
                y  = int(off.attrib.get("y",  0))
                cy = int(ext.attrib.get("cy", 0))
                if cy > 0:
                    return min(y + cy, cap)
    except Exception:
        pass
    return fallback


# ── Aspect ratio del PNG ──────────────────────────────────────────────────────
def _png_aspect(png_bytes: bytes) -> float:
    """Retorna ancho/alto real del PNG. Fallback: 3.1 (valor típico del cronograma)."""
    if _HAS_PIL:
        try:
            img = _PILImage.open(io.BytesIO(png_bytes))
            w, h = img.size
            return w / h if h else 3.1
        except Exception:
            pass
    return 3.1


# ── Content-Type ──────────────────────────────────────────────────────────────
def _register_ct(files: dict):
    ct = etree.fromstring(files["[Content_Types].xml"])
    for el in ct.findall(f"{{{NS_CT}}}Default"):
        if el.attrib.get("Extension", "").lower() == "png":
            return
    etree.SubElement(ct, f"{{{NS_CT}}}Default",
                     {"Extension": "png", "ContentType": "image/png"})
    files["[Content_Types].xml"] = etree.tostring(
        ct, xml_declaration=True, encoding="UTF-8", standalone=True)


# ── Relación de imagen en el slide ───────────────────────────────────────────
def _add_rel(files: dict, slide_path: str, img_name: str) -> str:
    sdir  = os.path.dirname(slide_path)
    sbase = os.path.basename(slide_path)
    rpath = f"{sdir}/_rels/{sbase}.rels"

    if rpath in files and files[rpath].strip():
        rroot = etree.fromstring(files[rpath])
    else:
        rroot = etree.Element(f"{{{NS_REL}}}Relationships")

    ids = [int(m.group(1))
           for r in rroot.findall(f"{{{NS_REL}}}Relationship")
           for m in [re.search(r"(\d+)$", r.attrib.get("Id", ""))] if m]
    rid = f"rId{max(ids, default=0) + 1}"

    etree.SubElement(rroot, f"{{{NS_REL}}}Relationship", {
        "Id":     rid,
        "Type":   REL_IMAGE,
        "Target": f"../media/{img_name}",
    })
    files[rpath] = etree.tostring(
        rroot, xml_declaration=True, encoding="UTF-8", standalone=True)
    return rid


# ── Insertar <p:pic> en el slide ─────────────────────────────────────────────
def _insert_pic(slide_xml: bytes, rel_id: str,
                title_bottom: int, aspect_w_over_h: float) -> bytes:
    """
    Coloca la imagen justo bajo el borde inferior del título.
    Ocupa el MÁXIMO ancho y alto disponible respetando el aspect ratio real del PNG.
    """
    root   = etree.fromstring(slide_xml)
    spTree = root.find(f".//{{{NS_P}}}spTree")
    if spTree is None:
        return slide_xml

    H_MARGIN = int(SLIDE_W * 0.015)   # margen horizontal (1.5%)
    V_GAP    = int(SLIDE_H * 0.008)   # espacio mínimo bajo el título (0.8%)
    V_MARGIN = int(SLIDE_H * 0.010)   # margen inferior (1.0%)

    # Área disponible para la imagen
    img_x    = H_MARGIN
    avail_w  = SLIDE_W - 2 * H_MARGIN
    img_y    = title_bottom + V_GAP
    avail_h  = SLIDE_H - img_y - V_MARGIN

    if avail_h <= 0:
        _log("WARN: no hay espacio bajo el título, usando 60% del slide")
        img_y   = int(SLIDE_H * 0.30)
        avail_h = int(SLIDE_H * 0.65)

    # Ajustar manteniendo aspect ratio: llenar el máximo posible
    # Primero intentar ancho completo
    img_w = avail_w
    img_h = int(img_w / aspect_w_over_h)

    # Si el alto resultante excede el espacio, acotar por alto
    if img_h > avail_h:
        img_h = avail_h
        img_w = int(img_h * aspect_w_over_h)
        # Centrar horizontalmente
        img_x = (SLIDE_W - img_w) // 2

    _log(f"Imagen: x={img_x} y={img_y} w={img_w} h={img_h} EMU")
    _log(f"  → {img_w/914400*2.54:.1f}cm × {img_h/914400*2.54:.1f}cm")
    _log(f"  → Y: {img_y/SLIDE_H*100:.1f}% – {(img_y+img_h)/SLIDE_H*100:.1f}%")

    pic = etree.fromstring(
        f'<p:pic xmlns:p="{NS_P}" xmlns:a="{NS_A}" xmlns:r="{NS_R}">'
        f'  <p:nvPicPr>'
        f'    <p:cNvPr id="9001" name="CronogramaImg"'
        f'             descr="Cronograma del Proyecto"/>'
        f'    <p:cNvPicPr><a:picLocks noChangeAspect="1"/></p:cNvPicPr>'
        f'    <p:nvPr/>'
        f'  </p:nvPicPr>'
        f'  <p:blipFill>'
        f'    <a:blip r:embed="{rel_id}"/>'
        f'    <a:stretch><a:fillRect/></a:stretch>'
        f'  </p:blipFill>'
        f'  <p:spPr>'
        f'    <a:xfrm>'
        f'      <a:off x="{img_x}" y="{img_y}"/>'
        f'      <a:ext cx="{img_w}" cy="{img_h}"/>'
        f'    </a:xfrm>'
        f'    <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>'
        f'  </p:spPr>'
        f'</p:pic>'
    )
    spTree.append(pic)
    return etree.tostring(root, xml_declaration=True,
                          encoding="UTF-8", standalone=True)


# ── ID de imagen siguiente ────────────────────────────────────────────────────
def _next_img_id(files: dict) -> int:
    mx = 0
    for p in files:
        m = re.search(r"ppt/media/image(\d+)", p)
        if m:
            mx = max(mx, int(m.group(1)))
    return mx + 1


def _log(msg: str):
    print(f"[CRONOGRAMA_PREVIEW] {msg}")
