"""
infrastructure/generators/alcances.py

Genera slides de Alcance Técnico del Servicio, uno por torre.

Cada torre produce uno o más slides de lista de bullets (formato overflow):
  - ITEMS_PER_OVERFLOW items por slide.
  - Las shapes decorativas/fondo y el logo del template se conservan.
  - Se añaden: título verde, línea separadora, lista de bullets.

Slide objetivo: el primero cuyo título contenga la palabra "alcance".
"""

import copy
import io
import re
import zipfile

from lxml import etree

from core.groq_client import create_chat_completion
from infrastructure.generators.cronograma_entregables import (
    _duplicate_slide,
    _get_slide_order,
)

# ── Namespaces ────────────────────────────────────────────────────────────────
A = 'http://schemas.openxmlformats.org/drawingml/2006/main'
P = 'http://schemas.openxmlformats.org/presentationml/2006/main'
R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'

SLIDE_W            = 9_144_000
SLOTS_PER_SLIDE    = 2   # items del alcance por slide de template
ITEMS_PER_OVERFLOW = 6   # items por slide de overflow
MAX_CHARS_DESC     = 350

# ── Configuración de shapes ───────────────────────────────────────────────────
DEBUG_SHAPES    = True
_SLIDE_TITLE_KW = 'alcance'

# Dejar vacíos → detección automática por patrón XXX
_NOMBRE_SHAPES: set[str] = set()
_DESC_SHAPES:   set[str] = set()

_PH_RE = re.compile(r'X{3,}', re.IGNORECASE)

# ── Prompt IA ─────────────────────────────────────────────────────────────────
_IA_SYSTEM = (
    "Eres un redactor experto de propuestas comerciales de TI. "
    "Dado el título y descripción de un punto de alcance de un proyecto, "
    "genera exactamente UN párrafo de máximo 2 oraciones que lo describa "
    "profesionalmente. "
    "Responde SOLO con el párrafo, sin títulos, viñetas ni texto adicional."
)


# ── Generación de texto ───────────────────────────────────────────────────────

def _primera_oracion(texto: str, max_len: int = 120) -> str:
    partes = re.split(r'(?<=[.!?])\s', texto.strip())
    primera = partes[0].strip()
    if len(primera) > max_len:
        primera = primera[:max_len - 1].rstrip() + '…'
    return primera


def _texto_con_ia(titulo: str, descripcion: str) -> str:
    mensajes = [
        {'role': 'system', 'content': _IA_SYSTEM},
        {'role': 'user',   'content': f'Título: {titulo}\n\nDescripción: {descripcion}'},
    ]
    try:
        return create_chat_completion(mensajes, max_tokens=150)
    except Exception as exc:
        print(f'[ALCANCES] IA falló para "{titulo}": {exc}. Usando texto original.')
        return descripcion


# ── Utilidades PPTX ───────────────────────────────────────────────────────────

def _sp_off_x(sp) -> int:
    spPr = sp.find(f'{{{P}}}spPr')
    if spPr is None:
        return 0
    xfrm = spPr.find(f'{{{A}}}xfrm')
    if xfrm is None:
        return 0
    off = xfrm.find(f'{{{A}}}off')
    return int(off.attrib.get('x', 0)) if off is not None else 0


def _sp_off_y(sp) -> int:
    spPr = sp.find(f'{{{P}}}spPr')
    if spPr is None:
        return 0
    xfrm = spPr.find(f'{{{A}}}xfrm')
    if xfrm is None:
        return 0
    off = xfrm.find(f'{{{A}}}off')
    return int(off.attrib.get('y', 0)) if off is not None else 0


def _sp_ext_cy(sp) -> int:
    spPr = sp.find(f'{{{P}}}spPr')
    if spPr is None:
        return 0
    xfrm = spPr.find(f'{{{A}}}xfrm')
    if xfrm is None:
        return 0
    ext = xfrm.find(f'{{{A}}}ext')
    return int(ext.attrib.get('cy', 0)) if ext is not None else 0


def _sp_text(sp) -> str:
    txb = sp.find(f'{{{P}}}txBody')
    if txb is None:
        return ''
    return ''.join(t.text or '' for t in txb.findall(f'.//{{{A}}}t')).strip()


