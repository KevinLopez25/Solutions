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
    slides = []
    with zipfile.ZipFile(io.BytesIO(pptx_bytes)) as z:
        slide_paths = sorted(
            [path for path in z.namelist() if re.match(r'ppt/slides/slide\d+\.xml$', path)],
            key=lambda path: int(re.search(r'\d+', path).group()),
        )
        for idx, path in enumerate(slide_paths, start=1):
            raw_xml = z.read(path)
            root = etree.fromstring(raw_xml)
            texts = [t.text or '' for t in root.xpath('.//a:t', namespaces=PPTX_NS)]
            if texts:
                slides.append(f"Slide {idx}: {''.join(texts)}")
    return '\n\n'.join(slides)


def _apply_replacements_to_pptx(pptx_bytes: bytes, replacements: list[dict[str, str]]) -> bytes:
    if not replacements:
        return pptx_bytes

    with zipfile.ZipFile(io.BytesIO(pptx_bytes)) as zin:
        files = {name: zin.read(name) for name in zin.namelist()}

    for path, content in list(files.items()):
        if re.match(r'ppt/slides/slide\d+\.xml$', path):
            try:
                text = content.decode('utf-8')
            except UnicodeDecodeError:
                continue
            original_text = text
            for replacement in replacements:
                frm = replacement.get('from')
                to = replacement.get('to')
                if isinstance(frm, str) and isinstance(to, str) and frm and frm in text:
                    text = text.replace(frm, to)
            if text != original_text:
                files[path] = text.encode('utf-8')

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zout:
        for name, content in files.items():
            zout.writestr(name, content)

    return buffer.getvalue()


def chat(messages: list[dict[str, str]]) -> str:
    """Chat con contexto de propuestas comerciales."""
    conversation = [{"role": "system", "content": SYSTEM_PROMPT}]
    conversation.extend(messages)
    return create_chat_completion(conversation)


def review_and_modify_proposal(messages: list[dict[str, str]], content_b64: str, instruction: str) -> tuple[str, str]:
    """Revisa el archivo PPTX y devuelve un PPTX modificado usando instrucciones del usuario."""
    pptx_bytes = base64.b64decode(content_b64)
    extracted_text = _extract_pptx_text(pptx_bytes)

    conversation = [
        {"role": "system", "content": EDIT_SYSTEM_PROMPT},
        {"role": "user", "content": (
            "A continuación tienes el texto extraído del PPTX. "
            "Usa la instrucción del usuario para encontrar y corregir errores en roles, nomenclatura y redacción. "
            "Devuelve ÚNICAMENTE un objeto JSON válido con la estructura {\"replacements\": [...]}. "
            "No añadas texto antes del JSON."
            "\n\nInstrucción:\n" + instruction + "\n\nTexto extraído:\n" + extracted_text
        )},
    ]

    model_reply = create_chat_completion(conversation)
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
