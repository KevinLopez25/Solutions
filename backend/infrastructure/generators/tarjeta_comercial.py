"""
infrastructure/generators/tarjeta_comercial.py
Toma el archivo PPTX de la tarjeta comercial seleccionada (un PPTX por comercial,
guardado en backend/templates/tarjetas_comerciales/<pais>/<Comercial>.pptx), copia
SUS DOS slides al deck generado y los inserta justo DESPUÉS del slide de
"Metodología Ágil" (detectado por contenido; respaldo: slide 19).

Corre al FINAL de la cadena de generadores para que ningún otro generador desplace
ni altere los slides recién insertados.

Riesgo técnico mitigado (compatibilidad de partes entre PPTX):
  - La relación slideLayout del slide copiado SIEMPRE se crea apuntando a un
    layout existente del deck destino. Los slides reales no declaran el layout
    en su XML (solo en .rels): sin esta relación PowerPoint exige "reparar".
  - Las imágenes (media) se copian con nombres únicos, se remapea su rId y se
    registra el Default de su extensión en [Content_Types].xml.
  - Los hyperlinks externos se conservan; cualquier otra referencia r:* sin
    relación válida (notesSlide, hyperlinks internos, tags...) se elimina del
    XML junto con los elementos que quedaron vacíos, para que el archivo no
    pida reparación ni pierda imágenes.
  - No se copian notesSlide (evita conflictos de notas duplicadas).
"""

import io
import posixpath
import re
import zipfile

from lxml import etree

P  = 'http://schemas.openxmlformats.org/presentationml/2006/main'
A  = 'http://schemas.openxmlformats.org/drawingml/2006/main'
R  = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
NS_REL     = 'http://schemas.openxmlformats.org/package/2006/relationships'
CT_NS      = 'http://schemas.openxmlformats.org/package/2006/content-types'
SLIDE_CT   = 'application/vnd.openxmlformats-officedocument.presentationml.slide+xml'
LAYOUT_REL = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout'
IMAGE_REL  = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/image'
HYPERLINK_REL = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink'

_MIME_BY_EXT = {
    'png': 'image/png', 'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
    'gif': 'image/gif', 'bmp': 'image/bmp', 'tiff': 'image/tiff',
    'emf': 'image/x-emf', 'wmf': 'image/x-wmf', 'svg': 'image/svg+xml',
    'webp': 'image/webp',
}

# Después del slide de "Metodología Ágil". Se detecta DINÁMICAMENTE buscando
# ese texto en los slides; si no existe, se usa esta posición de respaldo.
INSERT_AFTER_SLIDE_NUMBER = 19
METODOLOGIA_MARKER = 'METODOLOG'  # normalizado (sin tildes, mayúsculas)


def _normalize_name(value: str) -> str:
    """Quita tildes y normaliza para buscar/crear el archivo por nombre comercial."""
    import unicodedata
    s = unicodedata.normalize('NFKD', value or '')
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return re.sub(r'\s+', ' ', s.strip().upper())


def _normalize_name_tilde(value: str) -> str:
    """Normaliza a slug en minúsculas sin tildes (para carpetas de país)."""
    return _normalize_name(value).lower()


def _read_zip(pptx_bytes: bytes) -> dict[str, bytes]:
    with zipfile.ZipFile(io.BytesIO(pptx_bytes)) as z:
        return {name: z.read(name) for name in z.namelist()}


def _slide_order(files: dict[str, bytes]) -> list[str]:
    """Retorna paths de slides en el orden real de sldIdLst."""
    rels_root = etree.fromstring(files['ppt/_rels/presentation.xml.rels'])
    rid_map = {r.attrib['Id']: r.attrib['Target'] for r in rels_root}
    prs = etree.fromstring(files['ppt/presentation.xml'])
    ns = {'p': P, 'r': R}
    return ['ppt/' + rid_map[s.attrib[f'{{{R}}}id']]
            for s in prs.find('.//p:sldIdLst', ns)]


def _get_rels_path(slide_path: str) -> str:
    parts = slide_path.rsplit('/', 1)
    return f"{parts[0]}/_rels/{parts[1]}.rels"


def _guess_ext(target: str) -> str:
    ext = posixpath.splitext(target)[1].lstrip('.').lower()
    return ext if ext else 'png'


