"""
infrastructure/generators/oferta_economica.py

Llena las columnas 'Perfiles' (col 0) y 'Horas' (col 2) de la tabla
en la diapositiva 'Oferta Económica'.

Reglas:
  - Slide identificado por el GraphicFrame 'Tabla 3' (único en el template).
  - Solo se modifican las filas de datos 0-4 (la fila 5 = Total queda intacta).
  - Solo se escriben columnas 0 (Perfiles) y 2 (Horas); el resto queda quieto.
  - Si hay menos perfiles que filas, las filas sobrantes quedan vacías.
  - Estilos, colores y bordes de las celdas no se tocan.
"""

import io
import zipfile
from lxml import etree

P = 'http://schemas.openxmlformats.org/presentationml/2006/main'
A = 'http://schemas.openxmlformats.org/drawingml/2006/main'
R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'

OFERTA_MARKER = 'Tabla 3'   # nombre del GraphicFrame en la diapositiva
DATA_ROWS     = 5           # filas editables (0-4); fila 5 = Total, no se toca


def _get_slide_order(pptx_bytes):
    with zipfile.ZipFile(io.BytesIO(pptx_bytes)) as z:
        rels    = etree.fromstring(z.read('ppt/_rels/presentation.xml.rels'))
        rid_map = {r.attrib['Id']: r.attrib['Target'] for r in rels}
        prs     = etree.fromstring(z.read('ppt/presentation.xml'))
        ns      = {'p': P, 'r': R}
        return ['ppt/' + rid_map[s.attrib[f'{{{R}}}id']]
                for s in prs.find('.//p:sldIdLst', ns)]


def _find_oferta_slide(slides_order, files_dict):
    for slide_path in slides_order:
        content = files_dict.get(slide_path, b'')
        if b'Tabla 3' not in content:
            continue
        try:
            root = etree.fromstring(content)
            for gf in root.iter(f'{{{P}}}graphicFrame'):
                nvPr = gf.find(f'.//{{{P}}}cNvPr')
                if nvPr is not None and nvPr.get('name', '') == OFERTA_MARKER:
                    return slide_path
        except Exception:
            pass
    return None


def _set_cell_text(cell, text):
    """Reemplaza el texto del primer run de una celda preservando todos los estilos."""
    txBody = cell.find(f'{{{A}}}txBody')
    if txBody is None:
        return
    para = txBody.find(f'{{{A}}}p')
    if para is None:
        return
    runs = para.findall(f'{{{A}}}r')
    if runs:
        t_el = runs[0].find(f'{{{A}}}t')
        if t_el is not None:
            t_el.text = text
        for extra in runs[1:]:
            para.remove(extra)
    else:
        r_el = etree.SubElement(para, f'{{{A}}}r')
        t_el = etree.SubElement(r_el, f'{{{A}}}t')
        t_el.text = text


def edit(pptx_bytes, config, catalog_data=None):
    excel_data     = config.get('excel_data') or {}
    excel_perfiles = excel_data.get('perfiles') or []

    print('[OFERTA_ECONOMICA] Perfiles recibidos: %d' % len(excel_perfiles))
    for i, p in enumerate(excel_perfiles[:5]):
        print('[OFERTA_ECONOMICA]   [%d] perfil=%r  personas=%r  horas=%r' % (
            i, p.get('perfil'), p.get('personas'), p.get('horas')))

    files_dict = {}
    with zipfile.ZipFile(io.BytesIO(pptx_bytes)) as zin:
        files_dict = {name: zin.read(name) for name in zin.namelist()}

    slides_order = _get_slide_order(pptx_bytes)
    slide_path   = _find_oferta_slide(slides_order, files_dict)

    if not slide_path:
        print('[OFERTA_ECONOMICA] Diapositiva no encontrada, se omite.')
        return pptx_bytes

    root = etree.fromstring(files_dict[slide_path])

    tbl = None
    for gf in root.iter(f'{{{P}}}graphicFrame'):
        nvPr = gf.find(f'.//{{{P}}}cNvPr')
        if nvPr is not None and nvPr.get('name', '') == OFERTA_MARKER:
            tbl = gf.find(f'.//{{{A}}}tbl')
            break

    if tbl is None:
        print('[OFERTA_ECONOMICA] Tabla no encontrada en la diapositiva, se omite.')
        return pptx_bytes

    rows = tbl.findall(f'{{{A}}}tr')

    for row_idx in range(min(DATA_ROWS, len(rows) - 1)):
        cells = rows[row_idx].findall(f'{{{A}}}tc')

        if row_idx < len(excel_perfiles):
            entry    = excel_perfiles[row_idx]
            nombre   = str(entry.get('perfil') or '').strip()
            personas = entry.get('personas')
            horas    = entry.get('horas')
            try:
                cantidad_text = str(int(personas)) if personas not in (None, '') else ''
            except (ValueError, TypeError):
                cantidad_text = ''
            try:
                horas_text = str(int(horas)) if horas not in (None, '') and int(horas) != 0 else ''
            except (ValueError, TypeError):
                horas_text = ''
        else:
            nombre        = ''
            cantidad_text = ''
            horas_text    = ''

        if cells:
            _set_cell_text(cells[0], nombre)
        if len(cells) > 1:
            _set_cell_text(cells[1], cantidad_text)
        if len(cells) > 2:
            _set_cell_text(cells[2], horas_text)

    files_dict[slide_path] = etree.tostring(
        root, xml_declaration=True, encoding='UTF-8', standalone=True
    )

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zout:
        for name, data in files_dict.items():
            zout.writestr(name, data)

    filled = min(len(excel_perfiles), DATA_ROWS)
    print(f'[OFERTA_ECONOMICA] {filled} perfiles escritos en {slide_path}.')
    return buf.getvalue()
