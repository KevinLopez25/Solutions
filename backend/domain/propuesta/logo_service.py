"""
Centralized logo replacement for all PPTX proposal templates.

Placeholder types:
  1. Slide 1  : 'Rectángulo redondeado' frame (portada)
  2. Any slide: shapes whose full text is <<Logo Cliente>> or <<Logo del Cliente>>
  3. Any slide: text runs exactly matching ^(X{5,}|x{5,})$ (standalone logo runs)
  4. Any slide: text runs with an embedded x-sequence in mixed text
               (e.g. 'La propuesta se presenta de acuerdo con xxxx...')
"""

import io
import posixpath
import re
import zipfile

from lxml import etree

_NS_P    = 'http://schemas.openxmlformats.org/presentationml/2006/main'
_NS_A    = 'http://schemas.openxmlformats.org/drawingml/2006/main'
_NS_R    = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
_NS_RELS = 'http://schemas.openxmlformats.org/package/2006/relationships'
_REL_IMG = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/image'

_MIME_TO_EXT = {
    'image/png': 'png', 'image/jpeg': 'jpg', 'image/jpg': 'jpg',
    'image/gif': 'gif', 'image/webp': 'webp', 'image/svg+xml': 'svg',
}

_DEDICATED      = frozenset({'<<Logo Cliente>>', '<<Logo del Cliente>>'})
_X_RUN_RE       = re.compile(r'^(X{5,}|x{5,})$')
# Only match X-sequences that are NOT preceded/followed by another letter (avoids Xxxxxxx content placeholders)
_X_EMBED_RE     = re.compile(r'(?<![A-Za-z])(X{5,}|x{5,})(?![A-Za-z])')
_PROP_TEXT_RE   = re.compile(r'^La propuesta se presenta de acuerdo con', re.IGNORECASE)
_PROP_REPL      = 'La propuesta se presenta de acuerdo con el requerimiento definido por '
_PORTADA_SP     = 'Rectángulo redondeado'
_FILL_TAGS      = ['solidFill', 'gradFill', 'noFill', 'blipFill', 'pattFill', 'grpFill']

_INLINE_CX       = 914_400
_INLINE_CY       = 304_800
_LINE_HEIGHT_EMU = 280_000


def _sanitize_empty_runs(files: dict) -> None:
    """Remove <a:r> runs that contain only an empty <a:t/> — PowerPoint rejects them."""
    slide_re = re.compile(r'^ppt/slides/slide\d+\.xml$')
    for path in list(files):
        if not slide_re.match(path):
            continue
        root = etree.fromstring(files[path])
        changed = False
        for t in root.findall(f'.//{{{_NS_A}}}t'):
            if (t.text or '').strip():
                continue
            parent_r = t.getparent()
            if parent_r is None or parent_r.tag != f'{{{_NS_A}}}r':
                continue
            grandparent = parent_r.getparent()
            if grandparent is not None:
                grandparent.remove(parent_r)
                changed = True
        if changed:
            files[path] = _xml_bytes(root)


def _to_png(logo_bytes: bytes, logo_mime: str) -> bytes:
    """Convierte cualquier imagen a PNG para máxima compatibilidad con PowerPoint."""
    if logo_mime == 'image/svg+xml':
        try:
            import cairosvg
            return cairosvg.svg2png(bytestring=logo_bytes)
        except ImportError:
            pass
        # Sin cairosvg: embeber SVG directo (PowerPoint 2016+ lo soporta)
        return logo_bytes
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(logo_bytes)).convert('RGBA')
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        return buf.getvalue()
    except Exception:
        return logo_bytes


