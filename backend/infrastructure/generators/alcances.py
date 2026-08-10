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
_ROADMAP_MARKERS = {'start', 'finish', 'xxxxxxx'}
_ROADMAP_KEYWORDS = {'roadmap'}

# ── Configuración de tarjetas visuales (marca Periferia) ──────────────────────
# Paleta corporativa:
#   Verde principal  #1E7A3D   |   Verde oscuro  #0F5C2A   |   Gris texto  #595959
_BRAND_GREEN        = '1E7A3D'
_BRAND_GREEN_DARK   = '0F5C2A'
_BRAND_TEXT_GRAY    = '595959'
_BRAND_CARD_BG      = 'FFFFFF'
_BRAND_CARD_BG_SOFT = 'F4F9F5'

_VISUAL_CARD_BG        = _BRAND_CARD_BG        # blanco limpio corporativo
_VISUAL_TITLE_COLOR    = _BRAND_GREEN_DARK     # título en verde oscuro de marca
_VISUAL_DESC_COLOR     = _BRAND_TEXT_GRAY      # descripción en gris de marca
_VISUAL_CARD_RADIUS    = 55000                 # ~6px esquinas redondeadas
_VISUAL_CUT_TOP_R      = 12000                 # corte diagonal esquina sup. derecha (12%, más pequeño que antes para no robar tanto espacio)
_VISUAL_STRIPE_W       = 45000                 # ancho franja lateral de acento
_VISUAL_BADGE_SIZE     = 240000               # badge circular un poco más pequeño
_VISUAL_BADGE_GAP      = 140000               # separación badge → texto
_VISUAL_CARD_GAP       = 50000                 # espacio entre filas
_VISUAL_COLUMN_GAP     = 60000                 # espacio entre columnas
_VISUAL_LEFT_MARGIN    = 400000                # margen izquierdo
_VISUAL_CONTENT_WIDTH  = 8_344_000             # ancho total disponible
_VISUAL_GRID_COLS      = 2                     # número de columnas
_VISUAL_CARD_WIDTH     = 4_100_000             # ancho de cada tarjeta
_VISUAL_START_Y        = 1_100_000             # Y inicial después del título
_VISUAL_CONTENT_HEIGHT = 3_900_000             # altura disponible para contenido
_VISUAL_CARD_MIN_HEIGHT = 340_000              # altura mínima por tarjeta
_VISUAL_CARD_MAX_HEIGHT = 1_400_000            # altura máxima por tarjeta (permite textos largos)
_VISUAL_TITLE_FONT     = 1300                  # ~13pt título en negrita
_VISUAL_DESC_FONT      = 950                   # ~9.5pt descripción regular

# ── Tonos verdes corporativos (familia #1E7A3D – #0F5C2A) para categorías ─────
# Todas las categorías usan VARIACIONES de verde, simulando distinción por intensidad.
_BRAND_GREEN_LIGHT = 'A3D9A5'   # verde claro suave (franja)
_BRAND_GREEN_MID   = '5EAA68'   # verde medio
_BRAND_GREEN_DEEP  = '1A512E'   # verde profundo

