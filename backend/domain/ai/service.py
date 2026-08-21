import base64
import copy
import io
import json
import posixpath
import re
import time
import zipfile

from lxml import etree

from core.groq_client import create_chat_completion

SYSTEM_PROMPT = (
    "Eres un asistente experto especializado en revisar y optimizar propuestas comerciales de TI. "
    "\n\n"
    "ERRORES COMUNES A DETECTAR:"
    "\n1. **Redundancia de títulos**: Cuando se antepone 'desarrollador' a otros roles como:"
    "\n   - 'desarrollador analista de requerimientos' → debe ser solo 'Analista de Requerimientos'"
    "\n   - 'desarrollador analista funcional' → debe ser 'Analista Funcional'"
    "\n   - 'desarrollador arquitecto' → debe ser 'Arquitecto de Soluciones'"
    "\n   - 'desarrollador scrum master' → debe ser 'Scrum Master'"
    "\n   - 'desarrollador pmo' → debe ser 'PMO'"
    "\n2. **Inconsistencia de nomenclatura**: Usar nombres de roles de forma inconsistente"
    "\n3. **Redacción confusa**: Oraciones poco claras o mal estructuradas"
    "\n\n"
    "Cuando el usuario adjunta un archivo, trátalo como la propuesta generada por el proyecto y utilízalo para revisar los roles, la escritura y la estructura."
    "\n\n"
    "CÓMO RESPONDER:"
    "\n- Si encuentras errores, explica el problema de forma clara"
    "\n- Sugiere la corrección específica"
    "\n- Mantén un tono profesional pero accesible"
    "\n- Si el texto está bien, confirma que es correcto"
    "\n- Proporciona sugerencias de mejora cuando sea relevante"
    "\n\n"
    "Sé conciso y directo en tus respuestas."
)

EDIT_SYSTEM_PROMPT = (
    "Eres un asistente experto en corregir nombres de roles en propuestas PPTX. "
    "Tu única tarea es encontrar texto EXACTO que ya existe en el documento y proponer su corrección. "
    "\n\nREGLAS ESTRICTAS:"
    "\n- SOLO puedes reemplazar texto que aparece literalmente en el documento extraído."
    "\n- NUNCA agregues perfiles, roles, secciones ni contenido nuevo."
    "\n- NUNCA dupliques contenido existente."
    "\n- NUNCA cambies la cantidad de perfiles o roles que ya están en el documento."
    "\n- El campo 'to' debe ser únicamente la corrección del nombre, con la misma cantidad de información que el 'from'."
    "\n- Ejemplos de correcciones válidas: 'desarrollador ingeniero de datos' → 'Ingeniero de Datos', "
    "'desarrollador analista de requerimientos' → 'Analista de Requerimientos'."
    "\n\nDevuelve ÚNICAMENTE un objeto JSON con la estructura: "
    "{\"replacements\": [{\"from\": \"texto exacto del documento\", \"to\": \"texto corregido\"}, ...]}. "
    "Si no hay correcciones necesarias devuelve {\"replacements\": []}. "
    "No escribas nada fuera del JSON."
)

CONVERSATIONAL_SYSTEM_PROMPT = (
    "Eres un asistente experto en propuestas comerciales de TI. "
    "Puedes responder preguntas sobre la propuesta cargada. "
    "Las correcciones de perfiles se aplican automáticamente por código — no necesitas generarlas. "
    "Responde de forma concisa y en español."
)

AS_IS_TO_BE_SYSTEM_PROMPT = (
    "Eres un asistente experto en redactar descripciones AS-IS y TO-BE para propuestas comerciales de TI. "
    "Tu tarea es mejorar profesionalmente el estado actual y generar un estado futuro aspiracional a partir del contexto del proyecto. "
    "Responde SOLO con un objeto JSON válido con las claves 'as_is' y 'to_be'. "
    "No agregues explicaciones adicionales ni ningún texto fuera del JSON."
)

PPTX_NS = {
    'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
}

_LOGO_SHAPE_PREFIX = 'Rectángulo redondeado'
_MIME_TO_EXT = {
    'image/png': 'png', 'image/jpeg': 'jpg', 'image/jpg': 'jpg',
    'image/gif': 'gif', 'image/webp': 'webp', 'image/svg+xml': 'svg',
}
_NS_P    = 'http://schemas.openxmlformats.org/presentationml/2006/main'
_NS_A    = 'http://schemas.openxmlformats.org/drawingml/2006/main'
_NS_R    = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
_NS_RELS = 'http://schemas.openxmlformats.org/package/2006/relationships'
_REL_IMAGE_TYPE = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/image'
_FILL_TAGS = ['solidFill', 'gradFill', 'noFill', 'blipFill', 'pattFill', 'grpFill']


VERIFY_SYSTEM_PROMPT = (
    "Eres un verificador de calidad de contenido para propuestas comerciales de TI. "
    "Tu unica tarea es validar que una descripcion asignada a un perfil/rol sea "
    "VERIDICA, CONCRETA y coherente con el contexto real del proyecto. "
    "NO inventes tecnologias, certificaciones ni responsabilidades que no se deriven "
    "del rol ni del contexto proporcionado. "
    "Responde SOLO con un objeto JSON valido: "
    "{\"ok\": true/false, \"corregida\": \"texto corregido si hace falta\", \"motivo\": \"breve razon\"}. "
    "Si la descripcion es correcta, devuelve ok=true y corregida igual a la original. "
    "No escribas nada fuera del JSON."
)


def _project_context_for_verification(db_session, torre_nombre: str | None = None) -> str:
    """Construye un contexto breve y REAL del proyecto para verificar descripciones."""
    try:
        from infrastructure.repositories import catalogo_repository as repo
        torres = repo.get_torres(db_session, solo_activas=True)
        if torre_nombre:
            torres = [t for t in torres if _normalize_text(t.nombre) == _normalize_text(torre_nombre)] or torres
        lines = []
        for t in torres[:6]:
            perfiles = repo.get_perfiles(db_session, torre_id=t.id)
            consideraciones = repo.get_consideraciones(db_session, torre_id=t.id)
            fda = repo.get_fuera_alcance(db_session, torre_id=t.id)
            partes = [f"Torre: {t.nombre}"]
            if perfiles:
                partes.append("Perfiles: " + ", ".join(p.rol for p in perfiles[:10]))
            if consideraciones:
                partes.append("Consideraciones: " + ", ".join(c.texto for c in consideraciones[:5]))
            if fda:
                partes.append("Fuera de alcance: " + ", ".join(f.item for f in fda[:5]))
            lines.append(" | ".join(partes))
        return "\n".join(lines).strip()
    except Exception:
        return ''