def replace_logo_in_pptx(pptx_bytes: bytes, logo_bytes: bytes, logo_mime: str) -> bytes:
    """Replace all logo placeholders across every slide with the client logo image."""
    if logo_mime != 'image/svg+xml':
        logo_bytes = _to_png(logo_bytes, logo_mime)
        logo_mime  = 'image/png'

    ext = _MIME_TO_EXT.get(logo_mime, 'png')

    with zipfile.ZipFile(io.BytesIO(pptx_bytes)) as zin:
        files = {name: zin.read(name) for name in zin.namelist()}

    _sanitize_empty_runs(files)

    logo_name = f'logo_client.{ext}'
    logo_path = f'ppt/media/{logo_name}'
    c = 1
    while logo_path in files:
        logo_name = f'logo_client_{c}.{ext}'
        logo_path = f'ppt/media/{logo_name}'
        c += 1
    files[logo_path] = logo_bytes

    slide_re = re.compile(r'^ppt/slides/slide(\d+)\.xml$')
    slide_paths = sorted(
        (p for p in files if slide_re.match(p)),
        key=lambda p: int(slide_re.match(p).group(1)),
    )

    for slide_path in slide_paths:
        num      = int(slide_re.match(slide_path).group(1))
        rels_key = f'ppt/slides/_rels/slide{num}.xml.rels'
        root     = etree.fromstring(files[slide_path])
        raw_rels = files.get(rels_key, b'')
        rels_root = (
            etree.fromstring(raw_rels)
            if raw_rels
            else etree.Element(f'{{{_NS_RELS}}}Relationships')
        )

        rid            = _unique_rid(rels_root)
        slide_modified = False
        rels_modified  = False

        if num == 1:
            slide_modified, rels_modified = _process_slide1(
                root, rels_root, files, logo_bytes, logo_name, ext, rid
            )
        else:
            slide_modified = _process_slide(root, rid)
            rels_modified  = slide_modified

        if rels_modified:
            _add_rel(rels_root, rid, logo_name)
            files[rels_key] = _xml_bytes(rels_root)
        if slide_modified:
            files[slide_path] = _xml_bytes(root)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zout:
        for name, data in files.items():
            zout.writestr(name, data)
    return buf.getvalue()


def _process_slide1(root, rels_root, files, logo_bytes, logo_name, ext, rid):
    """Slide 1: swap image inside 'Rectángulo redondeado', or add blipFill fallback."""
    rels = {
        r.get('Id'): r.get('Target', '')
        for r in rels_root.findall(f'{{{_NS_RELS}}}Relationship')
    }

    rect_bounds = None
    for sp in root.iter(f'{{{_NS_P}}}sp'):
        cNvPr = sp.find(f'.//{{{_NS_P}}}cNvPr')
        if cNvPr is None or not (cNvPr.get('name') or '').startswith(_PORTADA_SP):
            continue
        b = _sp_bounds(sp)
        if b:
            x1, y1, cx, cy = b
            rect_bounds = (x1, y1, x1 + cx, y1 + cy)
            break

    if rect_bounds is None:
        return False, False

    rx1, ry1, rx2, ry2 = rect_bounds

    for pic in root.iter(f'{{{_NS_P}}}pic'):
        blip = pic.find(f'.//{{{_NS_A}}}blip')
        xfrm = pic.find(f'.//{{{_NS_A}}}xfrm')
        if blip is None or xfrm is None:
            continue
        off   = xfrm.find(f'{{{_NS_A}}}off')
        ext_e = xfrm.find(f'{{{_NS_A}}}ext')
        if off is None or ext_e is None:
            continue
        px = int(off.get('x', 0));  py = int(off.get('y', 0))
        pcx = int(ext_e.get('cx', 0)); pcy = int(ext_e.get('cy', 0))
        if px < 0 or py < 0:
            continue
        if rx1 <= px + pcx // 2 <= rx2 and ry1 <= py + pcy // 2 <= ry2:
            embed = blip.get(f'{{{_NS_R}}}embed')
            if embed:
                target = rels.get(embed, '')
                media  = posixpath.normpath('ppt/slides/' + target)
                if media in files:
                    files[media] = logo_bytes
                    return True, False

    for sp in root.iter(f'{{{_NS_P}}}sp'):
        cNvPr = sp.find(f'.//{{{_NS_P}}}cNvPr')
        if cNvPr is None or not (cNvPr.get('name') or '').startswith(_PORTADA_SP):
            continue
        spPr = sp.find(f'{{{_NS_P}}}spPr')
        if spPr is None:
            continue
        for tag in _FILL_TAGS:
            for el in spPr.findall(f'{{{_NS_A}}}{tag}'):
                spPr.remove(el)
        bf    = etree.SubElement(spPr, f'{{{_NS_A}}}blipFill')
        bl    = etree.SubElement(bf,   f'{{{_NS_A}}}blip')
        bl.set(f'{{{_NS_R}}}embed', rid)
        st    = etree.SubElement(bf,   f'{{{_NS_A}}}stretch')
        etree.SubElement(st, f'{{{_NS_A}}}fillRect')
        return True, True

    return False, False