# ── Diccionario de categorías de alcance → color de acento / icono SVG ────────
# Estructura simple para agregar categorías nuevas SIN tocar la lógica de tarjetas:
#   'nombre': {
#       'keywords':   (términos que activan la categoría automáticamente),
#       'color':      color de acento (franja lateral, etiqueta),
#       'color_dark': color oscuro (badge circular del ítem),
#       'badge_bg':   fondo suave para futuros usos,
#       'icono_svg':  RUTA DEL ARCHIVO SVG (lo defines al agregar la categoría),
#   }
_CATEGORIAS = {
    'desarrollo': {
        'keywords':   ('desarrollo', 'full stack', 'fullstack', 'software', 'codificación', 'codificacion',
                       'programación', 'programacion', 'aplicación', 'aplicacion', 'app', 'web', 'frontend',
                       'backend', 'api', 'módulo', 'modulo', 'integración', 'integracion', 'implementación', 'implementacion'),
        'color':      _BRAND_GREEN,          # #1E7A3D
        'color_dark': _BRAND_GREEN_DARK,     # #0F5C2A
        'badge_bg':   'E1F1E6',
        'icono_svg':  None,
    },
    'infraestructura': {
        'keywords':   ('infraestructura', 'servidor', 'servidores', 'nube', 'cloud', 'red', 'redes',
                       'almacenamiento', 'despliegue', 'devops', 'contenedor', 'contenedores', 'docker',
                       'kubernetes', 'virtualización', 'virtualizacion', 'ci/cd', 'infra'),
        'color':      _BRAND_GREEN_MID,      # #5EAA68
        'color_dark': _BRAND_GREEN_DEEP,     # #1A512E
        'badge_bg':   'E4F2E6',
        'icono_svg':  None,
    },
    'datos': {
        'keywords':   ('datos', 'data', 'base de datos', 'sql', 'analítica', 'analitica', 'reporte',
                       'reportes', 'dashboard', 'etl', 'modelo de datos', 'información', 'informacion',
                       'gestión de datos', 'gestion de datos', 'data warehouse'),
        'color':      _BRAND_GREEN_LIGHT,    # #A3D9A5
        'color_dark': _BRAND_GREEN_MID,      # #5EAA68
        'badge_bg':   'EAF6EB',
        'icono_svg':  None,
    },
    'seguridad': {
        'keywords':   ('seguridad', 'cyber', 'ciberseguridad', 'autenticación', 'autenticacion', 'acceso',
                       'permisos', 'encriptación', 'encriptacion', 'firewall', 'vulnerabilidad', 'auditoría', 'auditoria'),
        'color':      _BRAND_GREEN_DEEP,     # #1A512E
        'color_dark': _BRAND_GREEN_DARK,     # #0F5C2A
        'badge_bg':   'DCEFE0',
        'icono_svg':  None,
    },
    'calidad': {
        'keywords':   ('calidad', 'qa', 'testing', 'pruebas', 'test', 'garantía', 'garantia', 'validación',
                       'validacion', 'certificación', 'certificacion', 'aseguramiento', 'control de calidad'),
        'color':      _BRAND_GREEN_MID,      # #5EAA68
        'color_dark': _BRAND_GREEN_DEEP,     # #1A512E
        'badge_bg':   'E4F2E6',
        'icono_svg':  None,
    },
    'default': {
        'keywords':   (),
        'color':      _BRAND_GREEN,
        'color_dark': _BRAND_GREEN_DARK,
        'badge_bg':   _BRAND_CARD_BG_SOFT,
        'icono_svg':  None,
    },
}

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


def _is_roadmap_slide(root) -> bool:
    raw_text = []
    for sp in root.iter(f'{{{P}}}sp'):
        txb = sp.find(f'{{{P}}}txBody')
        if txb is None:
            continue
        raw = ''.join(t.text or '' for t in txb.findall(f'.//{{{A}}}t')).strip()
        if raw:
            raw_text.append(raw.lower())

    if not raw_text:
        return False

    raw = ' '.join(raw_text)
    if any(keyword in raw for keyword in _ROADMAP_KEYWORDS):
        return True

    for marker in _ROADMAP_MARKERS:
        if re.search(rf'\b{re.escape(marker)}\b', raw):
            return True

    return False


# ── Búsqueda del slide objetivo ───────────────────────────────────────────────

def _find_alcances_slide(files_dict: dict, slides_order: list) -> str | None:
    kw = _SLIDE_TITLE_KW.lower()
    _TITLE_TYPES = {'title', 'ctrtitle', 'centeredtitle'}
    # Shapes above this Y threshold are considered title-area (top ~25% of a 16:9 slide)
    _Y_TITLE_MAX = 1_400_000

    # Pass 1: official title/centeredTitle placeholders only
    for path in slides_order:
        root = etree.fromstring(files_dict[path])
        if _is_roadmap_slide(root):
            continue
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
        if _is_roadmap_slide(root):
            continue
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