def _find_metodologia_index(order_paths: list[str], files: dict[str, bytes]) -> int:
    """
    Índice (0-based) del slide que contiene 'Metodología Ágil' según su texto.
    Si no existe, devuelve la posición de respaldo (INSERT_AFTER_SLIDE_NUMBER - 1).
    """
    for i, path in enumerate(order_paths):
        try:
            root = etree.fromstring(files[path])
        except Exception:
            continue
        text = ' '.join((t.text or '') for t in root.iter(f'{{{A}}}t'))
        if METODOLOGIA_MARKER in _normalize_name(text):
            return i
    return INSERT_AFTER_SLIDE_NUMBER - 1


def _ensure_ct_default(dest: dict, ext: str) -> None:
    """Garantiza que [Content_Types].xml tenga un Default para la extensión copiada."""
    if not ext:
        return
    ct_root = etree.fromstring(dest['[Content_Types].xml'])
    has = any(
        (d.get('Extension') or '').lower() == ext.lower()
        for d in ct_root.findall(f'{{{CT_NS}}}Default')
    )
    if not has:
        etree.SubElement(ct_root, f'{{{CT_NS}}}Default', {
            'Extension':   ext,
            'ContentType': _MIME_BY_EXT.get(ext.lower(), 'application/octet-stream'),
        })
        dest['[Content_Types].xml'] = etree.tostring(
            ct_root, xml_declaration=True, encoding='UTF-8', standalone=True)


def edit(pptx_bytes: bytes, config: dict, catalog_data: dict | None = None) -> bytes:
    """
    config: {
        tarjeta_comercial: str | None          // nombre del comercial (coincide con el archivo)
        tarjeta_comercial_pais: str | None     // slug del país (colombia, ecuador, mexico...)
    }
    """
    tarjeta = str(config.get('tarjeta_comercial') or '').strip()
    if not tarjeta:
        # Sin tarjeta seleccionada: no tocar nada.
        return pptx_bytes

    # ── Localizar el archivo de la tarjeta ─────────────────────────────────────
    from core.config import settings

    pais_slug = _normalize_name_tilde(config.get('tarjeta_comercial_pais') or '')
    base_carpeta = settings.templates_path / 'tarjetas_comerciales'
    if not base_carpeta.exists():
        print('[TARJETA] No existe la carpeta de tarjetas comerciales.')
        return pptx_bytes

    # Carpeta del país (si existe), sino la base.
    carpeta_pais = base_carpeta / pais_slug if pais_slug else None
    if carpeta_pais is not None and carpeta_pais.is_dir():
        carpeta = carpeta_pais
    else:
        carpeta = base_carpeta

    norm_target = _normalize_name(tarjeta)
    candidates = []
    for f in sorted(carpeta.iterdir()):
        if not f.is_file() or f.suffix.lower() != '.pptx':
            continue
        norm_file = _normalize_name(f.stem)
        candidates.append((norm_file, f))
        if norm_file == norm_target:
            return _insert(f, pptx_bytes)

    # Fallback: apertura parcial (buscar "pepi" encuentra "Pepito Perez")
    matched = [f for (norm_file, f) in candidates if norm_target in norm_file]
    if len(matched) == 1:
        return _insert(matched[0], pptx_bytes)

    print(f'[TARJETA] No se encontró un único archivo para "{tarjeta}"'
          f' en carpeta "{carpeta.name}" ({len(matched)} coincidencias).')
    return pptx_bytes
