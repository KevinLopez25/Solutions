"""
Módulo IA — Periferia IT
Módulo 1: Validación inteligente de perfiles con llama-3.1-8b-instant
Módulo 2: Agente conversacional con llama-3.3-70b-versatile
"""
import json
import re
from sqlalchemy.orm import Session

from core.groq_client import get_groq_client
from domain.ia.entities import (
    ValidarPerfilesRequest, ValidarPerfilesResponse, ResultadoValidacion,
    ConfirmarPerfilRequest, ConfirmarPerfilResponse,
    ChatRequest, ChatResponse, ContextoPropuesta,
)
from infrastructure.models.catalogo import Perfil, Torre
from infrastructure.repositories.catalogo_repository import (
    get_torre_by_norm, build_catalog_data,
)

# ─── Módulo 1: Validación de perfiles ────────────────────────────────────────

_VALIDAR_SYSTEM = (
    "Eres un clasificador de roles de TI para proyectos en Colombia. "
    "Responde SOLO con JSON válido, sin texto adicional."
)

_VALIDAR_PROMPT = """Clasifica los siguientes perfiles de proyectos de software.
Para cada uno determina si es una tecnología pura, un rol completo o ambiguo.

Perfiles: {nombres}

Responde con este JSON exacto:
{{
  "resultados": [
    {{
      "perfil_original": "nombre exacto",
      "nombre_correcto": "nombre correcto completo",
      "accion": "corregir | dejar_igual | preguntar",
      "opciones": []
    }}
  ]
}}

REGLAS estrictas:
- Tecnología backend pura (Java, Python, .NET, Node.js, Spring, etc.) → accion="corregir", nombre_correcto="Desarrollador Backend {tech}"
- Tecnología frontend (React, Angular, Vue, Next.js, etc.) → accion="corregir", nombre_correcto="Desarrollador Frontend {tech}"
- Tecnología móvil (Flutter, React Native, Swift, Kotlin) → accion="corregir", nombre_correcto="Desarrollador Mobile {tech}"
- Tecnología fullstack o sin contexto claro → accion="corregir", nombre_correcto="Desarrollador Fullstack {tech}"
- Rol completo (Scrum Master, Arquitecto de Software, Analista de Datos, Gerente de Proyecto, Líder Técnico, Ingeniero de Pruebas, etc.) → accion="dejar_igual", nombre_correcto igual al original
- Ambiguo (QA, BA, DevOps, Data, PM, PO, etc.) → accion="preguntar", opciones con 2-3 alternativas concretas
- Si ya tiene prefijo correcto (ej: "Desarrollador Backend") → accion="dejar_igual"
"""

_DESC_PROMPT = """Genera una descripción profesional y concisa (máximo 180 caracteres) para el siguiente perfil de TI en un proyecto de software.
La descripción debe ser en español, orientada a propuestas comerciales, describiendo las responsabilidades principales del rol.

Perfil: {nombre}
Torre/Área: {torre}

Responde SOLO con la descripción, sin comillas ni texto adicional."""


def validar_perfiles(request: ValidarPerfilesRequest, db: Session) -> ValidarPerfilesResponse:
    client = get_groq_client()
    nombres = json.dumps([p.perfil for p in request.perfiles], ensure_ascii=False)

    raw_response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        response_format={"type": "json_object"},
        temperature=0,
        messages=[
            {"role": "system", "content": _VALIDAR_SYSTEM},
            {"role": "user",   "content": _VALIDAR_PROMPT.format(nombres=nombres)},
        ],
    )

    raw = json.loads(raw_response.choices[0].message.content)
    resultados_raw = raw.get("resultados", [])

    catalog = build_catalog_data(db)
    perf_db: dict = catalog.get("perf_db", {})

    resultados = []
    for i, r in enumerate(resultados_raw):
        nombre_correcto = r.get("nombre_correcto", request.perfiles[i].perfil)
        accion = r.get("accion", "dejar_igual")
        opciones = r.get("opciones", [])

        # Buscar en catálogo
        en_bd = False
        desc = ""
        nombre_norm = nombre_correcto.upper()
        for perfs in perf_db.values():
            for p in perfs:
                if p.get("rol", "").upper() == nombre_norm:
                    en_bd = True
                    desc = p.get("desc", "")
                    break
            if en_bd:
                break

        # Si no está en BD y la acción no requiere confirmación, generar descripción y guardar
        if not en_bd and accion != "preguntar":
            torre_str = request.perfiles[i].torre if i < len(request.perfiles) else ""
            desc = _generar_descripcion(client, nombre_correcto, torre_str)
            _insertar_perfil(db, nombre_correcto, torre_str, desc)

        resultados.append(ResultadoValidacion(
            perfil_original=r.get("perfil_original", request.perfiles[i].perfil),
            nombre_correcto=nombre_correcto,
            accion=accion,
            opciones=opciones,
            en_bd=en_bd,
            descripcion=desc,
        ))

    return ValidarPerfilesResponse(resultados=resultados)