# ── Slides de overflow (formato visual con tarjetas) ──────────────────────────

def _detectar_categoria(titulo: str, texto: str) -> dict:
    """
    Detecta la categoría de un alcance según sus keywords.

    Retorna la config completa de _CATEGORIAS (con 'default' como fallback).
    Es el punto único de mapeo categoría → color/icono: agrega categorías
    nuevas en _CATEGORIAS sin tocar la lógica de tarjetas.
    """
    titulo_n = (titulo or '').lower()
    texto_n  = (texto  or '').lower()
    for nombre, cfg in _CATEGORIAS.items():
        if nombre == 'default':
            continue
        for kw in cfg['keywords']:
            if kw in titulo_n or kw in texto_n:
                return cfg
    return _CATEGORIAS['default']


def _add_card_shape(sp_tree, shape_id: int, name: str,
                    x: int, y: int, cx: int, cy: int,
                    categoria_cfg: dict | None = None,
                    badge_text: str = '') -> etree._Element:
    """
    Crea una tarjeta corporativa de marca Periferia:
      - Fondo blanco con borde redondeado y sombra suave.
      - Franja lateral de acento (color de categoría).
      - Corte diagonal "tech frame" en la esquina superior derecha.
      - Badge circular con el color oscuro de la categoría y el número del ítem
        (soporte futuro: reemplazar el número por el icono SVG indicado en _CATEGORIAS).

    categoria_cfg: dict desde _CATEGORIAS; usa default si no se pasa.
    """
    from lxml import etree as _etree

    if categoria_cfg is None:
        categoria_cfg = _CATEGORIAS['default']

    accent    = categoria_cfg.get('color',      _BRAND_GREEN)
    accent_dk = categoria_cfg.get('color_dark', _BRAND_GREEN_DARK)

    # ── Tarjeta base (fondo blanco, esquinas redondeadas, sombra suave) ──
    sp = _etree.SubElement(sp_tree, f'{{{P}}}sp')
    nvSpPr  = _etree.SubElement(sp, f'{{{P}}}nvSpPr')
    cNvPr   = _etree.SubElement(nvSpPr, f'{{{P}}}cNvPr')
    cNvPr.attrib['id']   = str(shape_id)
    cNvPr.attrib['name'] = name
    cNvSpPr = _etree.SubElement(nvSpPr, f'{{{P}}}cNvSpPr')
    cNvSpPr.attrib['txBox'] = '1'
    _etree.SubElement(nvSpPr, f'{{{P}}}nvPr')

    spPr  = _etree.SubElement(sp, f'{{{P}}}spPr')
    xfrm  = _etree.SubElement(spPr, f'{{{A}}}xfrm')
    off   = _etree.SubElement(xfrm, f'{{{A}}}off')
    off.attrib['x'] = str(x)
    off.attrib['y'] = str(y)
    ext   = _etree.SubElement(xfrm, f'{{{A}}}ext')
    ext.attrib['cx'] = str(cx)
    ext.attrib['cy'] = str(cy)

    prstG = _etree.SubElement(spPr, f'{{{A}}}prstGeom')
    prstG.attrib['prst'] = 'roundRect'
    avLst = _etree.SubElement(prstG, f'{{{A}}}avLst')
    gd = _etree.SubElement(avLst, f'{{{A}}}gd')
    gd.attrib['name'] = 'adj'
    gd.attrib['fmla'] = f'val {_VISUAL_CARD_RADIUS}'

    # Fondo blanco corporativo
    _efill = _etree.SubElement(spPr, f'{{{A}}}solidFill')
    _eclr  = _etree.SubElement(_efill, f'{{{A}}}srgbClr')
    _eclr.attrib['val'] = _VISUAL_CARD_BG

    # Borde sutil gris-verde
    _eln = _etree.SubElement(spPr, f'{{{A}}}ln')
    _eln.attrib['w'] = '12700'  # 1pt
    _eln_sf = _etree.SubElement(_eln, f'{{{A}}}solidFill')
    _eln_cl = _etree.SubElement(_eln_sf, f'{{{A}}}srgbClr')
    _eln_cl.attrib['val'] = 'D9E4DC'

    # Sombra suave (estilo "tech frame")
    _eff = _etree.SubElement(spPr, f'{{{A}}}effectLst')
    _shd = _etree.SubElement(_eff, f'{{{A}}}outerShdw')
    _shd.attrib['blurRad'] = '90000'
    _shd.attrib['dist']    = '40000'
    _shd.attrib['dir']     = '5400000'
    _shd.attrib['rotWithShape'] = '0'
    _shd_sf = _etree.SubElement(_shd, f'{{{A}}}srgbClr')
    _shd_sf.attrib['val'] = '1E3A2A'
    _shd_a  = _etree.SubElement(_shd_sf, f'{{{A}}}alpha')
    _shd_a.attrib['val']  = '22000'

    # Área de texto: deja espacio para franja + badge a la izquierda,
    # y margen derecho amplio para que el triángulo diagonal NO se superponga.
    cut_w = int(cx * _VISUAL_CUT_TOP_R / 100000)
    txBody = _etree.SubElement(sp, f'{{{P}}}txBody')
    bodyPr = _etree.SubElement(txBody, f'{{{A}}}bodyPr')
    bodyPr.attrib['wrap']   = 'square'
    bodyPr.attrib['rtlCol'] = '0'
    bodyPr.attrib['lIns']   = str(_VISUAL_STRIPE_W + _VISUAL_BADGE_SIZE + _VISUAL_BADGE_GAP + 60000)
    bodyPr.attrib['rIns']   = str(cut_w + 120000)  # margen derecho = ancho del triángulo + holgura
    bodyPr.attrib['tIns']   = '140000'
    bodyPr.attrib['bIns']   = '120000'
    _etree.SubElement(bodyPr, f'{{{A}}}normAutofit')
    _etree.SubElement(txBody, f'{{{A}}}lstStyle')

    # ── Franja lateral de acento (color de categoría) ──
    stripe = _etree.SubElement(sp_tree, f'{{{P}}}sp')
    s_nv   = _etree.SubElement(stripe, f'{{{P}}}nvSpPr')
    s_cn   = _etree.SubElement(s_nv, f'{{{P}}}cNvPr')
    s_cn.attrib['id']   = str(shape_id) + '01'
    s_cn.attrib['name'] = name + '_stripe'
    _etree.SubElement(s_nv, f'{{{P}}}cNvSpPr')
    _etree.SubElement(s_nv, f'{{{P}}}nvPr')
    s_spPr = _etree.SubElement(stripe, f'{{{P}}}spPr')
    s_xfrm = _etree.SubElement(s_spPr, f'{{{A}}}xfrm')
    s_off  = _etree.SubElement(s_xfrm, f'{{{A}}}off')
    s_off.attrib['x'] = str(x)
    s_off.attrib['y'] = str(y + 60000)
    s_ext  = _etree.SubElement(s_xfrm, f'{{{A}}}ext')
    s_ext.attrib['cx'] = str(_VISUAL_STRIPE_W)
    s_ext.attrib['cy'] = str(cy - 120000)
    s_prst = _etree.SubElement(s_spPr, f'{{{A}}}prstGeom')
    s_prst.attrib['prst'] = 'roundRect'
    _etree.SubElement(s_prst, f'{{{A}}}avLst')
    s_fill = _etree.SubElement(s_spPr, f'{{{A}}}solidFill')
    s_clr  = _etree.SubElement(s_fill, f'{{{A}}}srgbClr')
    s_clr.attrib['val'] = accent

    # ── Corte diagonal "tech frame" (esquina superior derecha) ──
    cut_w = int(cx * _VISUAL_CUT_TOP_R / 100000)
    cut = _etree.SubElement(sp_tree, f'{{{P}}}sp')
    c_nv  = _etree.SubElement(cut, f'{{{P}}}nvSpPr')
    c_cn  = _etree.SubElement(c_nv, f'{{{P}}}cNvPr')
    c_cn.attrib['id']   = str(shape_id) + '02'
    c_cn.attrib['name'] = name + '_cut'
    _etree.SubElement(c_nv, f'{{{P}}}cNvSpPr')
    _etree.SubElement(c_nv, f'{{{P}}}nvPr')
    c_spPr = _etree.SubElement(cut, f'{{{P}}}spPr')
    c_xfrm = _etree.SubElement(c_spPr, f'{{{A}}}xfrm')
    c_off  = _etree.SubElement(c_xfrm, f'{{{A}}}off')
    c_off.attrib['x'] = str(x + cx - cut_w)
    c_off.attrib['y'] = str(y)
    c_ext  = _etree.SubElement(c_xfrm, f'{{{A}}}ext')
    c_ext.attrib['cx'] = str(cut_w)
    c_ext.attrib['cy'] = str(cut_w)
    c_prst = _etree.SubElement(c_spPr, f'{{{A}}}prstGeom')
    c_prst.attrib['prst'] = 'rtTriangle'
    _etree.SubElement(c_prst, f'{{{A}}}avLst')
    c_fill = _etree.SubElement(c_spPr, f'{{{A}}}solidFill')
    c_clr  = _etree.SubElement(c_fill, f'{{{A}}}srgbClr')
    c_clr.attrib['val'] = accent_dk

    # ── Badge circular con número del ítem (o icono SVG futuro) ──
    if badge_text:
        badge = _etree.SubElement(sp_tree, f'{{{P}}}sp')
        b_nv  = _etree.SubElement(badge, f'{{{P}}}nvSpPr')
        b_cn  = _etree.SubElement(b_nv, f'{{{P}}}cNvPr')
        b_cn.attrib['id']   = str(shape_id) + '03'
        b_cn.attrib['name'] = name + '_badge'
        _etree.SubElement(b_nv, f'{{{P}}}cNvSpPr')
        _etree.SubElement(b_nv, f'{{{P}}}nvPr')
        b_spPr = _etree.SubElement(badge, f'{{{P}}}spPr')
        b_xfrm = _etree.SubElement(b_spPr, f'{{{A}}}xfrm')
        b_off  = _etree.SubElement(b_xfrm, f'{{{A}}}off')
        b_off.attrib['x'] = str(x + _VISUAL_STRIPE_W + 100000)
        b_off.attrib['y'] = str(y + 140000)
        b_ext  = _etree.SubElement(b_xfrm, f'{{{A}}}ext')
        b_ext.attrib['cx'] = str(_VISUAL_BADGE_SIZE)
        b_ext.attrib['cy'] = str(_VISUAL_BADGE_SIZE)
        b_prst = _etree.SubElement(b_spPr, f'{{{A}}}prstGeom')
        b_prst.attrib['prst'] = 'ellipse'
        _etree.SubElement(b_prst, f'{{{A}}}avLst')
        b_fill = _etree.SubElement(b_spPr, f'{{{A}}}solidFill')
        b_clr  = _etree.SubElement(b_fill, f'{{{A}}}srgbClr')
        b_clr.attrib['val'] = accent_dk

        b_txb = _etree.SubElement(badge, f'{{{P}}}txBody')
        b_bp  = _etree.SubElement(b_txb, f'{{{A}}}bodyPr')
        b_bp.attrib['lIns'] = '0'
        b_bp.attrib['rIns'] = '0'
        b_bp.attrib['tIns'] = '0'
        b_bp.attrib['bIns'] = '0'
        b_bp.attrib['anchor'] = 'ctr'
        _etree.SubElement(b_txb, f'{{{A}}}lstStyle')
        b_p   = _etree.SubElement(b_txb, f'{{{A}}}p')
        b_pPr = _etree.SubElement(b_p, f'{{{A}}}pPr')
        _etree.SubElement(b_pPr, f'{{{A}}}buNone')
        b_r   = _etree.SubElement(b_p, f'{{{A}}}r')
        b_rPr = _etree.SubElement(b_r, f'{{{A}}}rPr')
        b_rPr.attrib['lang']  = 'es-CO'
        b_rPr.attrib['sz']    = '1200'
        b_rPr.attrib['b']     = '1'
        b_rPr.attrib['dirty'] = '0'
        b_rPr.attrib['align'] = 'ctr'
        b_rPr.attrib['baseline'] = '0'
        b_sf  = _etree.SubElement(b_rPr, f'{{{A}}}solidFill')
        b_scl = _etree.SubElement(b_sf, f'{{{A}}}srgbClr')
        b_scl.attrib['val'] = 'FFFFFF'
        b_t   = _etree.SubElement(b_r, f'{{{A}}}t')
        b_t.text = badge_text

    return sp