def _write_zip(files: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zout:
        for name, data in files.items():
            zout.writestr(name, data)
    return buf.getvalue()


def _validar_slides_nuevos(dest: dict[str, bytes], nums: list[int]) -> bool:
    """
    Verificación final de integridad de los slides insertados:
      1. Cada slide tiene relación slideLayout.
      2. Cero referencias r:* sin relación declarada (huérfanas).
      3. Cada imagen apunta a un media existente en el deck.
    Si algo falla, el llamador NO entrega la tarjeta (evita el 'archivo dañado').
    """
    for num in nums:
        try:
            rels_root = etree.fromstring(
                dest[f'ppt/slides/_rels/slide{num}.xml.rels'])
            rels = {r.attrib.get('Id'): r
                    for r in rels_root.findall(f'{{{NS_REL}}}Relationship')}
            slide_root = etree.fromstring(dest[f'ppt/slides/slide{num}.xml'])
        except Exception as exc:
            print(f'[TARJETA v2] slide{num}: XML ilegible ({exc}).')
            return False

        # 1) Layout presente.
        if not any(r.attrib.get('Type') == LAYOUT_REL for r in rels.values()):
            print(f'[TARJETA v2] slide{num}: sin relacion slideLayout.')
            return False

        # 2) Cero referencias huérfanas.
        for el in slide_root.iter():
            for key, val in el.attrib.items():
                if key.startswith('{%s}' % R) and val not in rels:
                    print(f'[TARJETA v2] slide{num}: ref huerfana {val}.')
                    return False

        # 3) Imágenes apuntan a media existente.
        for r in rels.values():
            if r.attrib.get('Type') == IMAGE_REL:
                target = posixpath.normpath('ppt/slides/' + r.attrib.get('Target', ''))
                if target not in dest:
                    print(f'[TARJETA v2] slide{num}: media faltante {target}.')
                    return False
    return True


def _update_app_xml(dest: dict[str, bytes], total_slides: int) -> None:
    """Actualiza el conteo de slides en docProps/app.xml (metadatos)."""
    if 'docProps/app.xml' not in dest:
        return
    try:
        ns_ep = 'http://schemas.openxmlformats.org/officeDocument/2006/extended-properties'
        root = etree.fromstring(dest['docProps/app.xml'])
        slides_el = root.find(f'{{{ns_ep}}}Slides')
        if slides_el is not None:
            slides_el.text = str(total_slides)
            dest['docProps/app.xml'] = etree.tostring(
                root, xml_declaration=True, encoding='UTF-8', standalone=True)
    except Exception:
        pass  # metadato informativo: nunca rompe la generación


def _insert(tarjeta_path, pptx_bytes: bytes) -> bytes:
    try:
        src_files = _read_zip(tarjeta_path.read_bytes())
    except Exception as exc:
        print(f'[TARJETA] No se pudo leer el PPTX de la tarjeta: {exc}')
        return pptx_bytes

    src_slides = sorted(
        (p for p in src_files if re.match(r'ppt/slides/slide\d+\.xml$', p)),
        key=lambda p: int(re.search(r'slide(\d+)', p).group(1)),
    )
    if not src_slides:
        print('[TARJETA] El archivo de tarjeta no tiene slides.')
        return pptx_bytes
    # Solo tomamos los 2 primeros slides (los que trae la tarjeta comercial).
    src_slides = src_slides[:2]

    dest = _read_zip(pptx_bytes)

    princ = 'ppt/presentation.xml'
    prs_root = etree.fromstring(dest[princ])
    sldIdLst = prs_root.find(f'.//{{{P}}}sldIdLst')
    order_paths = _slide_order(dest)

    # Layout válido en el destino (del primer slide).
    dest_layout_target = None
    first_slide = order_paths[0] if order_paths else None
    if first_slide:
        rels_fp = _get_rels_path(first_slide)
        if rels_fp in dest:
            rroot = etree.fromstring(dest[rels_fp])
            for rel in rroot.findall(f'{{{NS_REL}}}Relationship'):
                if rel.attrib.get('Type', '') == LAYOUT_REL:
                    dest_layout_target = rel.attrib.get('Target')
                    break

    existing_nums = [
        int(re.search(r'slide(\d+)', f).group(1))
        for f in dest
        if re.match(r'ppt/slides/slide\d+\.xml$', f)
    ]
    nxt = max(existing_nums) + 1 if existing_nums else 1
    new_nums = []
    for _ in src_slides:
        while f'ppt/slides/slide{nxt}.xml' in dest:
            nxt += 1
        new_nums.append(nxt)
        nxt += 1

    used_media = {name for name in dest if name.startswith('ppt/media/')}

    # Copiar cada slide y registrar sus relaciones en presentation.xml.rels.
    new_slides = []  # (new_num, slide_path)
    prs_rels_path = 'ppt/_rels/presentation.xml.rels'
    prs_rels_root = etree.fromstring(dest[prs_rels_path])
    rid_nums = [
        int(m.group(1))
        for r in prs_rels_root.findall(f'{{{NS_REL}}}Relationship')
        for m in [re.search(r'rId(\d+)', r.attrib.get('Id', ''))]
        if m
    ]

    new_rids = []
    for idx, src_path in enumerate(src_slides):
        new_num = new_nums[idx]
        new_path = f'ppt/slides/slide{new_num}.xml'
        root = etree.fromstring(src_files[src_path])

        new_rid = f'rId{max(rid_nums) + 1}'
        rid_nums.append(int(new_rid.replace('rId', '')))
        new_rids.append(new_rid)
        _copy_one(
            src_files, dest, root, src_path, new_num, new_path,
            idx, used_media, tarjeta_path, dest_layout_target,
        )

        etree.SubElement(prs_rels_root, f'{{{NS_REL}}}Relationship', {
            'Id': new_rid,
            'Type': f'{R}/slide',
            'Target': f'slides/slide{new_num}.xml',
        })

    dest[prs_rels_path] = etree.tostring(
        prs_rels_root, xml_declaration=True, encoding='UTF-8', standalone=True)

    # Insertar los sldId justo después del slide de "Metodología Ágil"
    # (o de la posición de respaldo si no existe).
    position = _find_metodologia_index(order_paths, dest)
    children = list(sldIdLst)
    for child in children:
        sldIdLst.remove(child)

    inserted = False
    for i, child in enumerate(children):
        sldIdLst.append(child)
        if i == position:
            _append_sld_ids(sldIdLst, new_rids)
            inserted = True
    if not inserted:
        _append_sld_ids(sldIdLst, new_rids)

    dest[princ] = etree.tostring(
        prs_root, xml_declaration=True, encoding='UTF-8', standalone=True)

    _update_app_xml(dest, total_slides=len(order_paths) + len(new_rids))

    # ── Verificación de integridad ANTES de entregar el archivo ────────────────
    # Si algo quedara sin resolver, se devuelve el deck SIN la tarjeta:
    # jamás entregamos un PPTX que PowerPoint marque como dañado.
    if not _validar_slides_nuevos(dest, new_nums):
        print('[TARJETA v2] VALIDACION FALLO: se omite la tarjeta para no '
              'entregar un archivo dañado. Revisa el PPTX de la tarjeta.')
        return pptx_bytes

    print(f'[TARJETA v2] Se insertaron {len(new_rids)} slide(s) de la tarjeta '
          f'"{tarjeta_path.name}" después del slide {position + 1} '
          f'(Metodología Ágil; verificación de integridad OK).')
    return _write_zip(dest)


def _append_sld_ids(sldIdLst, rids: list[str]) -> None:
    """Añade un <p:sldId> por cada rid, con id y r:id únicos."""
    max_sld_id = max((int(s.attrib['id']) for s in sldIdLst), default=0)
    for rid in rids:
        max_sld_id += 1
        sld = etree.Element(f'{{{P}}}sldId')
        sld.attrib['id'] = str(max_sld_id)
        sld.attrib[f'{{{R}}}id'] = rid
        sldIdLst.append(sld)


def _copy_one(src_files, dest, root, src_path, new_num, new_path, idx,
              used_media, tarjeta_path, dest_layout_target):
    """
    Copia un slide del origen al destino dejando TODAS sus relaciones resueltas:
      - slideLayout: SIEMPRE se agrega (apunta a un layout existente del deck
        destino). Sin esta relación PowerPoint marca el archivo como corrupto.
      - imágenes: se copia el archivo media con nombre único y se remapea el rId.
      - hyperlinks externos: se conservan tal cual (no requieren parte física).
      - cualquier otra referencia r:* no soportada (notesSlide, hyperlinks
        internos, tags, media...) se ELIMINA del XML: una referencia huérfana
        obliga a PowerPoint a "reparar" el archivo (y pierde las imágenes).
    """
    new_rels = _get_rels_path(new_path)

    # Quitar elementos con referencias propias (notas, transiciones, animaciones).
    for tag in ('notes', 'transition', 'timing'):
        el = root.find(f'{{{P}}}{tag}')
        if el is not None:
            root.remove(el)

    # ── Clasificar las relaciones del slide de origen ──────────────────────────
    entries = {}  # old_rid -> (type, target, external)
    src_rels_raw = src_files.get(_get_rels_path(src_path))
    if src_rels_raw:
        src_rels_root = etree.fromstring(src_rels_raw)
        for rel in src_rels_root.findall(f'{{{NS_REL}}}Relationship'):
            old_rid = rel.attrib.get('Id')
            if not old_rid:
                continue
            entries[old_rid] = (
                rel.attrib.get('Type', ''),
                rel.attrib.get('Target', ''),
                rel.attrib.get('TargetMode', '') == 'External',
            )

    new_rels_list = []   # (rid, type, target, external)
    rid_map = {}         # imágenes: old_rid -> new_rid
    keep_rids = {}       # hyperlinks externos: old_rid -> nuevo rid único

    # 1) Layout del destino SIEMPRE presente.
    new_rels_list.append(('rId1', LAYOUT_REL,
                          dest_layout_target or '../slideLayouts/slideLayout1.xml',
                          False))

    # 2) Imágenes → copiar el media con nombre único y remapear.
    for old_rid, (rtype, target, external) in entries.items():
        if rtype != IMAGE_REL or external:
            continue
        media_path = posixpath.normpath('ppt/slides/' + target)
        if media_path not in src_files:
            continue
        ext = _guess_ext(target)
        base = f'tarjeta_{_normalize_name(tarjeta_path.stem).replace(" ", "_")}_{idx + 1}_{old_rid}'
        media_name = f'ppt/media/{base}.{ext}'
        c = 1
        while media_name in dest or media_name in used_media:
            media_name = f'ppt/media/{base}_{c}.{ext}'
            c += 1
        dest[media_name] = src_files[media_path]
        used_media.add(media_name)
        _ensure_ct_default(dest, ext)
        new_rid = f'rIdImg{idx + 1}_{len(rid_map) + 1}'
        rid_map[old_rid] = new_rid
        new_rels_list.append(
            (new_rid, IMAGE_REL, f'../media/{posixpath.basename(media_name)}', False))

    # 3) Hyperlinks externos → se conservan pero con ID ÚNICO nuevo (sin riesgo
    #    de colisionar con rId1 del layout ni entre ellos).
    link_seq = 0
    for old_rid, (rtype, target, external) in entries.items():
        if rtype == HYPERLINK_REL and external and old_rid not in rid_map:
            link_seq += 1
            new_rid = f'rIdLink{idx + 1}_{link_seq}'
            keep_rids[old_rid] = new_rid
            new_rels_list.append((new_rid, HYPERLINK_REL, target, True))

    # 4) Remapear o limpiar TODA referencia r:* del XML del slide.
    for el in root.iter():
        for key in list(el.attrib):
            if not key.startswith('{%s}' % R):
                continue
            val = el.attrib[key]
            if val in rid_map:
                el.attrib[key] = rid_map[val]
            elif val in keep_rids:
                el.attrib[key] = keep_rids[val]
            else:
                del el.attrib[key]

    # 5) Limpieza de elementos que quedaron sin referencia (inválidos si
    #    se dejan vacíos: disparan la reparación de PowerPoint).
    for hlink in root.findall(f'.//{{{A}}}hlinkClick') + root.findall(f'.//{{{A}}}hlinkHover'):
        if not any(k.startswith('{%s}' % R) for k in hlink.attrib):
            hlink.getparent().remove(hlink)
    for cust in root.findall(f'.//{{{P}}}custDataLst'):
        if len(cust) == 0:
            cust.getparent().remove(cust)
    for pic in list(root.iter(f'{{{P}}}pic')):
        blip = pic.find(f'.//{{{A}}}blip')
        if blip is None or not (
            blip.get(f'{{{R}}}embed') or blip.get(f'{{{R}}}link')
        ):
            pic.getparent().remove(pic)

    dest[new_path] = etree.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True)

    # 6) Escribir el .rels completo del nuevo slide.
    rels_root = etree.Element(f'{{{NS_REL}}}Relationships', nsmap={None: NS_REL})
    for rid, rtype, tgt, external in new_rels_list:
        rel = etree.SubElement(rels_root, f'{{{NS_REL}}}Relationship')
        rel.set('Id', rid)
        rel.set('Type', rtype)
        rel.set('Target', tgt)
        if external:
            rel.set('TargetMode', 'External')
    dest[new_rels] = etree.tostring(rels_root, xml_declaration=True, encoding='UTF-8', standalone=True)

    # 7) Registrar en [Content_Types].xml
    ct_root = etree.fromstring(dest['[Content_Types].xml'])
    etree.SubElement(ct_root, f'{{{CT_NS}}}Override', {
        'PartName':    f'/ppt/slides/slide{new_num}.xml',
        'ContentType': SLIDE_CT,
    })
    dest['[Content_Types].xml'] = etree.tostring(
        ct_root, xml_declaration=True, encoding='UTF-8', standalone=True)