def _process_slide(root, rid) -> bool:
    """Slides 2+: replace all logo placeholder shapes/runs."""
    spTree = root.find(f'{{{_NS_P}}}cSld/{{{_NS_P}}}spTree')
    if spTree is None:
        return False

    to_remove   = []
    pics_to_add = []
    modified    = False

    for sp in list(spTree):
        if sp.tag != f'{{{_NS_P}}}sp':
            continue

        t_all      = sp.findall(f'.//{{{_NS_A}}}t')
        shape_text = ''.join(t.text or '' for t in t_all).strip()
        bounds     = _sp_bounds(sp)
        if bounds is None:
            continue
        x, y, cx, cy = bounds

        # TYPE0: caja dedicada (<<Logo Cliente>> / <<Logo del Cliente>>)
        if shape_text in _DEDICATED:
            to_remove.append(sp)
            pics_to_add.append((x, y, cx, cy))
            modified = True
            continue

        paras = sp.findall(f'.//{{{_NS_A}}}p')
        for para_idx, para in enumerate(paras):
            runs     = para.findall(f'{{{_NS_A}}}r')
            combined = ''.join((r.findtext(f'{{{_NS_A}}}t') or '') for r in runs)
            if not combined.strip():
                continue
            # Omitir teléfonos y emails
            if '@' in combined or re.match(r'^\+\d+\s', combined.strip()):
                continue
            # Omitir párrafos con contenido no-X insuficiente (<3 chars):
            # evita bullets "* Xxxxxxx xxxxxxx..." donde solo queda "*"
            if len(re.sub(r'[Xx\s]', '', combined)) < 3:
                continue

            logo_y   = y + para_idx * _LINE_HEIGHT_EMU
            is_prop  = bool(_PROP_TEXT_RE.match(combined))

            # PROP directo: párrafo "La propuesta se presenta..." sin X's (ej. CBIT con texto real)
            run_handled = False
            if is_prop and not re.search(r'[Xx]{5,}', combined):
                if runs:
                    rt = runs[0].find(f'{{{_NS_A}}}t')
                    if rt is not None:
                        rt.text = _PROP_REPL
                    for r in runs[1:]:   # eliminar runs extra en vez de vaciarlos
                        para.remove(r)
                pics_to_add.append((x + cx - _INLINE_CX, logo_y, _INLINE_CX, _INLINE_CY))
                run_handled = True
                modified    = True

            # TYPE2: run aislado de X puras (ej. run = "XXXXXXXXXX")
            if not run_handled:
                for run_idx, run in enumerate(runs):
                    t_el = run.find(f'{{{_NS_A}}}t')
                    if t_el is None:
                        continue
                    t = (t_el.text or '').strip()
                    if not _X_RUN_RE.match(t):
                        continue

                    if is_prop:
                        # Párrafo "La propuesta se presenta...": primer run → PROP_REPL, eliminar los demás
                        if runs:
                            rt = runs[0].find(f'{{{_NS_A}}}t')
                            if rt is not None:
                                rt.text = _PROP_REPL
                            for r in runs[1:]:
                                para.remove(r)
                        logo_x = x + cx - _INLINE_CX
                    else:
                        # OVERLAY: no borrar el texto, superponer logo encima
                        preceding = sum(len(r.findtext(f'{{{_NS_A}}}t') or '') for r in runs[:run_idx])
                        frac      = preceding / max(len(combined), 1)
                        logo_x    = x + int(frac * cx)

                    pics_to_add.append((logo_x, logo_y, _INLINE_CX, _INLINE_CY))
                    run_handled = True
                    modified    = True
                    break  # un logo por párrafo

            if run_handled:
                continue

            # TYPE3: X embebida en texto mixto (ej. "...de acuerdo con xxxxx")
            for run_idx, run in enumerate(runs):
                t_el = run.find(f'{{{_NS_A}}}t')
                if t_el is None:
                    continue
                t = t_el.text or ''
                m = _X_EMBED_RE.search(t)
                if not m:
                    continue

                if is_prop:
                    # Actualizar texto al reemplazo correcto y eliminar runs siguientes
                    t_el.text = _PROP_REPL
                    for r in runs[run_idx + 1:]:
                        para.remove(r)
                    logo_x = x + cx - _INLINE_CX
                else:
                    # OVERLAY: no borrar el texto, superponer logo encima
                    preceding = sum(len(r.findtext(f'{{{_NS_A}}}t') or '') for r in runs[:run_idx]) + m.start()
                    frac      = preceding / max(len(combined), 1)
                    logo_x    = x + int(frac * cx)

                pics_to_add.append((logo_x, logo_y, _INLINE_CX, _INLINE_CY))
                modified = True
                break

    for sp in to_remove:
        spTree.remove(sp)

    max_id = _max_id(root)
    for px, py, pcx, pcy in pics_to_add:
        max_id += 1
        spTree.append(_build_pic(rid, px, py, pcx, pcy, max_id))

    return modified