def _verify_description(rol: str, descripcion: str, contexto: str) -> tuple[bool, str, str]:
    """
    Verifica que la descripcion sea veridica y concreta frente al contexto del proyecto.
    Devuelve (ok, descripcion_corregida, motivo). Si no hay contexto suficiente,
    asume ok=True y conserva la descripcion original.
    """
    if not contexto:
        return True, descripcion, 'Sin contexto de proyecto para verificar; se conserva la descripcion.'
    try:
        conversation = [
            {"role": "system", "content": VERIFY_SYSTEM_PROMPT},
            {"role": "user", "content": (
                "Rol/perfil: " + rol + "\n\n"
                "Descripcion a verificar:\n" + descripcion + "\n\n"
                "Contexto REAL del proyecto:\n" + contexto + "\n\n"
                "Valida la descripcion. Si inventa algo no derivable del rol/contexto, corrigela."
            )},
        ]
        model_reply = create_chat_completion(conversation, max_tokens=300)
        parsed = _find_json_object(model_reply)
        ok = bool(parsed.get('ok', True))
        corregida = str(parsed.get('corregida') or '').strip() or descripcion
        motivo = str(parsed.get('motivo') or '').strip()
        return ok, corregida, motivo
    except Exception as exc:
        return True, descripcion, f'Verificacion no disponible ({exc}); se conserva la descripcion.'


def _generate_catalog_description(entity_name: str, value: str, prompt: str, verify: bool = True, db_session=None, torre: str | None = None) -> str:
    try:
        content = create_chat_completion([
            {"role": "system", "content": "Eres un asistente experto en redactar textos breves, profesionales y claros para propuestas de TI en espanol."},
            {"role": "user", "content": prompt},
        ], max_tokens=220)
        text = (content or '').strip()
        if not text:
            raise RuntimeError('La IA devolvio un contenido vacio')
        if verify:
            contexto = _project_context_for_verification(db_session, torre) if db_session is not None else ''
            _ok, text, _motivo = _verify_description(value, text, contexto)
        return text
    except Exception as exc:
        raise RuntimeError(f"No se pudo generar la descripcion para {entity_name}: {exc}") from exc


def generate_profile_description(perfil: str, torre: str | None = None, db_session=None) -> str:
    prompt = (
        "Genera una descripcion profesional CORTA y CONCISA para el siguiente perfil/rol. "
        "La descripcion debe resumir las responsabilidades principales y el valor que aporta al proyecto "
        "en muy pocas lineas. "
        "No repitas el nombre del perfil porque ya aparece como titulo. "
        "Usa maximo 25 palabras, en un parrafo unico y claro. "
        "Debe sonar natural, profesional y apto para una propuesta comercial. "
        "IMPORTANTE: Se breve, evita detalles muy especificos o extensos."
    )
    if torre:
        prompt += f" Considera que pertenece a la torre '{torre}' y enfocate en tareas clave y valor del perfil."
    else:
        prompt += (
            " Si no tienes contexto especifico del proyecto, "
            "genera una descripcion generica profesional basada en las responsabilidades tipicas del rol. "
            "NUNCA respondas pidiendo mas informacion. Siempre debes devolver la descripcion."
        )
    # Solo verificamos contra contexto real si hay torre definida
    should_verify = bool(torre)
    return _generate_catalog_description('perfil', perfil, prompt, verify=should_verify, db_session=db_session, torre=torre)


def generate_consideration_description(texto: str, torre: str | None = None) -> str:
    prompt = f"Genera una descripción breve y profesional para la consideración '{texto}'."
    if torre:
        prompt += f" Considera que pertenece a la torre '{torre}'."
    return _generate_catalog_description('consideración', texto, prompt)


def generate_entregable_description(item: str, torre: str | None = None) -> str:
    prompt = f"Genera una descripción breve y profesional para el entregable '{item}'."
    if torre:
        prompt += f" Considera que pertenece a la torre '{torre}'."
    return _generate_catalog_description('entregable', item, prompt)


def generate_fuera_alcance_description(item: str, torre: str | None = None) -> str:
    prompt = f"Genera una descripción breve y profesional para el ítem fuera de alcance '{item}'."
    if torre:
        prompt += f" Considera que pertenece a la torre '{torre}'."
    return _generate_catalog_description('fuera de alcance', item, prompt)