def _set_nombre_text(sp, texto: str):
    """Reemplaza el run XXX del párrafo que lo contiene, preservando otros runs (iconos)."""
    txb = sp.find(f'{{{P}}}txBody')
    if txb is None:
        return
    for p_el in txb.findall(f'{{{A}}}p'):
        p_txt = ''.join(t.text or '' for t in p_el.findall(f'.//{{{A}}}t'))
        if _PH_RE.search(p_txt):
            for r_el in p_el.findall(f'{{{A}}}r'):
                t_el = r_el.find(f'{{{A}}}t')
                if t_el is not None and _PH_RE.search(t_el.text or ''):
                    t_el.text = texto
                    return  # solo reemplaza el primer run XXX, deja el resto intacto
    _set_desc_text(sp, texto)


def _set_desc_text(sp, texto: str, strip_bullets: bool = False):
    """Reemplaza todo el contenido textual del shape (una línea por \\n)."""
    txb = sp.find(f'{{{P}}}txBody')
    if txb is None:
        return

    first_p = txb.find(f'{{{A}}}p')
    template_rPr = None
    if first_p is not None:
        first_r = first_p.find(f'{{{A}}}r')
        if first_r is not None:
            rPr_el = first_r.find(f'{{{A}}}rPr')
            if rPr_el is not None:
                template_rPr = copy.deepcopy(rPr_el)
                template_rPr.attrib.pop('err', None)

    # Quitar lstStyle de bullets heredados si se pide
    if strip_bullets:
        lst = txb.find(f'{{{A}}}lstStyle')
        if lst is not None:
            lst.clear()

    for p_el in txb.findall(f'{{{A}}}p'):
        txb.remove(p_el)

    for linea in (texto.split('\n') if texto else ['']):
        if template_rPr is not None:
            p_el = etree.SubElement(txb, f'{{{A}}}p')
            # pPr sin bullet
            if strip_bullets:
                pPr = etree.SubElement(p_el, f'{{{A}}}pPr')
                etree.SubElement(pPr, f'{{{A}}}buNone')
            r_el = etree.SubElement(p_el, f'{{{A}}}r')
            r_el.append(copy.deepcopy(template_rPr))
            t_el = etree.SubElement(r_el, f'{{{A}}}t')
            t_el.text = linea
        else:
            safe = linea.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            p_xml = (f'<a:p xmlns:a="{A}"><a:r>'
                     f'<a:rPr dirty="0"/>'
                     f'<a:t>{safe}</a:t>'
                     f'</a:r></a:p>')
            txb.append(etree.fromstring(p_xml))


def _hide_sp(sp):
    spPr = sp.find(f'{{{P}}}spPr')
    if spPr is not None:
        spPr.attrib['hidden'] = '1'


# ── Búsqueda de shapes ────────────────────────────────────────────────────────

def _find_title_shape(root):
    """Retorna el shape del título (placeholder primero, luego fallback restringido a zona de título)."""
    _TITLE_TYPES = {'title', 'ctrtitle', 'centeredtitle'}
    _Y_TITLE_MAX = 1_400_000
    for sp in root.iter(f'{{{P}}}sp'):
        ph = sp.find(f'.//{{{P}}}ph')
        if ph is None:
            continue
        ph_type = ph.attrib.get('type', '').lower()
        ph_idx  = ph.attrib.get('idx', '-1')
        if ph_type in _TITLE_TYPES or ph_idx in ('0', ''):
            return sp
    best, best_y = None, float('inf')
    for sp in root.iter(f'{{{P}}}sp'):
        if _sp_off_y(sp) > _Y_TITLE_MAX:
            continue
        txb = sp.find(f'{{{P}}}txBody')
        if txb is None:
            continue
        txt = ''.join(t.text or '' for t in txb.findall(f'.//{{{A}}}t')).lower()
        if _SLIDE_TITLE_KW.lower() in txt:
            y = _sp_off_y(sp)
            if y < best_y:
                best_y = y
                best = sp
    return best