def confirmar_perfil(request: ConfirmarPerfilRequest, db: Session) -> ConfirmarPerfilResponse:
    client = get_groq_client()
    desc = _generar_descripcion(client, request.nombre, request.torre)
    _insertar_perfil(db, request.nombre, request.torre, desc)
    return ConfirmarPerfilResponse(descripcion=desc)


def _generar_descripcion(client, nombre: str, torre: str) -> str:
    try:
        resp = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            temperature=0.3,
            max_tokens=100,
            messages=[
                {"role": "user", "content": _DESC_PROMPT.format(nombre=nombre, torre=torre or "Tecnología")},
            ],
        )
        return resp.choices[0].message.content.strip().strip('"')
    except Exception:
        return ""


def _insertar_perfil(db: Session, nombre: str, torre_nombre: str, desc: str) -> None:
    try:
        torre = get_torre_by_norm(db, torre_nombre) if torre_nombre else None
        if not torre:
            return
        obj = Perfil(torre_id=torre.id, rol=nombre, descripcion=desc)
        db.add(obj)
        db.commit()
    except Exception:
        db.rollback()


# ─── Módulo 2: Chat agente ────────────────────────────────────────────────────

_CHAT_SYSTEM = """Eres Peri, el asistente de Periferia IT para crear propuestas comerciales de proyectos de software.
Habla en español colombiano, con tono cálido y profesional. Haz UNA sola pregunta por turno (máximo dos si están muy relacionadas).

## Torres disponibles en Periferia IT (14)
Fullstack | QA | Arquitectura | Datos | RPA | DevOps | Ciberseguridad | IA | SAP | PMO | Mobile | Portales | Integración | Soporte

## Filiales
- CORP → proyectos corporativos grandes  (valor: "corp")
- GROUP → proyectos medianos             (valor: "group")
- CBIT → proyectos tecnológicos especializados (valor: "cbit")

---
## FLUJO DE CONVERSACIÓN

### FASE 1 — Identificación del negocio (SIEMPRE, en este orden exacto)
Recopila uno a la vez:
1. **cliente**: nombre de la empresa cliente (CRÍTICO — aparece en portada, textos legales, consideraciones y garantía)
2. **proyecto**: nombre del proyecto o servicio (título de la portada)
3. **codigo_oportunidad**: código del CRM (ej: f5b96bb4) — si no lo saben, pasar al siguiente
4. **filial**: cuál empresa Periferia emite → CORP / GROUP / CBIT
5. **KAM**: nombre completo, email corporativo y teléfono del ejecutivo asignado
6. **ciudad y país** del cliente
7. **version**: default "V1.0.0", cambia solo si hubo revisiones previas

### FASE 2 — Tipo de proyecto
Pregunta qué tipo de solución necesitan. Según la respuesta sugiere torres:
- App web o plataforma → Fullstack, QA, Arquitectura
- Gobierno/ingeniería de datos → Datos, IA, Arquitectura
- App móvil → Mobile, QA, Fullstack (si hay API)
- Portal o intranet → Portales, Fullstack, QA
- Integración de sistemas → Integración, Arquitectura
- Automatización RPA → RPA, Arquitectura
- IA / ML → IA, Datos, Arquitectura
- DevOps / nube → DevOps, Arquitectura
- Ciberseguridad → Ciberseguridad, Arquitectura
- Staffing (equipo dedicado) → principalmente perfiles, sin roadmap detallado
- Gestión de proyecto → PMO más las torres técnicas que apliquen
Confirma con el usuario las torres y agrega/quita según sus comentarios.

### FASE 3 — Horas y contenido narrativo
Pregunta horas estimadas por torre (o duración del proyecto para calcularlas).
Estima: torre principal ≈ 480-600 hrs en 3 meses; torres de soporte ≈ 120-240 hrs.
Luego recopila (solo lo relevante al tipo de proyecto):
- **objetivo**: qué problema resuelve Periferia (1-2 oraciones claras)
- **as_is**: situación actual del cliente, el problema que tienen hoy
- **to_be**: la solución que entrega Periferia, el estado futuro
- **fases_roadmap**: cuántas fases, nombre y actividades clave de cada una
- Consideraciones especiales: accesos, ambientes, restricciones del cliente
- ¿Hay supuestos o riesgos importantes a documentar?
- ¿Incluye Adopción del Cambio con SeriaMente como aliado? (poco frecuente)

### FASE 4 — Oferta económica
- Si **tiene_excel=true** → NO preguntar perfiles ni horas, ya están cargados del Excel
- Si no hay Excel → preguntar perfiles del equipo, cantidades y horas por torre
- Forma de pago default: "30% firma acta de inicio / 50% entrega de sprints / 20% paso a producción"

### FASE 5 — Confirmación y generación
Muestra un resumen completo de todo lo recopilado.
Pregunta si es correcto o si quieren ajustar algo.
Cuando el usuario confirme → emite el bloque [READY].

---
## REGLAS
- Si el usuario dice "lo de siempre" o "los valores por defecto" → usa valores estándar de Periferia
- **incluir_qa**: true por defecto; solo false si el usuario dice explícitamente que no hay QA
- Si hay **perfiles_ambiguos** en el contexto → preséntaselos como opciones antes de pasar a FASE 3
- Nunca repitas preguntas ya respondidas — revisa el contexto actual antes de preguntar
- Si el usuario responde de forma parcial → acepta lo que dio y sigue con lo que falta
- Los nombres de torres en **torres_seleccionadas** deben ser EXACTAMENTE como aparecen en la lista de 14 torres

---
## METADATOS (invisibles al usuario — el servidor los extrae)
CRÍTICO: tu texto visible NO debe tener JSON ni llaves. Solo texto natural.
Al final de cada respuesta incluye los bloques que apliquen:

[CTX]{"campo1": valor, "campo2": valor}[/CTX]  ← datos nuevos aprendidos este turno
[OPTS]["opción A", "opción B"][/OPTS]            ← respuestas rápidas sugeridas
[READY]{"filial":"...", "cliente":"...", "proyecto":"...", "torres_seleccionadas":[], "horas_por_torre":{}, "incluir_qa":true}[/READY]  ← SOLO al confirmar en FASE 5

Campos válidos para CTX: cliente, proyecto, codigo_oportunidad, filial, kam_nombre, kam_email, kam_telefono, ciudad, pais, version, tipo_proyecto, objetivo, as_is, to_be, torres_seleccionadas, horas_por_torre, incluir_qa, fases_roadmap.
torres_seleccionadas debe usar nombres EXACTOS de las 14 torres.

Contexto actual (NO preguntar lo que ya está aquí):
CONTEXTO_PLACEHOLDER
"""