def replace_logo_in_pptx(pptx_bytes: bytes, logo_bytes: bytes, logo_mime: str) -> bytes:
    """Reemplaza el logo del cliente (logo Mapfre) en TODAS las diapositivas.

    Estrategia por diapositiva (se conserva el tamaño del logo, ya que solo se
    sobrescribe la imagen referenciada sin tocar las coordenadas xfrm del p:pic):
    1. Buscar la forma 'Rectángulo redondeado' para obtener el área del logo.
    2. Buscar p:pic cuyo centro quede dentro de esa área (ignora fondos).
       → Reemplaza el archivo de imagen que referencia en el ZIP.
    3. Fallback: si no hay p:pic, aplica blipFill a la forma 'Rectángulo redondeado'.
    """
    with zipfile.ZipFile(io.BytesIO(pptx_bytes)) as zin:
        files = {name: zin.read(name) for name in zin.namelist()}

    slide_paths = sorted(
        name for name in files
        if re.match(r'ppt/slides/slide\d+\.xml$', name)
    )
    if not slide_paths:
        raise ValueError('No se encontraron diapositivas (slideN.xml) en el PPTX.')

    for slide_path in slide_paths:
        rels_path = f'ppt/slides/_rels/{posixpath.basename(slide_path)}.rels'
        root      = etree.fromstring(files[slide_path])
        rels_raw  = files.get(rels_path)
        if rels_raw is None:
            continue
        rels_root = etree.fromstring(rels_raw)
        rels = {r.get('Id'): r.get('Target', '')
                for r in rels_root.findall(f'{{{_NS_RELS}}}Relationship')}

        # ── 1. Bounding box de la forma 'Rectángulo redondeado' (banner horizontal)
        #    Solo se considera contenedor de logo si es horizontal (cx >= cy).
        #    Los contenedores de fotos de perfil son verticales y se descartan para
        #    evitar reemplazar las fotos por el logo.
        rect_bounds = None
        for sp in root.iter(f'{{{_NS_P}}}sp'):
            nvSpPr = sp.find(f'{{{_NS_P}}}nvSpPr')
            if nvSpPr is None:
                continue
            cNvPr = nvSpPr.find(f'{{{_NS_P}}}cNvPr')
            if cNvPr is None or not (cNvPr.get('name') or '').startswith(_LOGO_SHAPE_PREFIX):
                continue
            spPr = sp.find(f'{{{_NS_P}}}spPr')
            if spPr is None:
                continue
            xfrm = spPr.find(f'{{{_NS_A}}}xfrm')
            if xfrm is None:
                continue
            off, ext_e = xfrm.find(f'{{{_NS_A}}}off'), xfrm.find(f'{{{_NS_A}}}ext')
            if off is None or ext_e is None:
                continue
            x1 = int(off.get('x', 0))
            y1 = int(off.get('y', 0))
            box_cx = int(ext_e.get('cx', 0))
            box_cy = int(ext_e.get('cy', 0))
            if box_cx < box_cy:
                continue  # contenedor vertical (fotos de perfil), se descarta
            rect_bounds = (x1, y1, x1 + box_cx, y1 + box_cy)
            break

        if rect_bounds is None:
            continue  # esta diapositiva no tiene forma de logo

        rx1, ry1, rx2, ry2 = rect_bounds

        # ── 2. p:pic dentro del área del logo ────────────────────────────────
        logo_pics = []
        for pic in root.iter(f'{{{_NS_P}}}pic'):
            blip = pic.find(f'.//{{{_NS_A}}}blip')
            xfrm = pic.find(f'.//{{{_NS_A}}}xfrm')
            if blip is None or xfrm is None:
                continue
            off, ext_e = xfrm.find(f'{{{_NS_A}}}off'), xfrm.find(f'{{{_NS_A}}}ext')
            if off is None or ext_e is None:
                continue
            x, y = int(off.get('x', 0)), int(off.get('y', 0))
            cx, cy = int(ext_e.get('cx', 0)), int(ext_e.get('cy', 0))
            if x < 0 or y < 0:
                continue  # fondo de pantalla completa
            mid_x, mid_y = x + cx // 2, y + cy // 2
            if rx1 <= mid_x <= rx2 and ry1 <= mid_y <= ry2:
                rid = blip.get(f'{{{_NS_R}}}embed')
                if rid:
                    logo_pics.append(rid)

        if logo_pics:
            # ── 2a. Reemplaza TODOS los pics de logo (conserva el tamaño) ───
            for rid in logo_pics:
                target = rels.get(rid, '')
                if not target:
                    continue
                media_path = posixpath.normpath('ppt/slides/' + target)
                if media_path in files:
                    files[media_path] = logo_bytes
        else:
            # ── 2b. Fallback: blipFill en la forma 'Rectángulo redondeado' ───
            slide_tag = posixpath.basename(slide_path).replace('.xml', '')
            name_key = '' if slide_tag == 'slide1' else f'_{slide_tag}'
            ext = _MIME_TO_EXT.get(logo_mime, 'png')
            media_name = f'logo_custom{name_key}.{ext}'
            media_path = f'ppt/media/{media_name}'
            c = 1
            while media_path in files:
                media_name = f'logo_custom{name_key}_{c}.{ext}'
                media_path = f'ppt/media/{media_name}'
                c += 1
            files[media_path] = logo_bytes

            existing_ids = {r.get('Id') for r in rels_root.findall(f'{{{_NS_RELS}}}Relationship')}
            new_rid = 'rIdLogo'
            c = 1
            while new_rid in existing_ids:
                new_rid = f'rIdLogo{c}'
                c += 1
            new_rel = etree.SubElement(rels_root, f'{{{_NS_RELS}}}Relationship')
            new_rel.set('Id', new_rid)
            new_rel.set('Type', _REL_IMAGE_TYPE)
            new_rel.set('Target', f'../media/{media_name}')
            files[rels_path] = etree.tostring(rels_root, xml_declaration=True, encoding='UTF-8', standalone=True)

            for sp in root.iter(f'{{{_NS_P}}}sp'):
                nvSpPr = sp.find(f'{{{_NS_P}}}nvSpPr')
                if nvSpPr is None:
                    continue
                cNvPr = nvSpPr.find(f'{{{_NS_P}}}cNvPr')
                if cNvPr is None or not (cNvPr.get('name') or '').startswith(_LOGO_SHAPE_PREFIX):
                    continue
                spPr = sp.find(f'{{{_NS_P}}}spPr')
                if spPr is None:
                    continue
                for tag in _FILL_TAGS:
                    for el in spPr.findall(f'{{{_NS_A}}}{tag}'):
                        spPr.remove(el)
                blipFill = etree.Element(f'{{{_NS_A}}}blipFill')
                blip_el  = etree.SubElement(blipFill, f'{{{_NS_A}}}blip')
                blip_el.set(f'{{{_NS_R}}}embed', new_rid)
                stretch = etree.SubElement(blipFill, f'{{{_NS_A}}}stretch')
                etree.SubElement(stretch, f'{{{_NS_A}}}fillRect')
                xfrm = spPr.find(f'{{{_NS_A}}}xfrm')
                if xfrm is not None:
                    spPr.insert(list(spPr).index(xfrm) + 1, blipFill)
                else:
                    spPr.append(blipFill)
                break
            files[slide_path] = etree.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True)

    # ── 3. Reconstruir PPTX ──────────────────────────────────────────────────
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zout:
        for name, data in files.items():
            zout.writestr(name, data)
    return buf.getvalue()


# Texto que el generator escribe cuando no hay descripcion en el catalogo
_NO_DESC_MARKERS = (
    'Solicita al asistente IA que complete esta descripción',
    'No encontramos este perfil en la base de datos',
)

# Placeholder que se usa en la BD cuando no hay descripcion
PLACEHOLDER_TEXT = _NO_DESC_MARKERS[0]

_A_NS = 'http://schemas.openxmlformats.org/drawingml/2006/main'
_P_NS = 'http://schemas.openxmlformats.org/presentationml/2006/main'


def _normalize_text(value: str | None) -> str:
    """Normaliza texto para comparaciones: mayúsculas, sin espacios extra."""
    return " ".join(str(value or "").strip().upper().split())