def _collect_shapes(root):
    """
    Retorna (nombres[SLOTS_PER_SLIDE], descs[SLOTS_PER_SLIDE]).

    Automático: detecta orientación por dispersión X vs Y, divide en grupos,
    dentro de cada grupo el más corto (cy) = nombre, el más alto = descripción.
    """
    nombres_raw, descs_raw, unknown_raw = [], [], []

    for sp in root.iter(f'{{{P}}}sp'):
        nvpr = sp.find(f'.//{{{P}}}cNvPr')
        if nvpr is None:
            continue
        name = nvpr.attrib.get('name', '')

        if DEBUG_SHAPES:
            txt = _sp_text(sp)
            x, y, cy = _sp_off_x(sp), _sp_off_y(sp), _sp_ext_cy(sp)
            print(f'[ALCANCES DEBUG] shape="{name}" x={x} y={y} cy={cy} txt={repr(txt[:60])}')

        if _NOMBRE_SHAPES and name in _NOMBRE_SHAPES:
            nombres_raw.append(sp)
            continue
        if _DESC_SHAPES and name in _DESC_SHAPES:
            descs_raw.append(sp)
            continue
        if not _NOMBRE_SHAPES and not _DESC_SHAPES:
            if _PH_RE.search(_sp_text(sp)):
                unknown_raw.append(sp)

    if nombres_raw or descs_raw:
        nombres_raw.sort(key=_sp_off_x)
        descs_raw.sort(key=_sp_off_x)
        while len(nombres_raw) < SLOTS_PER_SLIDE:
            nombres_raw.append(None)
        while len(descs_raw) < SLOTS_PER_SLIDE:
            descs_raw.append(None)
        return nombres_raw[:SLOTS_PER_SLIDE], descs_raw[:SLOTS_PER_SLIDE]

    if not unknown_raw:
        return [None] * SLOTS_PER_SLIDE, [None] * SLOTS_PER_SLIDE

    xs = [_sp_off_x(sp) for sp in unknown_raw]
    ys = [_sp_off_y(sp) for sp in unknown_raw]
    x_spread = max(xs) - min(xs)
    y_spread = max(ys) - min(ys)

    if x_spread >= y_spread:
        unknown_raw.sort(key=_sp_off_x)
        layout = 'horizontal'
    else:
        unknown_raw.sort(key=_sp_off_y)
        layout = 'vertical'

    print(f'[ALCANCES] Layout: {layout}, {len(unknown_raw)} shapes con XXX')

    n = len(unknown_raw)
    group_size = max(1, (n + SLOTS_PER_SLIDE - 1) // SLOTS_PER_SLIDE)

    nombres_out, descs_out = [], []
    for i in range(SLOTS_PER_SLIDE):
        group = unknown_raw[i * group_size: (i + 1) * group_size]
        if not group:
            nombres_out.append(None)
            descs_out.append(None)
        elif len(group) == 1:
            nombres_out.append(group[0])
            descs_out.append(None)
        else:
            by_h = sorted(group, key=_sp_ext_cy)
            nombres_out.append(by_h[0])   # más corto → barra del nombre
            descs_out.append(by_h[-1])    # más alto  → caja de descripción

    return nombres_out, descs_out


# ── Búsqueda del slide objetivo ───────────────────────────────────────────────

def _find_alcances_slide(files_dict: dict, slides_order: list) -> str | None:
    kw = _SLIDE_TITLE_KW.lower()
    _TITLE_TYPES = {'title', 'ctrtitle', 'centeredtitle'}
    # Shapes above this Y threshold are considered title-area (top ~25% of a 16:9 slide)
    _Y_TITLE_MAX = 1_400_000

    # Pass 1: official title/centeredTitle placeholders only
    for path in slides_order:
        root = etree.fromstring(files_dict[path])
        for sp in root.iter(f'{{{P}}}sp'):
            ph = sp.find(f'.//{{{P}}}ph')
            if ph is None:
                continue
            if ph.attrib.get('type', '').lower() not in _TITLE_TYPES:
                idx = ph.attrib.get('idx', '-1')
                if idx not in ('0', ''):
                    continue
            txb = sp.find(f'{{{P}}}txBody')
            if txb is None:
                continue
            txt = ''.join(t.text or '' for t in txb.findall(f'.//{{{A}}}t')).lower()
            if kw in txt:
                print(f'[ALCANCES] Slide encontrado (placeholder): {path}')
                return path

    # Pass 2: plain text boxes — ONLY shapes in the title area (top of slide)
    # to avoid matching "alcance" inside roadmap/content bullet points
    for path in slides_order:
        root = etree.fromstring(files_dict[path])
        for sp in root.iter(f'{{{P}}}sp'):
            if _sp_off_y(sp) > _Y_TITLE_MAX:
                continue
            txb = sp.find(f'{{{P}}}txBody')
            if txb is None:
                continue
            txt = ''.join(t.text or '' for t in txb.findall(f'.//{{{A}}}t')).lower()
            if kw in txt:
                print(f'[ALCANCES] Slide encontrado (fallback título): {path}')
                return path

    print(f'[ALCANCES] No se encontró slide con título "{_SLIDE_TITLE_KW}".')
    return None


# ── Relleno del slide template ────────────────────────────────────────────────

def _fill_slide_items(xml_bytes: bytes, torre: str, items: list[dict]) -> bytes:
    """
    items = [{'titulo': str, 'texto': str}, ...] (máx SLOTS_PER_SLIDE)
    Modifica el título del slide e inserta cada item en su slot.
    """
    root = etree.fromstring(xml_bytes)

    title_sp = _find_title_shape(root)
    if title_sp is not None:
        _set_desc_text(title_sp, f'Alcance Técnico del Servicio — {torre}',
                       strip_bullets=True)

    nombres, descs = _collect_shapes(root)

    for i in range(SLOTS_PER_SLIDE):
        sp_n = nombres[i] if i < len(nombres) else None
        sp_d = descs[i]   if i < len(descs)   else None

        if i < len(items):
            item = items[i]
            if sp_n:
                _set_nombre_text(sp_n, item['titulo'])
            if sp_d:
                _set_desc_text(sp_d, item['texto'])
        else:
            if sp_n:
                _hide_sp(sp_n)
            if sp_d:
                _hide_sp(sp_d)

    return etree.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True)