# Regex tolerante: acepta [/TAG], [//TAG], [TAG/] — el LLM a veces varía el cierre
_TAG_RE = re.compile(
    r'\[(CTX|READY|OPTS)\](.*?)(?:\[/+\1\]|\[\1/+\])',
    re.DOTALL | re.IGNORECASE,
)
# Fallback para bloques sin cierre correcto: busca apertura y captura hasta el siguiente bloque
_TAG_OPEN_RE = re.compile(r'\[(CTX|READY|OPTS)\]', re.IGNORECASE)

# Torres válidas (nombres exactos del catálogo)
_VALID_TOWERS = {
    "Fullstack", "QA", "Arquitectura", "Datos", "RPA", "DevOps",
    "Ciberseguridad", "IA", "SAP", "PMO", "Mobile", "Portales",
    "Integración", "Soporte",
}
# Mapa tecnología/alias → torre válida
_TOWER_ALIAS: dict[str, str] = {
    "java": "Fullstack", "python": "Fullstack", "react": "Fullstack",
    "angular": "Fullstack", "vue": "Fullstack", ".net": "Fullstack",
    "node": "Fullstack", "nodejs": "Fullstack", "spring": "Fullstack",
    "backend": "Fullstack", "frontend": "Fullstack",
    "sql": "Datos", "oracle": "Datos", "etl": "Datos", "bi": "Datos",
    "azure": "DevOps", "aws": "DevOps", "gcp": "DevOps",
    "docker": "DevOps", "kubernetes": "DevOps", "cloud": "DevOps",
    "ml": "IA", "machine learning": "IA", "nlp": "IA", "llm": "IA",
    "rpa": "RPA", "automatización": "RPA", "automatizacion": "RPA",
    "ios": "Mobile", "android": "Mobile", "flutter": "Mobile",
    "react native": "Mobile", "kotlin": "Mobile", "swift": "Mobile",
    "seguridad": "Ciberseguridad", "security": "Ciberseguridad",
    "scrum": "PMO", "agile": "PMO", "pmo": "PMO",
    "sap": "SAP", "integracion": "Integración",
    "testing": "QA", "qa": "QA",
    "soporte": "Soporte", "portal": "Portales",
}