def _clean_inline_text(s: str) -> str:
    if s is None:
        return ''
    s = str(s).replace('\r\n', '\n').replace('\r', '\n')
    s = s.replace('\n', ' ')
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def _esc(t):
    return (t or '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def _build_para_from_template(template_para, text):
    new_para = copy.deepcopy(template_para)
    for r in new_para.findall(f'{{{_A_NS}}}r'):
        new_para.remove(r)
    for br in new_para.findall(f'{{{_A_NS}}}br'):
        new_para.remove(br)
    rPr = None
    orig_r = template_para.find(f'{{{_A_NS}}}r')
    if orig_r is not None:
        orig_rPr = orig_r.find(f'{{{_A_NS}}}rPr')
        if orig_rPr is not None:
            rPr = copy.deepcopy(orig_rPr)
    r_elem = etree.Element(f'{{{_A_NS}}}r')
    if rPr is not None:
        r_elem.append(rPr)
    t_elem = etree.SubElement(r_elem, f'{{{_A_NS}}}t')
    t_elem.text = text
    end_rpr = new_para.find(f'{{{_A_NS}}}endParaRPr')
    if end_rpr is not None:
        end_rpr.addprevious(r_elem)
    else:
        new_para.append(r_elem)
    return new_para


def _normalize_bodyPr(txb):
    bodyPr = txb.find(f'{{{_A_NS}}}bodyPr')
    if bodyPr is None:
        return
    bodyPr.set('wrap', 'square')
    for tag in ('spAutoFit', 'noAutofit', 'normAutofit'):
        el = bodyPr.find(f'{{{_A_NS}}}{tag}')
        if el is not None:
            bodyPr.remove(el)
    etree.SubElement(bodyPr, f'{{{_A_NS}}}normAutofit')


def _update_desc_height(sp, desc_text):
    spPr = sp.find(f'{{{_P_NS}}}spPr')
    if spPr is None:
        return
    xfrm = spPr.find(f'{{{_A_NS}}}xfrm')
    if xfrm is None:
        return
    ext = xfrm.find(f'{{{_A_NS}}}ext')
    if ext is None:
        return
    chars_per_line = 17
    line_height = 167_640
    padding = 200_000
    text_lines = [l for l in desc_text.split('\n') if l.strip()] or [desc_text]
    total_lines = sum(max(1, -(-len(line) // chars_per_line)) for line in text_lines)
    needed_cy = total_lines * line_height + padding
    current_cy = int(ext.attrib.get('cy', 0))
    ext.attrib['cy'] = str(max(current_cy, needed_cy))


def _apply_descriptions_to_pptx(pptx_bytes: bytes, descriptions: list[dict]) -> bytes:
    """
    Reescribe las descripciones de las tarjetas de perfiles en un PPTX ya generado.
    Empareja cada descripcion con su rol (titulo de la tarjeta) y reemplaza el
    texto de placeholder por la descripcion veridica generada por la IA.

    descriptions: lista de {'rol': str, 'descripcion': str}
    """
    if not descriptions:
        return pptx_bytes

    by_rol = {}
    for d in descriptions:
        rol = str(d.get('rol') or '').strip()
        desc = str(d.get('descripcion') or '').strip()
        if rol and desc and desc not in _NO_DESC_MARKERS:
            by_rol[_normalize_text(rol)] = _clean_inline_text(desc)

    if not by_rol:
        return pptx_bytes

    with zipfile.ZipFile(io.BytesIO(pptx_bytes)) as zin:
        files = {name: zin.read(name) for name in zin.namelist()}

    for path, content in list(files.items()):
        if not re.match(r'ppt/slides/slide\d+\.xml$', path):
            continue
        try:
            root = etree.fromstring(content)
        except etree.XMLSyntaxError:
            continue

        modified = False
        for grp in root.iter(f'{{{_P_NS}}}grpSp'):
            inner_name_map = {}
            for sp in grp.iter(f'{{{_P_NS}}}sp'):
                nvpr = sp.find(f'.//{{{_P_NS}}}cNvPr')
                if nvpr is None:
                    continue
                nm = nvpr.attrib.get('name', '')
                inner_name_map.setdefault(nm, []).append(sp)

            for role_name, _desc_name in (
                ('CuadroTexto 10', 'CuadroTexto 22'),
                ('CuadroTexto 30', 'CuadroTexto 28'),
                ('CuadroTexto 47', 'CuadroTexto 34'),
                ('CuadroTexto 53', 'CuadroTexto 51'),
            ):
                role_sps = inner_name_map.get(role_name)
                if not role_sps:
                    continue
                rol_text = ''.join(
                    t.text or '' for t in role_sps[0].iter(f'{{{_A_NS}}}t')
                ).strip()
                rol_norm = _normalize_text(rol_text)
                desc_sps = inner_name_map.get(_desc_name)
                if not desc_sps:
                    continue
                desc_text = ''.join(
                    t.text or '' for t in desc_sps[0].iter(f'{{{_A_NS}}}t')
                ).strip()
                if rol_norm in by_rol and (
                    not desc_text or any(m in desc_text for m in _NO_DESC_MARKERS)
                ):
                    new_desc = by_rol[rol_norm]
                    txb = desc_sps[0].find(f'{{{_P_NS}}}txBody')
                    if txb is None:
                        continue
                    paras = txb.findall(f'{{{_A_NS}}}p')
                    template_para = paras[0] if paras else None
                    for p in paras:
                        txb.remove(p)
                    lines = [l for l in new_desc.split('\n') if l.strip()] or [new_desc]
                    for line in lines:
                        if template_para is not None:
                            txb.append(_build_para_from_template(template_para, line))
                        else:
                            p_xml = (
                                f'<a:p xmlns:a="{_A_NS}">'
                                f'<a:r><a:t>{_esc(line)}</a:t></a:r></a:p>'
                            )
                            txb.append(etree.fromstring(p_xml))
                    _update_desc_height(desc_sps[0], new_desc)
                    _normalize_bodyPr(txb)
                    modified = True
                break

        if modified:
            files[path] = etree.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zout:
        for name, data in files.items():
            zout.writestr(name, data)
    return buf.getvalue()


def completar_descripciones_y_pptx(
    pptx_bytes: bytes,
    db_session=None,
) -> tuple[str, bytes]:
    """
    Flujo del boton 'Completar descripciones con IA':
    1. Busca perfiles pendientes en la BD (placeholder).
    2. Genera descripcion veridica con autoverificacion y la persiste.
    3. Reaplica las descripciones al PPTX ya generado.
    Devuelve (mensaje_para_chat, pptx_actualizado_bytes).
    """
    from infrastructure.repositories import catalogo_repository as repo

    if db_session is None:
        raise RuntimeError('Se requiere sesion de BD para completar descripciones.')

    pendientes = []
    for p in repo.get_perfiles(db_session):
        if p.descripcion and PLACEHOLDER_TEXT in p.descripcion:
            torre_obj = repo.get_torre_by_id(db_session, p.torre_id)
            torre_nombre = torre_obj.nombre if torre_obj else ''
            pendientes.append({'nombre': p.rol, 'torre': torre_nombre, 'id': p.id})

    if not pendientes:
        return "Todos los perfiles ya tienen descripcion verificada. No hay nada que completar.", pptx_bytes

    completados = []
    errores = []
    descriptions_for_pptx = []
    for idx, item in enumerate(pendientes):
        if idx > 0:
            time.sleep(2)
        try:
            desc = generate_profile_description(item['nombre'], item['torre'] or None, db_session=db_session)
            if desc and desc.strip() != PLACEHOLDER_TEXT:
                repo.update_perfil(db_session, item['id'], item['nombre'], desc)
                completados.append(item['nombre'])
                descriptions_for_pptx.append({'rol': item['nombre'], 'descripcion': desc})
            else:
                errores.append(item['nombre'])
        except Exception as e:
            errores.append(f"{item['nombre']} ({e})")

    if not completados:
        return "No se pudo completar ninguna descripcion. " + (', '.join(errores) if errores else ''), pptx_bytes

    updated_pptx = _apply_descriptions_to_pptx(pptx_bytes, descriptions_for_pptx)

    mensaje = (
        f"**Complete {len(completados)} descripcion(es) verificadas y las guarde en la base de datos.**\n\n"
        f"Perfiles completados: {', '.join(completados)}\n\n"
        "**El documento ya fue actualizado con las descripciones.** "
        "Descarga la propuesta para ver los cambios reflejados."
    )
    if errores:
        mensaje += f"\n\nNo se pudieron completar ({len(errores)}): " + ', '.join(errores)
    return mensaje, updated_pptx


def sugerir_descripciones_pendientes(
    pptx_bytes: bytes,
    db_session=None,
) -> dict:
    """
    Solo SUGIERE descripciones para perfiles pendientes (NO guarda en BD, NO aplica a PPTX).
    Devuelve las sugerencias para que el usuario las revise y apruebe.
    """
    from infrastructure.repositories import catalogo_repository as repo

    if db_session is None:
        raise RuntimeError('Se requiere sesion de BD.')

    pendientes = []
    for p in repo.get_perfiles(db_session):
        if p.descripcion and PLACEHOLDER_TEXT in p.descripcion:
            torre_obj = repo.get_torre_by_id(db_session, p.torre_id)
            torre_nombre = torre_obj.nombre if torre_obj else ''
            pendientes.append({'nombre': p.rol, 'torre': torre_nombre, 'id': p.id})

    if not pendientes:
        return {
            'sugerencias': [],
            'reply': 'Todos los perfiles ya tienen descripcion verificada. No hay nada que completar.',
        }

    sugerencias = []
    errores = []
    for idx, item in enumerate(pendientes):
        if idx > 0:
            time.sleep(20)  # Rate limit de Groq (~20s entre requests)
        try:
            desc = generate_profile_description(item['nombre'], item['torre'] or None, db_session=db_session)
            if desc and desc.strip() != PLACEHOLDER_TEXT and 'describe' not in desc.lower()[:20]:
                sugerencias.append({
                    'nombre': item['nombre'],
                    'torre': item['torre'],
                    'descripcion_sugerida': desc,
                    'id': item['id'],
                })
            else:
                errores.append(item['nombre'])
        except Exception as e:
            errores.append(f"{item['nombre']} ({e})")

    if not sugerencias:
        msg = 'No se pudo generar ninguna sugerencia.'
        if errores:
            msg += ' Error(es): ' + ', '.join(errores)
        return {'sugerencias': [], 'reply': msg}

    reply_parts = [
        f'**Sugerencia de descripciones para {len(sugerencias)} perfil(es):**\n'
    ]
    for s in sugerencias:
        torre_info = f" (Torre: {s['torre']})" if s.get('torre') else ''
        reply_parts.append(
            f"\n📌 **{s['nombre']}**{torre_info}:\n"
            f"_{s['descripcion_sugerida']}_\n"
        )
    reply_parts.append(
        '\n---\n'
        'Responde con **"Aprobar"** para aplicar todas las sugerencias al documento, '
        'o dime si quieres ajustar alguna descripción.'
    )
    if errores:
        reply_parts.append(f'\n⚠️ No se pudieron generar ({len(errores)}): ' + ', '.join(errores))

    return {
        'sugerencias': sugerencias,
        'reply': '\n'.join(reply_parts),
    }


def aplicar_descripciones_aprobadas(
    pptx_bytes: bytes,
    descripciones: list[dict],
    db_session=None,
) -> tuple[str, bytes]:
    """
    Aplica las descripciones aprobadas por el usuario:
    - Guarda en BD
    - Aplica al PPTX
    """
    from infrastructure.repositories import catalogo_repository as repo

    if db_session is None:
        raise RuntimeError('Se requiere sesion de BD.')

    completados = []
    errores = []
    descriptions_for_pptx = []

    for item in descripciones:
        nombre = str(item.get('nombre') or '').strip()
        desc = str(item.get('descripcion') or item.get('descripcion_sugerida') or '').strip()
        item_id = item.get('id')

        if not nombre or not desc:
            errores.append(nombre or 'sin nombre')
            continue

        try:
            # Guardar en BD
            if item_id:
                repo.update_perfil(db_session, item_id, nombre, desc)
            else:
                # Buscar por nombre si no hay id
                for p in repo.get_perfiles(db_session):
                    if _normalize_text(p.rol) == _normalize_text(nombre):
                        repo.update_perfil(db_session, p.id, p.rol, desc)
                        break
            completados.append(nombre)
            descriptions_for_pptx.append({'rol': nombre, 'descripcion': desc})
        except Exception as e:
            errores.append(f"{nombre} ({e})")

    if not completados:
        msg = "No se pudo aplicar ninguna descripcion."
        if errores:
            msg += " Detalle: " + "; ".join(errores)
        print(f"[AI] Error aplicar_descripciones_aprobadas: {msg}")
        return msg, pptx_bytes

    updated_pptx = _apply_descriptions_to_pptx(pptx_bytes, descriptions_for_pptx)

    mensaje = (
        f"**✅ {len(completados)} descripcion(es) aprobadas y aplicadas.**\n\n"
        f"Perfiles actualizados: {', '.join(completados)}\n\n"
        "**El documento fue actualizado.** Descarga la propuesta para ver los cambios."
    )
    if errores:
        mensaje += f"\n\n⚠️ Error(es): {', '.join(errores)}"
    return mensaje, updated_pptx


def _find_json_object(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find('{')
        end = text.rfind('}')
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                pass
        raise


def _extract_pptx_text(pptx_bytes: bytes) -> str:
    """Extrae texto párrafo por párrafo para que la IA pueda identificar nombres de perfil individuales."""
    slides = []
    with zipfile.ZipFile(io.BytesIO(pptx_bytes)) as z:
        slide_paths = sorted(
            [path for path in z.namelist() if re.match(r'ppt/slides/slide\d+\.xml$', path)],
            key=lambda path: int(re.search(r'\d+', path).group()),
        )
        for idx, path in enumerate(slide_paths, start=1):
            raw_xml = z.read(path)
            root = etree.fromstring(raw_xml)
            paragraphs = []
            for p in root.xpath('.//a:p', namespaces=PPTX_NS):
                runs = [t.text or '' for t in p.xpath('.//a:t', namespaces=PPTX_NS)]
                para = ''.join(runs).strip()
                if para:
                    paragraphs.append(para)
            if paragraphs:
                slides.append(f"Slide {idx}:\n" + '\n'.join(paragraphs))
    return '\n\n'.join(slides)


# Tecnologías que siempre necesitan el prefijo "Desarrollador" (comparación en minúsculas)
_TECH_PROFILES = frozenset({
    'java', 'java ee', 'java se', 'java spring', 'java spring boot',
    '.net', '.net core', '.net framework', 'net', 'net core', 'net framework',
    'c#', 'c# .net',
    'react', 'reactjs', 'react.js', 'react native',
    'angular', 'angularjs',
    'vue', 'vuejs', 'vue.js',
    'node', 'nodejs', 'node.js',
    'python',
    'go', 'golang',
    'php',
    'ios', 'ios swift',
    'android',
    'spring', 'spring boot',
    'kotlin',
    'typescript', 'ts',
    'javascript', 'js',
    'salesforce',
    'ruby', 'ruby on rails', 'rails',
    'rust', 'scala', 'flutter', 'swift', 'django', 'laravel',
    'mysql', 'sql', 'postgresql', 'oracle sql',
    'cobol', 'abap', 'sap abap',
    'power bi', 'powerbi',
    'full stack', 'fullstack', 'backend', 'frontend',
    'data engineer', 'ml engineer', 'devops engineer',
})

# Palabras clave que indican que el texto es de acción (el usuario quiere corregir perfiles)
_CORRECTION_TRIGGERS = frozenset({
    'corrige', 'corrije', 'arregla', 'completa', 'modifica', 'revisa',
    'añade', 'agrega', 'pon', 'coloca', 'falta', 'incompleto',
})


def _is_correction_request(messages: list[dict]) -> bool:
    """Detecta si el último mensaje del usuario pide corregir/completar perfiles."""
    last = messages[-1].get('content', '').lower() if messages else ''
    has_action = any(w in last for w in _CORRECTION_TRIGGERS)
    has_scope  = any(w in last for w in ('perfil', 'perfiles', 'desarrollador', 'rol', 'roles', 'nombre'))
    return has_action and has_scope


def _build_developer_prefix_replacements(extracted_text: str) -> list[dict]:
    """Genera reemplazos exactos para perfiles que son tecnologías sin prefijo 'Desarrollador'."""
    seen = set()
    replacements = []
    for line in extracted_text.splitlines():
        name = line.strip()
        if not name or len(name) > 60:
            continue
        name_lower = name.lower()
        if name_lower in seen:
            continue
        seen.add(name_lower)
        if name_lower.startswith('desarrollador'):
            continue
        if name_lower in _TECH_PROFILES:
            replacements.append({'from': name, 'to': f'Desarrollador {name}', 'exact': True})
    return replacements


def _apply_replacements_to_pptx(pptx_bytes: bytes, replacements: list[dict[str, str]]) -> bytes:
    """Aplica reemplazos de texto usando lxml para modificar SOLO nodos <a:t>,
    evitando corromper atributos, IDs de relaciones u otras partes del XML."""
    if not replacements:
        return pptx_bytes

    with zipfile.ZipFile(io.BytesIO(pptx_bytes)) as zin:
        files = {name: zin.read(name) for name in zin.namelist()}

    for path, content in list(files.items()):
        if not re.match(r'ppt/slides/slide\d+\.xml$', path):
            continue
        try:
            root = etree.fromstring(content)
        except etree.XMLSyntaxError:
            continue

        modified = False
        # Trabajar a nivel de párrafo para manejar texto dividido en múltiples runs
        for p_elem in root.xpath('.//a:p', namespaces=PPTX_NS):
            t_elems = p_elem.xpath('.//a:t', namespaces=PPTX_NS)
            if not t_elems:
                continue
            combined = ''.join(t.text or '' for t in t_elems)
            if not combined.strip():
                continue
            updated = combined
            for r in replacements:
                frm   = r.get('from', '')
                to    = r.get('to', '')
                exact = r.get('exact', False)
                if not (frm and to and isinstance(frm, str) and isinstance(to, str)):
                    continue
                if exact:
                    # Solo reemplaza si el párrafo completo coincide (evita tocar descripciones)
                    if combined.strip() == frm:
                        updated = to
                else:
                    if frm in updated:
                        updated = updated.replace(frm, to)
            if updated != combined:
                # Poner el texto completo en el primer run y vaciar los demás
                t_elems[0].text = updated
                for t in t_elems[1:]:
                    t.text = ''
                modified = True

        if modified:
            files[path] = etree.tostring(
                root,
                xml_declaration=True,
                encoding='UTF-8',
                standalone=True,
            )

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zout:
        for name, data in files.items():
            zout.writestr(name, data)
    return buf.getvalue()


def chat(messages: list[dict[str, str]]) -> str:
    """Chat con contexto de propuestas comerciales."""
    conversation = [{"role": "system", "content": SYSTEM_PROMPT}]
    conversation.extend(messages)
    return create_chat_completion(conversation)


def review_and_modify_proposal(messages: list[dict[str, str]], content_b64: str, instruction: str) -> tuple[str, str]:
    """Revisa el archivo PPTX y devuelve un PPTX modificado usando instrucciones del usuario."""
    pptx_bytes = base64.b64decode(content_b64)
    extracted_text = _extract_pptx_text(pptx_bytes)

    # Limitar el texto para no superar el contexto del modelo (~4000 chars)
    text_for_ai = extracted_text[:4000] if len(extracted_text) > 4000 else extracted_text

    conversation = [
        {"role": "system", "content": EDIT_SYSTEM_PROMPT},
        {"role": "user", "content": (
            "A continuación tienes el texto extraído del PPTX. "
            "Usa la instrucción del usuario para encontrar y corregir errores en roles, nomenclatura y redacción. "
            "Devuelve ÚNICAMENTE un objeto JSON válido con la estructura {\"replacements\": [...]}. "
            "No añadas texto antes del JSON. Sé conciso: máximo 30 reemplazos."
            "\n\nInstrucción:\n" + instruction + "\n\nTexto extraído:\n" + text_for_ai
        )},
    ]

    model_reply = create_chat_completion(conversation, max_tokens=4096)
    replacements = []
    try:
        parsed = _find_json_object(model_reply)
        raw = parsed.get('replacements', []) if isinstance(parsed, dict) else []
        for r in raw:
            frm = r.get('from', '')
            to = r.get('to', '')
            if not frm or not to:
                continue
            if frm not in extracted_text:
                continue
            if len(to) > len(frm) * 3:
                continue
            replacements.append(r)
    except Exception as exc:
        raise RuntimeError(f"No se pudo interpretar la respuesta de IA como JSON: {exc}")

    modified_bytes = _apply_replacements_to_pptx(pptx_bytes, replacements)
    modified_b64 = base64.b64encode(modified_bytes).decode()
    return model_reply, modified_b64


def _build_excel_context(excel_data: dict) -> str:
    if not isinstance(excel_data, dict):
        return ''

    lines = []
    if excel_data.get('cliente'):
        lines.append(f"Cliente: {excel_data.get('cliente')}")
    if excel_data.get('proyecto'):
        lines.append(f"Proyecto: {excel_data.get('proyecto')}")
    if excel_data.get('filename'):
        lines.append(f"Archivo de estimación: {excel_data.get('filename')}")

    torres = excel_data.get('torres') or []
    if torres:
        total_horas = sum((t.get('horas') or 0) for t in torres)
        lines.append(f"Torres: {len(torres)} torres, {total_horas} horas totales.")
        for torre in torres[:5]:
            nombre = torre.get('nombre', '').strip()
            horas = torre.get('horas', 0)
            personas = torre.get('personas', 0)
            if nombre:
                lines.append(f"- {nombre}: {horas} hrs, {personas} personas")

    perfiles = excel_data.get('perfiles') or []
    if perfiles:
        lines.append(f"Perfiles: {len(perfiles)} roles detectados.")
        for perfil in perfiles[:5]:
            nombre = perfil.get('perfil', '').strip() or perfil.get('rol', '').strip()
            torre = perfil.get('torre', '').strip()
            if nombre:
                lines.append(f"- {nombre} {f'({torre})' if torre else ''}".strip())

    if excel_data.get('entregables'):
        entregables = excel_data.get('entregables')[:5]
        lines.append(f"Entregables: {len(entregables)} grupos.")
        for item in entregables:
            if isinstance(item, dict) and item.get('torre'):
                lines.append(f"- {item.get('torre')}: {', '.join((item.get('items') or [])[:4])}")

    if excel_data.get('consideraciones'):
        lines.append(f"Consideraciones: {', '.join((excel_data.get('consideraciones') or [])[:5])}")
    if excel_data.get('fda'):
        lines.append(f"FDA: {', '.join((excel_data.get('fda') or [])[:5])}")

    return '\n'.join(lines).strip()


_COMPLETE_TRIGGERS = frozenset({
    'completa', 'completar', 'describe', 'descripcion', 'descripciones',
    'sin descripcion', 'rellena', 'genera descripcion', 'falta descripcion',
})


def completar_descripciones_catalogo(
    entity_type: str,
    items: list[dict],
    db_session = None,
) -> list[dict]:
    """
    Genera descripciones IA para items del catalogo que tengan placeholder.

    Args:
        entity_type: 'perfil', 'consideracion', 'entregable', 'fda'
        items: Lista de dicts con al menos 'nombre' y opcionalmente 'torre'
        db_session: Sesion de BD opcional para persistir las descripciones

    Returns:
        Lista de dicts con {'nombre': ..., 'torre': ..., 'descripcion': ...}
    """
    from infrastructure.repositories import catalogo_repository as repo
    from sqlalchemy.orm import Session as SASession

    results = []

    for item in items:
        nombre = str(item.get('nombre', '') or '').strip()
        torre_nombre = str(item.get('torre', '') or '').strip() or None

        if not nombre:
            continue

        try:
            if entity_type == 'perfil':
                descripcion = generate_profile_description(nombre, torre_nombre, db_session=db_session)
            elif entity_type == 'consideracion':
                descripcion = generate_consideration_description(nombre, torre_nombre)
            elif entity_type == 'entregable':
                descripcion = generate_entregable_description(nombre, torre_nombre)
            elif entity_type == 'fda':
                descripcion = generate_fuera_alcance_description(nombre, torre_nombre)
            else:
                continue
        except Exception as exc:
            print(f"[AI] No se pudo generar descripcion para '{nombre}': {exc}")
            continue

        if not descripcion or descripcion.strip() == PLACEHOLDER_TEXT:
            continue

        # Persistir en BD si hay sesion
        if db_session is not None and isinstance(db_session, SASession):
            try:
                if entity_type == 'perfil':
                    torre_obj = None
                    if torre_nombre:
                        torre_obj = repo.get_torre_by_norm(db_session, torre_nombre)
                    if torre_obj:
                        existing = repo.get_perfiles(db_session, torre_id=torre_obj.id)
                    else:
                        existing = repo.get_perfiles(db_session)
                    for p in existing:
                        if _normalize_text(p.rol) == _normalize_text(nombre):
                            repo.update_perfil(db_session, p.id, p.rol, descripcion)
                            break
                elif entity_type == 'consideracion':
                    existing = repo.get_consideraciones(db_session)
                    for c in existing:
                        if _normalize_text(c.texto) == _normalize_text(nombre):
                            repo.update_consideracion(db_session, c.id, c.texto, c.orden)
                            break
                elif entity_type == 'entregable':
                    existing = repo.get_entregables(db_session)
                    for e in existing:
                        if _normalize_text(e.item) == _normalize_text(nombre):
                            repo.update_entregable(db_session, e.id, e.item, e.orden)
                            break
                elif entity_type == 'fda':
                    existing = repo.get_fuera_alcance(db_session)
                    for f in existing:
                        if _normalize_text(f.item) == _normalize_text(nombre):
                            repo.update_fuera_alcance(db_session, f.id, f.item, f.orden)
                            break
            except Exception as exc:
                print(f"[AI] No se pudo persistir descripcion para '{nombre}': {exc}")

        results.append({
            'nombre': nombre,
            'torre': torre_nombre,
            'descripcion': descripcion,
        })

    return results


def _is_complete_description_request(messages: list[dict]) -> bool:
    last = messages[-1].get('content', '').lower() if messages else ''
    has_action = any(w in last for w in _COMPLETE_TRIGGERS)
    has_scope  = any(w in last for w in ('perfil', 'perfiles', 'descripcion', 'descripciones', 'catalogo', 'catalogo'))
    return has_action and has_scope


def chat_with_proposal(messages: list[dict], pptx_bytes: bytes | None, db_session=None) -> tuple[str, bytes | None]:
    from sqlalchemy.orm import Session as SASession
    from infrastructure.repositories import catalogo_repository as repo

    # Si no se pasa sesion, la obtiene internamente para verificar/completar con BD
    own_db = False
    if db_session is None:
        try:
            from core.dependencies import get_db
            db_session = next(get_db())
            own_db = True
        except Exception:
            db_session = None

    try:
        extracted_text = _extract_pptx_text(pptx_bytes) if pptx_bytes else ''

        # Si el usuario pide corregir perfiles (agregar prefijo 'Desarrollador')
        if pptx_bytes and _is_correction_request(messages):
            replacements = _build_developer_prefix_replacements(extracted_text)
            modified_bytes = _apply_replacements_to_pptx(pptx_bytes, replacements) if replacements else pptx_bytes
            if replacements:
                nombres = ', '.join(r['to'] for r in replacements)
                reply = (
                    f"Corregí {len(replacements)} perfil(es): {nombres}. "
                    "Les agregué el prefijo 'Desarrollador'. "
                    "Descarga la propuesta para ver los cambios."
                )
            else:
                reply = (
                    "Revisé la propuesta. Todos los perfiles ya tienen el prefijo 'Desarrollador' "
                    "o son roles que no lo necesitan (Arquitecto, Scrum Master, Analista, etc.)."
                )
            return reply, (modified_bytes if modified_bytes != pptx_bytes else None)

        # Si el usuario pide completar descripciones (en lenguaje natural o boton)
        if pptx_bytes and db_session is not None and isinstance(db_session, SASession) and _is_complete_description_request(messages):
            if repo.get_perfiles(db_session):
                reply, updated_bytes = completar_descripciones_y_pptx(pptx_bytes, db_session=db_session)
                return reply, (updated_bytes if updated_bytes != pptx_bytes else None)
            return "Todos los perfiles ya tienen descripcion verificada. No hay nada que completar.", None

        # Camino conversacional
        text_for_ai = extracted_text[:2000] if len(extracted_text) > 2000 else extracted_text
        conversation = [{'role': 'system', 'content': CONVERSATIONAL_SYSTEM_PROMPT}]
        if text_for_ai:
            conversation.append({'role': 'user', 'content': f'[PROPUESTA CARGADA]\n{text_for_ai}'})
            conversation.append({'role': 'assistant', 'content': 'Propuesta cargada. En que te puedo ayudar?'})
        conversation.extend(messages)

        model_reply = create_chat_completion(conversation, max_tokens=600)
        return model_reply, None
    finally:
        if own_db and db_session is not None:
            db_session.close()


def generate_as_is_to_be(excel_data: dict, as_is_description: str) -> tuple[str, str]:
    if not as_is_description or not str(as_is_description).strip():
        raise ValueError('Descripción de AS-IS requerida.')

    context = _build_excel_context(excel_data)
    prompt_lines = [
        'Descripción del estado actual proporcionada por el usuario:',
        str(as_is_description).strip(),
    ]
    if context:
        prompt_lines.extend(['', 'Contexto del proyecto extraído del Excel:', context])
    prompt_lines.extend([
        '', 'Instrucciones:',
        '- Redacta AS-IS como una descripción profesional y concisa del estado actual del cliente antes de la solución.',
        '- Genera TO-BE como el estado futuro aspiracional después de integrar la solución, basado en el contexto del proyecto.',
        '- No uses la descripción del usuario para formar el TO-BE, usa sólo el contexto.',
        '- Responde únicamente con JSON válido: {"as_is": "...", "to_be": "..."}.',
    ])

    conversation = [
        {'role': 'system', 'content': AS_IS_TO_BE_SYSTEM_PROMPT},
        {'role': 'user', 'content': '\n'.join(prompt_lines)},
    ]

    model_reply = create_chat_completion(conversation, max_tokens=512)
    parsed = _find_json_object(model_reply)
    as_is = str(parsed.get('as_is', '') or '').strip()
    to_be = str(parsed.get('to_be', '') or '').strip()
    if not as_is or not to_be:
        raise RuntimeError('La IA no devolvió AS-IS y TO-BE válidos.')

    return as_is, to_be


ROADMAP_SYSTEM_PROMPT = (
    "Eres un asistente experto en generar roadmaps de servicios y soluciones de TI. "
    "Tu tarea es sintetizar un roadmap de 4 fases a partir de la estimación y el contexto del proyecto. "
    "Respóndeme SOLO con JSON válido y sin texto adicional fuera del objeto JSON."
)


def _build_roadmap_context(excel_data: dict) -> str:
    lines = []
    if not isinstance(excel_data, dict):
        return ''

    proyecto = excel_data.get('proyecto') or excel_data.get('nombre_proyecto') or ''
    if proyecto:
        lines.append(f'Proyecto: {proyecto}')

    cliente = excel_data.get('cliente') or excel_data.get('organizacion') or ''
    if cliente:
        lines.append(f'Cliente: {cliente}')

    torres = excel_data.get('torres') or []
    if not torres:
        torres = excel_data.get('actividades') or []
    if torres:
        lines.append(f'Torres o áreas: {len(torres)}')
        for torre in torres[:4]:
            nombre = torre.get('nombre', '').strip() or torre.get('torre', '').strip() or torre.get('actividad', '').strip()
            if nombre:
                horas = torre.get('horas', 0)
                personas = torre.get('personas', 0)
                lines.append(f'- {nombre}: {horas} hrs, {personas} personas')

    perfiles = excel_data.get('perfiles') or []
    if perfiles:
        lines.append(f'Perfiles: {len(perfiles)} roles.')
        for perfil in perfiles[:4]:
            nombre = perfil.get('perfil', '').strip() or perfil.get('rol', '').strip()
            torre = perfil.get('torre', '').strip()
            if nombre:
                lines.append(f'- {nombre} {f"({torre})" if torre else ""}'.strip())

    entregables = excel_data.get('entregables') or []
    if entregables:
        lines.append(f'Entregables: {len(entregables)} grupos.')
        for item in entregables[:4]:
            if isinstance(item, dict) and item.get('torre'):
                values = ', '.join((item.get('items') or [])[:4])
                lines.append(f'- {item.get("torre")}: {values}')

    if excel_data.get('consideraciones'):
        lines.append(f'Consideraciones: {", ".join((excel_data.get("consideraciones") or [])[:4])}')
    if excel_data.get('fda'):
        lines.append(f'FDA: {", ".join((excel_data.get("fda") or [])[:4])}')

    return '\n'.join(lines).strip()


def _clean_roadmap_phase(phase: dict) -> dict:
    return {
        'title': str(phase.get('title', '') or '').strip(),
        'highlight': str(phase.get('highlight', '') or '').strip(),
        'description': str(phase.get('description', '') or '').strip(),
    }


def fallback_roadmap_phases(excel_data: dict) -> list[dict]:
    context = _build_roadmap_context(excel_data)
    if not context:
        raise RuntimeError('No hay contexto suficiente para generar el roadmap de fallback.')

    proyecto = excel_data.get('proyecto') or excel_data.get('nombre_proyecto') or 'el proyecto'
    return [
        {
            'title': 'Análisis',
            'highlight': f'Evaluar la situación actual de {proyecto}.',
            'description': 'Analizar las torres, roles y entregables para definir prioridades y riesgos.',
        },
        {
            'title': 'Diseño',
            'highlight': 'Definir la solución y el alcance de implementación.',
            'description': 'Estructurar la propuesta técnica y los entregables clave con base en el contexto extraído.',
        },
        {
            'title': 'Ejecución',
            'highlight': 'Construir e integrar la solución planificada.',
            'description': 'Implementar las torres y coordinar los equipos para entregar valor en cada fase.',
        },
        {
            'title': 'Transición',
            'highlight': 'Poner en operación y validar el resultado.',
            'description': 'Entregar el proyecto, capacitar al cliente y asegurar continuidad operativa.',
        },
    ]


def generate_roadmap_phases(excel_data: dict) -> list[dict]:
    context = _build_roadmap_context(excel_data)
    prompt_lines = [
        'Contexto del proyecto extraído del Excel:',
        context or 'No hay información disponible más allá de la estimación.',
        '',
        'Instrucciones:',
        '- Genera exactamente 4 fases de roadmap basadas en el ciclo de vida de desarrollo de software.',
        '- Ordena las fases en este flujo: análisis, diseño, codificación, pruebas/despliegue/mantenimiento.',
        '- Cada fase debe contener un título corto, un texto destacado en negrita y una descripción breve.',
        '- El título debe ser conciso (1-3 palabras).',
        '- El texto destacado debe resumir la acción clave en una frase breve.',
        '- La descripción debe ser clara y apropiada para un roadmap ejecutivo.',
        '- No agregues explicaciones adicionales ni ningún texto fuera del JSON.',
        '- Devuelve solo un objeto JSON con la clave "phases".',
        '',
        'Formato esperado:',
        '{"phases": [{"title": "...", "highlight": "...", "description": "..."}, ...]}',
    ]

    conversation = [
        {'role': 'system', 'content': ROADMAP_SYSTEM_PROMPT},
        {'role': 'user', 'content': '\n'.join(prompt_lines)},
    ]

    model_reply = create_chat_completion(conversation, max_tokens=512)
    parsed = _find_json_object(model_reply)
    phases = parsed.get('phases')
    if not isinstance(phases, list) or len(phases) != 4:
        raise RuntimeError('La IA no devolvió un roadmap válido de 4 fases.')

    cleaned = [_clean_roadmap_phase(phase) for phase in phases]
    if any(not item['title'] or not item['highlight'] or not item['description'] for item in cleaned):
        raise RuntimeError('La IA devolvió fases de roadmap con campos incompletos.')

    return cleaned