# ── Slides de overflow (formato simple) ───────────────────────────────────────

def _add_sp(sp_tree, shape_id: int, name: str,
            x: int, y: int, cx: int, cy: int) -> tuple:
    """Adds a blank p:sp to sp_tree and returns (sp, txBody)."""
    sp = etree.SubElement(sp_tree, f'{{{P}}}sp')

    nvSpPr  = etree.SubElement(sp, f'{{{P}}}nvSpPr')
    cNvPr   = etree.SubElement(nvSpPr, f'{{{P}}}cNvPr')
    cNvPr.attrib['id']   = str(shape_id)
    cNvPr.attrib['name'] = name
    cNvSpPr = etree.SubElement(nvSpPr, f'{{{P}}}cNvSpPr')
    cNvSpPr.attrib['txBox'] = '1'
    spLocks = etree.SubElement(cNvSpPr, f'{{{A}}}spLocks')
    spLocks.attrib['noGrp'] = '1'
    etree.SubElement(nvSpPr, f'{{{P}}}nvPr')

    spPr  = etree.SubElement(sp, f'{{{P}}}spPr')
    xfrm  = etree.SubElement(spPr, f'{{{A}}}xfrm')
    off   = etree.SubElement(xfrm, f'{{{A}}}off')
    off.attrib['x'] = str(x)
    off.attrib['y'] = str(y)
    ext   = etree.SubElement(xfrm, f'{{{A}}}ext')
    ext.attrib['cx'] = str(cx)
    ext.attrib['cy'] = str(cy)
    prstG = etree.SubElement(spPr, f'{{{A}}}prstGeom')
    prstG.attrib['prst'] = 'rect'
    etree.SubElement(prstG, f'{{{A}}}avLst')
    etree.SubElement(spPr, f'{{{A}}}noFill')

    txBody = etree.SubElement(sp, f'{{{P}}}txBody')
    bodyPr = etree.SubElement(txBody, f'{{{A}}}bodyPr')
    bodyPr.attrib['wrap']   = 'square'
    bodyPr.attrib['rtlCol'] = '0'
    etree.SubElement(bodyPr, f'{{{A}}}normAutofit')
    etree.SubElement(txBody, f'{{{A}}}lstStyle')

    return sp, txBody


