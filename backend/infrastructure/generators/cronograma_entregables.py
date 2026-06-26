"""
infrastructure/generators/cronograma_entregables.py

Edita slide de Entregables del PPTX.

Lógica:
  - Entregables vienen de la BD (tabla entregables via catalog_data),
    filtrados por las torres activas del config.
  - Máximo 4 torres por slide (columnas). Si hay más, se duplica el slide.
  - 1 col → centrado. 2 cols → centrados. 3 cols → posiciones del template.
  - 4 cols → layout escalado al 75% para que quepan las 4 columnas.
  - Los rectángulos de fondo se mueven/eliminan junto con el título y la lista.
"""

import copy
import io
import re
import zipfile
import unicodedata
from lxml import etree

A = 'http://schemas.openxmlformats.org/drawingml/2006/main'
P = 'http://schemas.openxmlformats.org/presentationml/2006/main'
R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
NS_REL = 'http://schemas.openxmlformats.org/package/2006/relationships'

ENTREGABLES_LIST_SHAPES = {'CuadroTexto 4', 'CuadroTexto 13', 'CuadroTexto 17'}

SLIDE_WIDTH_EMU  = 9144000

# ── Métricas layout 3 columnas (posiciones del template) ─────────────────────
_ENT_PITCH       = 2750433   # distancia entre inicios de columnas (EMU)
_ENT_TITLE_CX    = 2725809   # ancho del título de columna
_ENT_LIST_CX     = 2300506   # ancho de la lista de entregables
_ENT_LIST_OFF_X  = 15335     # lista_x = title_x + offset
_ENT_RECT_CX     = 2560844   # ancho del rectángulo de fondo
_ENT_RECT_OFF_X  = -90615    # rect_x  = title_x + offset (rect a la izq del título)
_ENT_RECT_PREFIX = 'Rectángulo: esquinas redondeadas'

# ── Métricas layout 4 columnas (75 % del layout de 3) ────────────────────────
_ENT4_PITCH      = 2062825   # round(_ENT_PITCH   * 0.75)
_ENT4_TITLE_CX   = 2044357   # round(_ENT_TITLE_CX * 0.75)
_ENT4_LIST_CX    = 1725380   # round(_ENT_LIST_CX  * 0.75)
_ENT4_LIST_OFF_X = 11501     # round(_ENT_LIST_OFF_X * 0.75)
_ENT4_RECT_CX    = 1920633   # round(_ENT_RECT_CX  * 0.75)
_ENT4_RECT_OFF_X = -67961    # round(_ENT_RECT_OFF_X * 0.75)

MAX_PER_SLIDE = 4   # máximo de torres por slide de entregables


# ══════════════════════════════ utilidades ════════════════════════════════════

def _norm(s):
    s = (s or '').strip().upper()
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return re.sub(r'\s+', ' ', s).strip()