def _sp_bounds(sp):
    spPr = sp.find(f'{{{_NS_P}}}spPr')
    if spPr is None:
        return None
    xfrm = spPr.find(f'{{{_NS_A}}}xfrm')
    if xfrm is None:
        return None
    off = xfrm.find(f'{{{_NS_A}}}off')
    ext = xfrm.find(f'{{{_NS_A}}}ext')
    if off is None or ext is None:
        return None
    try:
        return (
            int(off.get('x', 0)), int(off.get('y', 0)),
            int(ext.get('cx', 0)), int(ext.get('cy', 0)),
        )
    except (ValueError, TypeError):
        return None


def _max_id(root) -> int:
    ids = [int(el.get('id', 0)) for el in root.iter() if el.get('id', '').isdigit()]
    return max(ids, default=0)


def _build_pic(rid, x, y, cx, cy, shape_id):
    pic = etree.Element(f'{{{_NS_P}}}pic')

    nvPicPr = etree.SubElement(pic, f'{{{_NS_P}}}nvPicPr')
    cNvPr   = etree.SubElement(nvPicPr, f'{{{_NS_P}}}cNvPr')
    cNvPr.set('id', str(shape_id))
    cNvPr.set('name', f'Logo {shape_id}')
    cNvPicPr = etree.SubElement(nvPicPr, f'{{{_NS_P}}}cNvPicPr')
    locks    = etree.SubElement(cNvPicPr, f'{{{_NS_A}}}picLocks')
    locks.set('noChangeAspect', '1')
    etree.SubElement(nvPicPr, f'{{{_NS_P}}}nvPr')

    blipFill = etree.SubElement(pic, f'{{{_NS_P}}}blipFill')
    blip     = etree.SubElement(blipFill, f'{{{_NS_A}}}blip')
    blip.set(f'{{{_NS_R}}}embed', rid)
    stretch  = etree.SubElement(blipFill, f'{{{_NS_A}}}stretch')
    etree.SubElement(stretch, f'{{{_NS_A}}}fillRect')

    spPr    = etree.SubElement(pic, f'{{{_NS_P}}}spPr')
    xfrm    = etree.SubElement(spPr, f'{{{_NS_A}}}xfrm')
    off     = etree.SubElement(xfrm, f'{{{_NS_A}}}off')
    off.set('x', str(x));  off.set('y', str(y))
    ext     = etree.SubElement(xfrm, f'{{{_NS_A}}}ext')
    ext.set('cx', str(cx)); ext.set('cy', str(cy))
    geom    = etree.SubElement(spPr, f'{{{_NS_A}}}prstGeom')
    geom.set('prst', 'rect')
    etree.SubElement(geom, f'{{{_NS_A}}}avLst')

    return pic


def _unique_rid(rels_root) -> str:
    existing = {r.get('Id') for r in rels_root.findall(f'{{{_NS_RELS}}}Relationship')}
    rid = 'rIdClientLogo'
    c = 1
    while rid in existing:
        rid = f'rIdClientLogo{c}'
        c += 1
    return rid


def _add_rel(rels_root, rid, logo_name) -> None:
    rel = etree.SubElement(rels_root, f'{{{_NS_RELS}}}Relationship')
    rel.set('Id', rid)
    rel.set('Type', _REL_IMG)
    rel.set('Target', f'../media/{logo_name}')


def _xml_bytes(root) -> bytes:
    return etree.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True)


def sanitize_pptx(pptx_bytes: bytes) -> bytes:
    """Elimina <a:r> con <a:t/> vacío de todos los slides — PowerPoint los rechaza."""
    with zipfile.ZipFile(io.BytesIO(pptx_bytes)) as zin:
        files = {name: zin.read(name) for name in zin.namelist()}
    _sanitize_empty_runs(files)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zout:
        for name, data in files.items():
            zout.writestr(name, data)
    return buf.getvalue()
