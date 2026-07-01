import base64
import io
import json
import re
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
                # Poner el texto completo en el primer <a:t> y eliminar los runs extra
                # (no vaciar <a:t> — PowerPoint rechaza nodos <a:t/> vacíos)
                t_elems[0].text = updated
                for t in t_elems[1:]:
                    parent_r = t.getparent()
                    if parent_r is not None:
                        grandparent = parent_r.getparent()
                        if grandparent is not None:
                            grandparent.remove(parent_r)
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


def chat_with_proposal(messages: list[dict], pptx_bytes: bytes | None) -> tuple[str, bytes | None]:
    """Chat conversacional con la propuesta.

    Si el usuario pide corregir perfiles → aplica regla de código (sin IA):
      tecnología sin prefijo → 'Desarrollador {tecnología}'.
    Para cualquier otra pregunta → responde con IA.
    """
    extracted_text = _extract_pptx_text(pptx_bytes) if pptx_bytes else ''

    # ── Camino de corrección de perfiles (código puro, sin IA) ──────────────────
    if pptx_bytes and _is_correction_request(messages):
        replacements = _build_developer_prefix_replacements(extracted_text)
        modified_bytes = _apply_replacements_to_pptx(pptx_bytes, replacements) if replacements else None

        if replacements:
            nombres = ', '.join(r['from'] for r in replacements)
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
        return reply, modified_bytes

    # ── Camino conversacional (IA responde preguntas) ───────────────────────────
    text_for_ai = extracted_text[:2000] if len(extracted_text) > 2000 else extracted_text
    conversation = [{'role': 'system', 'content': CONVERSATIONAL_SYSTEM_PROMPT}]
    if text_for_ai:
        conversation.append({'role': 'user', 'content': f'[PROPUESTA CARGADA]\n{text_for_ai}'})
        conversation.append({'role': 'assistant', 'content': 'Propuesta cargada. ¿En qué te puedo ayudar?'})
    conversation.extend(messages)

    model_reply = create_chat_completion(conversation, max_tokens=600)
    return model_reply, None


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