def _esc(t):
    return (t or '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

def _sp_off_x(sp):
    spPr = sp.find(f'{{{P}}}spPr')
    if spPr is None: return 0
    xfrm = spPr.find(f'{{{A}}}xfrm')
    if xfrm is None: return 0
    off = xfrm.find(f'{{{A}}}off')
    return int(off.attrib.get('x', 0)) if off is not None else 0

def _sp_set_x_cx(sp, new_x, new_cx):
    spPr = sp.find(f'{{{P}}}spPr')
    if spPr is None: return
    xfrm = spPr.find(f'{{{A}}}xfrm')
    if xfrm is None: return
    off = xfrm.find(f'{{{A}}}off')
    ext = xfrm.find(f'{{{A}}}ext')
    if off is not None: off.attrib['x'] = str(new_x)
    if ext is not None: ext.attrib['cx'] = str(new_cx)

def _sp_get_cx(sp) -> int:
    spPr = sp.find(f'{{{P}}}spPr')
    if spPr is None: return 0
    xfrm = spPr.find(f'{{{A}}}xfrm')
    if xfrm is None: return 0
    ext = xfrm.find(f'{{{A}}}ext')
    return int(ext.attrib.get('cx', 0)) if ext is not None else 0

def _sp_set_x(sp, new_x):
    spPr = sp.find(f'{{{P}}}spPr')
    if spPr is None: return
    xfrm = spPr.find(f'{{{A}}}xfrm')
    if xfrm is None: return
    off = xfrm.find(f'{{{A}}}off')
    if off is not None: off.attrib['x'] = str(new_x)


# ══════════════════════════════ carga de datos ════════════════════════════════

def _load_entregables(torres_activas, catalog_data: dict):
    entregables_db: list[dict] = catalog_data.get('entregables_db', [])

    ent_por_torre: dict[str, list[str]] = {
        _norm(g['torre']): g['items']
        for g in entregables_db
    }

    resultado = []
    for torre in torres_activas:
        key   = _norm(torre)
        items = ent_por_torre.get(key, [])
        if not items:
            for k in ent_por_torre:
                if key in k or k in key:
                    items = ent_por_torre[k]
                    break
        if items:
            items_limpios = [i for i in items if (i or '').strip()]
            resultado.append({'torre': torre, 'items': items_limpios[:7]})

    print(f'[ENTREGABLES] Torres activas  : {torres_activas}')
    print(f'[ENTREGABLES] Con entregables : {[g["torre"] for g in resultado]}')
    return resultado


# ══════════════════════════════ navegación PPTX ═══════════════════════════════

def _get_slide_order(pptx_bytes):
    with zipfile.ZipFile(io.BytesIO(pptx_bytes)) as z:
        rels    = etree.fromstring(z.read('ppt/_rels/presentation.xml.rels'))
        rid_map = {r.attrib['Id']: r.attrib['Target'] for r in rels}
        prs     = etree.fromstring(z.read('ppt/presentation.xml'))
        ns      = {'p': P, 'r': R}
        return ['ppt/' + rid_map[s.attrib[f'{{{R}}}id']]
                for s in prs.find('.//p:sldIdLst', ns)]


def _find_entregables_slide(slides_order, files_dict):
    for path in slides_order:
        root = etree.fromstring(files_dict[path])
        names = {
            nvpr.attrib.get('name', '')
            for sp in root.iter(f'{{{P}}}sp')
            for nvpr in [sp.find(f'.//{{{P}}}cNvPr')]
            if nvpr is not None
        }
        if len(ENTREGABLES_LIST_SHAPES & names) >= 2:
            return path
    fallback_idx = min(6, len(slides_order) - 1)
    print(f'[ENTREGABLES] Advertencia: slide no encontrado por shapes, usando índice {fallback_idx}.')
    return slides_order[fallback_idx]


def _duplicate_slide(files_dict, src_path, insert_after_path):
    SLIDE_CT = 'application/vnd.openxmlformats-officedocument.presentationml.slide+xml'
    CT_NS    = 'http://schemas.openxmlformats.org/package/2006/content-types'

    existing_nums = [
        int(re.search(r'slide(\d+)', f).group(1))
        for f in files_dict
        if re.match(r'ppt/slides/slide\d+\.xml$', f)
    ]
    new_num        = max(existing_nums) + 1
    new_slide_path = f'ppt/slides/slide{new_num}.xml'
    files_dict[new_slide_path] = files_dict[src_path]

    ct_root = etree.fromstring(files_dict['[Content_Types].xml'])
    etree.SubElement(ct_root, f'{{{CT_NS}}}Override', {
        'PartName':    f'/ppt/slides/slide{new_num}.xml',
        'ContentType': SLIDE_CT,
    })
    files_dict['[Content_Types].xml'] = etree.tostring(
        ct_root, xml_declaration=True, encoding='UTF-8', standalone=True)

    def _rels_path(p):
        parts = p.rsplit('/', 1)
        return f"{parts[0]}/_rels/{parts[1]}.rels"

    src_rels = _rels_path(src_path)
    new_rels = _rels_path(new_slide_path)
    if src_rels in files_dict:
        rels_root = etree.fromstring(files_dict[src_rels])
        for rel in rels_root.findall(f'{{{NS_REL}}}Relationship'):
            if 'notesSlide' in rel.attrib.get('Type', ''):
                rels_root.remove(rel)
        files_dict[new_rels] = etree.tostring(
            rels_root, xml_declaration=True, encoding='UTF-8', standalone=True)

    prs_rels_path = 'ppt/_rels/presentation.xml.rels'
    prs_rels_root = etree.fromstring(files_dict[prs_rels_path])

    ref_target = insert_after_path.replace('ppt/', '')
    ref_rid = next((
        r.attrib['Id']
        for r in prs_rels_root.findall(f'{{{NS_REL}}}Relationship')
        if r.attrib.get('Target', '') == ref_target
    ), None)

    rid_nums = [
        int(m.group(1))
        for r in prs_rels_root.findall(f'{{{NS_REL}}}Relationship')
        for m in [re.search(r'rId(\d+)', r.attrib.get('Id', ''))]
        if m
    ]
    new_rid = f'rId{max(rid_nums) + 1}'
    etree.SubElement(prs_rels_root, f'{{{NS_REL}}}Relationship', {
        'Id':     new_rid,
        'Type':   f'{R}/slide',
        'Target': f'slides/slide{new_num}.xml',
    })
    files_dict[prs_rels_path] = etree.tostring(
        prs_rels_root, xml_declaration=True, encoding='UTF-8', standalone=True)

    prs_root = etree.fromstring(files_dict['ppt/presentation.xml'])
    sldIdLst = prs_root.find(f'.//{{{P}}}sldIdLst')
    max_id   = max(int(s.attrib['id']) for s in sldIdLst)
    new_sld  = etree.Element(f'{{{P}}}sldId')
    new_sld.attrib['id']         = str(max_id + 1)
    new_sld.attrib[f'{{{R}}}id'] = new_rid

    children = list(sldIdLst)
    for child in children:
        sldIdLst.remove(child)
    inserted = False
    for child in children:
        sldIdLst.append(child)
        if child.attrib.get(f'{{{R}}}id') == ref_rid and not inserted:
            sldIdLst.append(new_sld)
            inserted = True
    if not inserted:
        sldIdLst.append(new_sld)

    files_dict['ppt/presentation.xml'] = etree.tostring(
        prs_root, xml_declaration=True, encoding='UTF-8', standalone=True)
    return new_slide_path


# ══════════════════════════════ edición del slide ═════════════════════════════

_ICON_MAX_X = int(SLIDE_WIDTH_EMU * 0.85)  # excluye logo (extremo derecho, ~88%)


def _collect_shapes(root):
    titulos_raw = []
    listas_raw  = []
    rects_raw   = []
    icons_raw   = []

    for sp in root.iter(f'{{{P}}}sp'):
        nvpr = sp.find(f'.//{{{P}}}cNvPr')
        if nvpr is None: continue
        name = nvpr.attrib.get('name', '')

        if name.startswith(_ENT_RECT_PREFIX):
            rects_raw.append(sp)
            continue

        txb = sp.find(f'{{{P}}}txBody')
        if txb is None: continue
        txt = ''.join(t.text or '' for t in txb.findall(f'.//{{{A}}}t')).strip()

        if name == 'Título 1' and 'Entregables de' in txt:
            titulos_raw.append(sp)
        elif name in ENTREGABLES_LIST_SHAPES:
            listas_raw.append(sp)

    # Íconos: pics que no son fondo (x<=0) ni logo (x>80% del slide)
    for pic in root.iter(f'{{{P}}}pic'):
        x = _sp_off_x(pic)
        if 0 < x < _ICON_MAX_X:
            icons_raw.append(pic)

    return (sorted(titulos_raw, key=_sp_off_x),
            sorted(listas_raw,  key=_sp_off_x),
            sorted(rects_raw,   key=_sp_off_x),
            sorted(icons_raw,   key=_sp_off_x))


def _clone_col(spTree, src_sp):
    existing_ids = [
        int(el.attrib['id'])
        for el in spTree.iter()
        if 'id' in el.attrib and el.attrib['id'].isdigit()
    ]
    next_id = max(existing_ids, default=0) + 1
    new_sp  = copy.deepcopy(src_sp)
    for el in new_sp.iter():
        if 'id' in el.attrib and el.attrib['id'].isdigit():
            el.attrib['id'] = str(next_id)
            next_id += 1
    spTree.append(new_sp)
    return new_sp


def _fill_titulo(sp, nombre_torre):
    txb = sp.find(f'{{{P}}}txBody')
    if txb is None: return
    all_t = txb.findall(f'.//{{{A}}}t')
    first_done = False
    for t in all_t:
        if not first_done and 'Entregables de' in (t.text or ''):
            first_done = True
        elif first_done:
            t.text = nombre_torre
            break


def _font_sz(n: int) -> str:
    """Tamaño de fuente en centésimas de punto según cantidad de ítems."""
    if n <= 4: return '1000'
    if n <= 6: return '900'
    return '800'


def _fill_lista(sp, items):
    txb = sp.find(f'{{{P}}}txBody')
    if txb is None: return

    sz = _font_sz(len(items))

    # normAutofit: PowerPoint comprime el texto si aún no cabe en la caja fija
    bodyPr = txb.find(f'{{{A}}}bodyPr')
    if bodyPr is not None:
        for child in list(bodyPr):
            if etree.QName(child.tag).localname in ('noAutofit', 'normAutofit', 'spAutoFit'):
                bodyPr.remove(child)
        etree.SubElement(bodyPr, f'{{{A}}}normAutofit')

    existing_ps = txb.findall(f'{{{A}}}p')
    template_p  = existing_ps[0] if existing_ps else None

    for p in existing_ps:
        txb.remove(p)

    for item in items:
        if not (item or '').strip():
            continue
        if template_p is not None:
            new_p = copy.deepcopy(template_p)
            for r_el in new_p.findall(f'{{{A}}}r'):
                rPr = r_el.find(f'{{{A}}}rPr')
                if rPr is not None:
                    rPr.attrib['sz'] = sz
                    rPr.attrib.pop('err', None)
                t_el = r_el.find(f'{{{A}}}t')
                if t_el is not None:
                    t_el.text = item
                break
            endPr = new_p.find(f'{{{A}}}endParaRPr')
            if endPr is not None:
                endPr.attrib['sz'] = sz
            txb.append(new_p)
        else:
            p_xml = (f'<a:p xmlns:a="{A}"><a:r>'
                     f'<a:rPr sz="{sz}" dirty="0"/>'
                     f'<a:t>• {_esc(item)}</a:t>'
                     f'</a:r></a:p>')
            txb.append(etree.fromstring(p_xml))


def _edit_entregables_slide(xml_bytes, chunk):
    root   = etree.fromstring(xml_bytes)
    spTree = root.find(f'.//{{{P}}}spTree')
    n_use  = min(len(chunk), MAX_PER_SLIDE)

    titulos, listas, rects, icons = _collect_shapes(root)

    if n_use == 4 and len(titulos) == 3:
        if rects:   rects.append(_clone_col(spTree, rects[-1]))
        if titulos: titulos.append(_clone_col(spTree, titulos[-1]))
        if listas:  listas.append(_clone_col(spTree, listas[-1]))
        if icons:   icons.append(_clone_col(spTree, icons[-1]))

    for i, grupo in enumerate(chunk[:n_use]):
        if i < len(titulos):
            _fill_titulo(titulos[i], grupo['torre'])
        if i < len(listas):
            _fill_lista(listas[i], grupo['items'])

    for i in range(n_use, len(titulos)):
        spTree.remove(titulos[i])
    for i in range(n_use, len(listas)):
        spTree.remove(listas[i])
    for i in range(n_use, len(rects)):
        spTree.remove(rects[i])
    for i in range(n_use, len(icons)):
        spTree.remove(icons[i])

    if n_use == 4:
        pitch    = _ENT4_PITCH;    title_cx = _ENT4_TITLE_CX
        list_cx  = _ENT4_LIST_CX;  list_dx  = _ENT4_LIST_OFF_X
        rect_cx  = _ENT4_RECT_CX;  rect_dx  = _ENT4_RECT_OFF_X
    else:
        pitch    = _ENT_PITCH;     title_cx = _ENT_TITLE_CX
        list_cx  = _ENT_LIST_CX;   list_dx  = _ENT_LIST_OFF_X
        rect_cx  = _ENT_RECT_CX;   rect_dx  = _ENT_RECT_OFF_X

    if n_use != 3 and n_use > 0:
        total_w = (n_use - 1) * pitch + title_cx
        start_x = (SLIDE_WIDTH_EMU - total_w) // 2
        for i in range(n_use):
            tx = start_x + i * pitch
            if i < len(titulos): _sp_set_x_cx(titulos[i], tx,           title_cx)
            if i < len(listas):  _sp_set_x_cx(listas[i],  tx + list_dx, list_cx)
            if i < len(rects):   _sp_set_x_cx(rects[i],   tx + rect_dx, rect_cx)
            if i < len(icons):
                icon_cx = _sp_get_cx(icons[i])
                _sp_set_x(icons[i], tx + (title_cx - icon_cx) // 2)

    return etree.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True)


# ══════════════════════════════ entry point ═══════════════════════════════════

def edit(pptx_bytes, config, catalog_data=None):
    excel_data        = config.get('excel_data') or {}
    excel_torres      = excel_data.get('torres', [])
    excel_entregables = excel_data.get('entregables', [])
    torres_sel        = config.get('torres_seleccionadas', [])
    opciones          = config.get('opciones', {})
    usar_genericos    = bool(opciones.get('entregables', True))

    torres_activas = [t['nombre'] for t in excel_torres] if excel_torres else torres_sel

    if excel_entregables:
        print(f'[ENTREGABLES] Usando entregables del Excel del usuario: {[e["torre"] for e in excel_entregables]}')

        def _split_excel_items(raw_items):
            result = []
            for i in raw_items:
                for sub in re.split(r'[\r\n]+', i or ''):
                    sub = sub.strip()
                    if sub:
                        result.append(sub)
            return result[:7]

        entregables_grupos = [
            {'torre': e['torre'], 'items': _split_excel_items(e['items'])}
            for e in excel_entregables
            if e.get('items')
        ]
        if usar_genericos:
            torres_con_excel = {_norm(e['torre']) for e in excel_entregables if e.get('items')}
            catalogo = _load_entregables(torres_activas, catalog_data or {})
            for grupo in catalogo:
                if _norm(grupo['torre']) not in torres_con_excel:
                    entregables_grupos.append(grupo)
    else:
        entregables_grupos = _load_entregables(torres_activas, catalog_data or {})

    chunks = [entregables_grupos[i:i + MAX_PER_SLIDE]
              for i in range(0, len(entregables_grupos), MAX_PER_SLIDE)]
    if not chunks:
        chunks = [[]]

    print(f'[ENTREGABLES] Slides necesarios: {len(chunks)}')

    files_dict = {}
    with zipfile.ZipFile(io.BytesIO(pptx_bytes)) as zin:
        files_dict = {name: zin.read(name) for name in zin.namelist()}

    slides_order  = _get_slide_order(pptx_bytes)
    ent_slide_key = _find_entregables_slide(slides_order, files_dict)
    template_xml  = files_dict[ent_slide_key]

    files_dict[ent_slide_key] = _edit_entregables_slide(template_xml, chunks[0])

    prev_path = ent_slide_key
    for chunk in chunks[1:]:
        new_path = _duplicate_slide(files_dict, ent_slide_key, prev_path)
        files_dict[new_path] = _edit_entregables_slide(template_xml, chunk)
        prev_path = new_path

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zout:
        for name, data in files_dict.items():
            zout.writestr(name, data)
    return buf.getvalue()