def _normalize_towers(raw: list[str]) -> list[str]:
    """Filtra/mapea nombres de torres a los 14 valores exactos del catálogo."""
    valid_lower = {t.lower(): t for t in _VALID_TOWERS}
    seen, result = set(), []
    for name in raw:
        key = name.strip().lower()
        canonical = valid_lower.get(key) or _TOWER_ALIAS.get(key)
        if canonical and canonical not in seen:
            seen.add(canonical)
            result.append(canonical)
    return result


def _extract_tags(text: str) -> tuple[dict[str, str | None], str]:
    """
    Extrae bloques [TAG]...[/TAG] del texto tolerando variaciones del LLM
    en el tag de cierre ([//TAG], [TAG/], etc.).
    Devuelve (dict con contenido por tag, texto limpio).
    """
    found: dict[str, str | None] = {"CTX": None, "READY": None, "OPTS": None}
    clean = text

    # Primer intento: regex con cierre correcto / tolerante
    for match in _TAG_RE.finditer(text):
        tag = match.group(1).upper()
        if found[tag] is None:
            found[tag] = match.group(2).strip()

    clean = _TAG_RE.sub("", clean)

    # Segundo intento: si quedó una apertura sin cierre detectado, tomar hasta fin de línea
    for tag in ("CTX", "READY", "OPTS"):
        if found[tag] is not None:
            continue
        m = re.search(rf'\[{tag}\](.*?)(?=\n\n|\Z)', clean, re.DOTALL | re.IGNORECASE)
        if m:
            candidate = m.group(1).strip()
            if candidate.startswith('{') or candidate.startswith('['):
                found[tag] = candidate
                clean = re.sub(
                    rf'\[{tag}\].*?(?=\n\n|\Z)', '', clean,
                    flags=re.DOTALL | re.IGNORECASE,
                )

    return found, clean


def _clean_response(raw: str) -> str:
    """Elimina todos los bloques de metadatos y JSON suelto del texto visible."""
    _, clean = _extract_tags(raw)
    # Bloques de código con JSON
    clean = re.sub(r'```[\w]*\n?[\s\S]*?```', '', clean)
    # Líneas que son JSON puro (fallback)
    lines = []
    for line in clean.split('\n'):
        s = line.strip()
        if s.startswith('{') and s.endswith('}'):
            continue
        if s.startswith('[') and s.endswith(']') and ('","' in s or '",' in s):
            continue
        lines.append(line)
    return '\n'.join(lines).strip()


def _clean_history_content(content: str) -> str:
    """Limpia los bloques de metadatos de mensajes anteriores antes de enviar a Groq."""
    clean, _ = _extract_tags(content)
    return _clean_response(content)