def _add_para(txBody, text: str, sz: int, bold: bool,
              color_hex: str | None = None, indent: int = 0):
    """Appends a paragraph to txBody with the given styling."""
    p   = etree.SubElement(txBody, f'{{{A}}}p')
    pPr = etree.SubElement(p, f'{{{A}}}pPr')
    pPr.attrib['indent'] = str(indent)
    r   = etree.SubElement(p, f'{{{A}}}r')
    rPr = etree.SubElement(r, f'{{{A}}}rPr')
    rPr.attrib['lang']  = 'es-CO'
    rPr.attrib['sz']    = str(sz)
    rPr.attrib['b']     = '1' if bold else '0'
    rPr.attrib['dirty'] = '0'
    if color_hex:
        sf  = etree.SubElement(rPr, f'{{{A}}}solidFill')
        clr = etree.SubElement(sf,  f'{{{A}}}srgbClr')
        clr.attrib['val'] = color_hex
    t       = etree.SubElement(r, f'{{{A}}}t')
    t.text  = text


def _make_overflow_xml(template_xml: bytes, torre: str, items: list[dict]) -> bytes:
    """
    Slide de overflow completamente limpio: elimina TODAS las shapes del template
    (fondo/logo vienen del slide master) y añade título + lista de bullets con
    etree para evitar problemas de namespaces.
    """
    root    = etree.fromstring(template_xml)
    sp_tree = root.find(f'.//{{{P}}}spTree')
    if sp_tree is None:
        return template_xml

    # ── Limpiar spTree: eliminar solo shapes con texto (placeholders de contenido) ─
    # Se conservan:
    #   - nvGrpSpPr / grpSpPr  → metadatos estructurales obligatorios
    #   - p:sp sin texto        → rectángulos de fondo, líneas decorativas
    #   - p:pic                 → imágenes embebidas (logo)
    # Se eliminan:
    #   - p:sp con texto        → placeholders de título / contenido del template
    #   - p:grpSp con texto     → grupos que contengan texto
    _STRUCTURAL = {f'{{{P}}}nvGrpSpPr', f'{{{P}}}grpSpPr'}
    for child in list(sp_tree):
        tag = child.tag
        if tag in _STRUCTURAL:
            continue
        if tag == f'{{{P}}}sp':
            if _sp_text(child):
                sp_tree.remove(child)
            # sin texto → conservar (fondo, decorativo)
        elif tag == f'{{{P}}}grpSp':
            if any(_sp_text(s) for s in child.iter(f'{{{P}}}sp')):
                sp_tree.remove(child)
            # sin texto → conservar
        # p:pic y otros → conservar (logo)

    # ── Título ────────────────────────────────────────────────────────────────────
    _, title_body = _add_sp(sp_tree, 200, 'ov_title',
                            x=457_200, y=200_000,
                            cx=8_229_600, cy=750_000)
    _add_para(title_body,
              f'Alcance Técnico del Servicio — {torre}',
              sz=2400, bold=True, color_hex='1A5C38')

    # ── Separador visual (rectángulo verde delgado) ───────────────────────────────
    sep = etree.SubElement(sp_tree, f'{{{P}}}sp')
    sep_nvSpPr = etree.SubElement(sep, f'{{{P}}}nvSpPr')
    sep_cNvPr  = etree.SubElement(sep_nvSpPr, f'{{{P}}}cNvPr')
    sep_cNvPr.attrib['id']   = '201'
    sep_cNvPr.attrib['name'] = 'ov_sep'
    etree.SubElement(sep_nvSpPr, f'{{{P}}}cNvSpPr')
    etree.SubElement(sep_nvSpPr, f'{{{P}}}nvPr')
    sep_spPr   = etree.SubElement(sep, f'{{{P}}}spPr')
    sep_xfrm   = etree.SubElement(sep_spPr, f'{{{A}}}xfrm')
    sep_off    = etree.SubElement(sep_xfrm, f'{{{A}}}off')
    sep_off.attrib['x'] = '457200'
    sep_off.attrib['y'] = '950000'
    sep_ext    = etree.SubElement(sep_xfrm, f'{{{A}}}ext')
    sep_ext.attrib['cx'] = '8229600'
    sep_ext.attrib['cy'] = '50000'
    sep_prstG  = etree.SubElement(sep_spPr, f'{{{A}}}prstGeom')
    sep_prstG.attrib['prst'] = 'rect'
    etree.SubElement(sep_prstG, f'{{{A}}}avLst')
    sep_sf  = etree.SubElement(sep_spPr, f'{{{A}}}solidFill')
    sep_clr = etree.SubElement(sep_sf,  f'{{{A}}}srgbClr')
    sep_clr.attrib['val'] = '1A5C38'

    # ── Contenido: lista de bullets ───────────────────────────────────────────────
    _, content_body = _add_sp(sp_tree, 202, 'ov_content',
                              x=457_200, y=1_050_000,
                              cx=8_229_600, cy=4_050_000)
    for item in items:
        titulo = (item.get('titulo') or '').strip()
        texto  = (item.get('texto')  or '').strip()
        if not titulo:
            continue
        _add_para(content_body, f'• {titulo}',
                  sz=1700, bold=True, color_hex='1A5C38')
        if texto:
            _add_para(content_body, f'   {_primera_oracion(texto, max_len=240)}',
                      sz=1300, bold=False, color_hex='333333', indent=457200)
        # blank spacer
        etree.SubElement(etree.SubElement(content_body, f'{{{A}}}p'), f'{{{A}}}endParaRPr')

    return etree.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True)