def _add_card_para(txBody, text: str, sz: int, bold: bool,
                   color_hex: str, is_title: bool = False):
    """Agrega un párrafo dentro de una tarjeta visual."""
    p   = etree.SubElement(txBody, f'{{{A}}}p')
    pPr = etree.SubElement(p, f'{{{A}}}pPr')
    etree.SubElement(pPr, f'{{{A}}}buNone')  # sin viñetas
    if is_title:
        spcA = etree.SubElement(pPr, f'{{{A}}}spcAft')
        spcA.attrib['spcPts'] = '80'  # ~8pt spacing after title
    r   = etree.SubElement(p, f'{{{A}}}r')
    rPr = etree.SubElement(r, f'{{{A}}}rPr')
    rPr.attrib['lang']  = 'es-CO'
    rPr.attrib['sz']    = str(sz)
    rPr.attrib['b']     = '1' if bold else '0'
    rPr.attrib['dirty'] = '0'
    rPr.attrib['kern']  = '1200'  # kerning para mejor legibilidad
    if color_hex:
        sf  = etree.SubElement(rPr, f'{{{A}}}solidFill')
        clr = etree.SubElement(sf,  f'{{{A}}}srgbClr')
        clr.attrib['val'] = color_hex
    t       = etree.SubElement(r, f'{{{A}}}t')
    t.text  = text