def _build_propuesta_config(contexto: ContextoPropuesta, ready_raw: dict) -> dict:
    """
    Construye el payload exacto que espera POST /api/v1/propuesta/generar,
    equivalente al wizard en modo 'sin Excel, catálogo completo + todas las pills ON'.
    """
    filial = (contexto.filial or ready_raw.get("filial", "corp")).lower()
    cliente = contexto.cliente or ready_raw.get("cliente", "")
    proyecto = contexto.proyecto or ready_raw.get("proyecto", "")
    torres_sel = (
        contexto.torres_seleccionadas
        or ready_raw.get("torres_seleccionadas", [])
    )
    horas = contexto.horas_por_torre or ready_raw.get("horas_por_torre", {})
    incluir_qa = (
        contexto.incluir_qa
        if contexto.incluir_qa is not None
        else ready_raw.get("incluir_qa", True)
    )

    # Normalizar torres a los 14 nombres exactos del catálogo
    torres_sel = _normalize_towers(torres_sel)

    torres_data = [
        {"nombre": t, "horas": int(horas.get(t, 120)), "personas": 1}
        for t in torres_sel
    ]

    actividades = [
        {"torre": t, "actividad": t, "horas": int(horas.get(t, 120)), "personas": 1}
        for t in torres_sel
    ]

    return {
        "filial": filial,
        "excel_data": {
            "cliente":         cliente,
            "proyecto":        proyecto,
            "torres":          torres_data,
            "perfiles":        [],
            "consideraciones": [],
            "fda":             [],
            "entregables":     [],
            "filename":        "",
        },
        "torres_seleccionadas": torres_sel,
        # Todas las pills ON → el catálogo de BD completa perfiles, FDA,
        # consideraciones y entregables para cada torre seleccionada
        "opciones": {
            "perfiles":        True,
            "fda":             True,
            "consideraciones": True,
            "entregables":     True,
        },
        "perfiles_manuales": [],
        "incluir_qa":        bool(incluir_qa),
        "actividades":       actividades,
        "roles":             [],
    }


def chat(request: ChatRequest) -> ChatResponse:
    client = get_groq_client()

    # Solo incluir campos con valor real (reduce tokens del contexto)
    contexto_dict = {
        k: v for k, v in request.contexto_propuesta.model_dump().items()
        if v not in (None, [], {}, "")
    }
    system = _CHAT_SYSTEM.replace(
        "CONTEXTO_PLACEHOLDER",
        json.dumps(contexto_dict, ensure_ascii=False),
    )

    # Limitar historial a últimos 12 mensajes + limpiar metadatos acumulados
    historial_reciente = request.historial[-12:]
    messages = [{"role": "system", "content": system}]
    for msg in historial_reciente:
        messages.append({
            "role": msg.role,
            "content": _clean_history_content(msg.content),
        })
    messages.append({"role": "user", "content": request.mensaje})

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        temperature=0.6,
        max_tokens=900,
        messages=messages,
    )

    raw_text = response.choices[0].message.content or ""

    # Extraer metadatos con regex tolerante (acepta [//CTX], [CTX/] etc.)
    tags, _ = _extract_tags(raw_text)

    ctx_data: dict = {}
    ready_data: dict | None = None
    quick_options: list[str] = []

    if tags["CTX"]:
        try:
            ctx_data = json.loads(tags["CTX"])
            if not isinstance(ctx_data, dict):
                ctx_data = {}
        except json.JSONDecodeError:
            pass

    if tags["READY"]:
        try:
            ready_data = json.loads(tags["READY"])
            if not isinstance(ready_data, dict):
                ready_data = None
        except json.JSONDecodeError:
            pass

    if tags["OPTS"]:
        try:
            quick_options = json.loads(tags["OPTS"])
            if not isinstance(quick_options, list):
                quick_options = []
        except json.JSONDecodeError:
            pass

    # Texto limpio — sin metadatos, sin JSON suelto, sin saltos múltiples
    clean = _clean_response(raw_text)
    clean = re.sub(r'\n{3,}', '\n\n', clean).strip()

    # Actualizar contexto con los datos aprendidos
    contexto = request.contexto_propuesta.model_copy(deep=True)
    if ctx_data:
        valid_fields = ContextoPropuesta.model_fields.keys()
        safe_updates = {k: v for k, v in ctx_data.items() if k in valid_fields}
        if safe_updates:
            contexto = contexto.model_copy(update=safe_updates)

    # Construir config completo y correcto para generar_propuesta
    # Solo si hay torres seleccionadas y filial — sin eso el PPT queda vacío
    config_propuesta = None
    if ready_data:
        torres = (
            contexto.torres_seleccionadas
            or ready_data.get("torres_seleccionadas", [])
        )
        filial = (contexto.filial or ready_data.get("filial", "")).strip()
        if torres and filial:
            config_propuesta = _build_propuesta_config(contexto, ready_data)

    return ChatResponse(
        respuesta=clean,
        contexto_actualizado=contexto,
        accion="generar_ppt" if config_propuesta else None,
        quick_options=quick_options,
        config_propuesta=config_propuesta,
    )