# ── Entry point ───────────────────────────────────────────────────────────────

def edit(pptx_bytes: bytes, config: dict, catalog_data=None) -> bytes:
    excel_data = config.get('excel_data') or {}
    alcances   = excel_data.get('alcances', [])
    usar_ia    = bool((config.get('opciones') or {}).get('usar_ia_alcances', False))

    if not alcances:
        print('[ALCANCES] Sin datos de alcances, se omite.')
        return pptx_bytes

    files_dict = {}
    with zipfile.ZipFile(io.BytesIO(pptx_bytes)) as zin:
        files_dict = {n: zin.read(n) for n in zin.namelist()}

    slides_order = _get_slide_order(pptx_bytes)
    target_path  = _find_alcances_slide(files_dict, slides_order)

    if not target_path:
        return pptx_bytes

    template_xml = files_dict[target_path]
    prev_path    = target_path
    first_slide  = True

    for alc in alcances:
        torre     = (alc.get('torre') or '').strip()
        raw_items = alc.get('items', [])
        if not torre:
            continue

        items = []
        for it in raw_items:
            titulo = (it.get('titulo') or '').strip()
            desc   = (it.get('descripcion') or '').strip()
            if not titulo:
                continue
            texto = (_texto_con_ia(titulo, desc) if usar_ia and desc
                     else desc[:MAX_CHARS_DESC] if desc
                     else titulo)
            items.append({'titulo': titulo, 'texto': texto})

        if not items:
            continue

        print(f'[ALCANCES] Torre "{torre}" — {len(items)} items, IA={usar_ia}')

        # Un slide por cada chunk de ITEMS_PER_OVERFLOW items (mismo formato para todos)
        for i in range(0, len(items), ITEMS_PER_OVERFLOW):
            chunk   = items[i: i + ITEMS_PER_OVERFLOW]
            ov_xml  = _make_overflow_xml(template_xml, torre, chunk)
            if first_slide:
                files_dict[target_path] = ov_xml
                prev_path   = target_path
                first_slide = False
            else:
                new_path = _duplicate_slide(files_dict, target_path, prev_path)
                files_dict[new_path] = ov_xml
                prev_path = new_path

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zout:
        for n, d in files_dict.items():
            zout.writestr(n, d)
    return buf.getvalue()