def _estimate_item_required_height(titulo: str, texto: str) -> int:
    """
    Estima la altura mínima en EMU que necesita una tarjeta para mostrar
    su título y descripción sin que el texto se desborde.
    
    Toma en cuenta: ancho disponible, tamaño de fuente, interlineado y márgenes.
    El normAutofit de PPTX se encargará de reducir la fuente si aún falta espacio.
    """
    # Ancho de texto disponible dentro de la tarjeta (card_width - márgenes internos)
    avail_width = _VISUAL_CARD_WIDTH - 360_000  # 180k left + 180k right
    # Caracteres aproximados por línea según el ancho y el tamaño de fuente
    # A 12pt (sz=1200), cada carácter ocupa ~76,000 EMU en promedio
    title_cpl = max(1, int(avail_width / 76_000))   # ~49 chars/line at 12pt
    desc_cpl  = max(1, int(avail_width / 58_000))   # ~65 chars/line at 9pt
    # Altura de línea con interlineado ~1.3x
    title_lh = 200_000  # ~12pt * 1.3 * 12700
    desc_lh  = 150_000  # ~9pt * 1.3 * 12700
    # Espaciado entre título y descripción
    title_desc_gap = 8_000  # 0.6pt
    # Márgenes internos (top + bottom)
    margins = 200_000

    titulo = (titulo or '').strip()
    texto  = (texto or '').strip()

    title_lines = max(1, (len(titulo) + title_cpl - 1) // title_cpl)
    desc_lines = 0
    if texto and texto != titulo:
        desc_lines = max(1, (len(texto) + desc_cpl - 1) // desc_cpl)

    required = (title_lines * title_lh +
                title_desc_gap +
                desc_lines * desc_lh +
                margins)
    # Acotar dentro de los límites
    return max(_VISUAL_CARD_MIN_HEIGHT, min(required, _VISUAL_CARD_MAX_HEIGHT))


def _calculate_row_heights(items: list[dict], cols: int = 2) -> list[int]:
    """
    Calcula alturas RESPONSIVE para cada FILA del grid de 2 columnas.
    
    Estrategia:
    1. Calcula la altura MÍNIMA REQUERIDA para que el texto de cada item
       quepa sin desbordarse (basado en longitud de texto, fuente y ancho).
    2. La altura de cada fila = el máximo entre la altura requerida y la
       altura proporcional (distribución justa del espacio sobrante).
    3. normAutofit se encarga de reducir la fuente si aún falta espacio.
    """
    n = len(items)
    if n == 0:
        return []

    num_rows = (n + cols - 1) // cols
    total_gaps = (num_rows - 1) * _VISUAL_CARD_GAP
    available = _VISUAL_CONTENT_HEIGHT - total_gaps

    row_required = []   # altura mínima que necesita cada fila para su contenido
    row_weights   = []  # peso proporcional para distribuir el sobrante

    for r in range(num_rows):
        start = r * cols
        end   = min(start + cols, n)
        max_req = _VISUAL_CARD_MIN_HEIGHT
        max_w   = 1
        for i in range(start, end):
            item = items[i]
            titulo = (item.get('titulo') or '').strip()
            texto  = (item.get('texto')  or '').strip()
            # Altura requerida para este item
            req = _estimate_item_required_height(titulo, texto)
            if req > max_req:
                max_req = req
            # Peso para distribución proporcional
            w = max(1, len(titulo) * 2 + len(texto) * 0.35)
            if w > max_w:
                max_w = w
        row_required.append(max_req)
        row_weights.append(max_w)

    total_weight = sum(row_weights)

    # Altura final = max(requerida, proporcional), acotada a max
    row_heights = []
    for i in range(num_rows):
        prop_h = int(available * (row_weights[i] / total_weight)) if total_weight else _VISUAL_CARD_MIN_HEIGHT
        prop_h = max(_VISUAL_CARD_MIN_HEIGHT, min(prop_h, _VISUAL_CARD_MAX_HEIGHT))
        h = max(row_required[i], prop_h)
        h = min(h, _VISUAL_CARD_MAX_HEIGHT)
        row_heights.append(h)

    # Redistribuir espacio sobrante entre filas que no alcanzaron el máximo
    total_used = sum(row_heights)
    if total_used < available:
        surplus = available - total_used
        non_max = [i for i, h in enumerate(row_heights) if h < _VISUAL_CARD_MAX_HEIGHT]
        if non_max:
            nm_weight = sum(row_weights[i] for i in non_max)
            if nm_weight > 0:
                for i in non_max:
                    extra = int(surplus * (row_weights[i] / nm_weight))
                    row_heights[i] = min(row_heights[i] + extra, _VISUAL_CARD_MAX_HEIGHT)

    return row_heights


def _make_overflow_xml_visual(template_xml: bytes, torre: str, items: list[dict]) -> bytes:
    """
    Slide de overflow con TARJETAS VISUALES de marca en GRID DE 2 COLUMNAS.
    Cada ítem se muestra en una tarjeta blanca corporativa con:
      - Franja lateral de acento según categoría detectada (diccionario _CATEGORIAS).
      - Corte diagonal "tech frame" en la esquina superior derecha.
      - Badge circular numerado por categoría.
      - Título en verde oscuro #0F5C2A, descripción en gris #595959.
    - Las tarjetas se organizan en 2 columnas × N filas.
    - La altura de cada fila es proporcional al contenido más largo de esa fila.
    - normAutofit evita que el texto se desborde.
    """
    root    = etree.fromstring(template_xml)
    sp_tree = root.find(f'.//{{{P}}}spTree')
    if sp_tree is None:
        return template_xml

    # ── Limpiar spTree ────────────────────────────────────────────────────────
    _STRUCTURAL = {f'{{{P}}}nvGrpSpPr', f'{{{P}}}grpSpPr'}
    for child in list(sp_tree):
        tag = child.tag
        if tag in _STRUCTURAL:
            continue
        if tag == f'{{{P}}}sp':
            if _sp_text(child):
                sp_tree.remove(child)
        elif tag == f'{{{P}}}grpSp':
            if any(_sp_text(s) for s in child.iter(f'{{{P}}}sp')):
                sp_tree.remove(child)

    # ── Título ────────────────────────────────────────────────────────────────
    _, title_body = _add_sp(sp_tree, 200, 'ov_title',
                            x=457_200, y=200_000,
                            cx=8_229_600, cy=750_000)
    _add_para(title_body,
              f'Alcance Técnico del Servicio — {torre}',
              sz=2400, bold=True, color_hex=_BRAND_GREEN_DARK)

    # ── Separador visual ──────────────────────────────────────────────────────
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
    sep_clr.attrib['val'] = _BRAND_GREEN

    # ── Calcular alturas de filas ─────────────────────────────────────────────
    row_heights = _calculate_row_heights(items, cols=_VISUAL_GRID_COLS)
    cols       = _VISUAL_GRID_COLS
    card_w     = _VISUAL_CARD_WIDTH
    col_gap    = _VISUAL_COLUMN_GAP
    card_x     = _VISUAL_LEFT_MARGIN
    card_x2    = card_x + card_w + col_gap  # posición X de la 2ª columna
    row_gap    = _VISUAL_CARD_GAP

    # ── Grid de tarjetas (2 columnas × N filas) ───────────────────────────────
    y_cursor = _VISUAL_START_Y
    card_idx = 0
    num_rows = (len(items) + cols - 1) // cols

    for row in range(num_rows):
        row_h = row_heights[row] if row < len(row_heights) else _VISUAL_CARD_MIN_HEIGHT
        start = row * cols
        end   = min(start + cols, len(items))

        for col in range(start, end):
            item = items[col]
            titulo = (item.get('titulo') or '').strip()
            texto  = (item.get('texto')  or '').strip()
            if not titulo:
                continue

            # Alternar columna: 0 = izquierda, 1 = derecha
            col_pos = col - start
            x_pos = card_x if col_pos == 0 else card_x2
            card_id = 300 + card_idx
            card_idx += 1

            # Detectar categoría automáticamente (color de acento + badge)
            categoria_cfg = _detectar_categoria(titulo, texto)

            card = _add_card_shape(
                sp_tree, card_id, f'card_{card_idx}',
                x=x_pos, y=y_cursor,
                cx=card_w, cy=row_h,
                categoria_cfg=categoria_cfg,
                badge_text=str(card_idx),
            )

            txBody = card.find(f'{{{P}}}txBody')
            if txBody is not None:
                _add_card_para(txBody, titulo,
                               sz=_VISUAL_TITLE_FONT, bold=True,
                               color_hex=_VISUAL_TITLE_COLOR,
                               is_title=True)
                if texto and texto != titulo:
                    _add_card_para(txBody, texto,
                                   sz=_VISUAL_DESC_FONT, bold=False,
                                   color_hex=_VISUAL_DESC_COLOR)

        y_cursor += row_h + row_gap

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

        # Presentación SIEMPRE con tarjetas visuales de marca (la IA solo
        # enriquece el texto; la lógica de extracción del Excel no cambia).
        render_fn = _make_overflow_xml_visual

        # Un slide por cada chunk de ITEMS_PER_OVERFLOW items
        for i in range(0, len(items), ITEMS_PER_OVERFLOW):
            chunk   = items[i: i + ITEMS_PER_OVERFLOW]
            ov_xml  = render_fn(template_xml, torre, chunk)
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
