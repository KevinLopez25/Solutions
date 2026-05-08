from pydantic import BaseModel


# ── Módulo 1: Validación de perfiles ─────────────────────────────────────────

class PerfilParaValidar(BaseModel):
    perfil: str
    torre: str = ""
    seniority: str = ""
    personas: int = 1


class ResultadoValidacion(BaseModel):
    perfil_original: str
    nombre_correcto: str
    accion: str          # "corregir" | "dejar_igual" | "preguntar"
    opciones: list[str] = []
    en_bd: bool = False
    descripcion: str = ""


class ValidarPerfilesRequest(BaseModel):
    perfiles: list[PerfilParaValidar]


class ValidarPerfilesResponse(BaseModel):
    resultados: list[ResultadoValidacion]


class ConfirmarPerfilRequest(BaseModel):
    nombre: str
    torre: str


class ConfirmarPerfilResponse(BaseModel):
    descripcion: str


# ── Módulo 2: Chat agente ─────────────────────────────────────────────────────

class MensajeChat(BaseModel):
    role: str    # "user" | "assistant"
    content: str


class ContextoPropuesta(BaseModel):
    cliente: str | None = None
    proyecto: str | None = None
    codigo_oportunidad: str | None = None
    filial: str | None = None          # "corp" | "group" | "cbit"
    kam_nombre: str | None = None
    kam_email: str | None = None
    kam_telefono: str | None = None
    ciudad: str | None = None
    pais: str | None = None
    version: str = "V1.0.0"
    tipo_proyecto: str | None = None
    objetivo: str | None = None
    as_is: str | None = None
    to_be: str | None = None
    torres_seleccionadas: list[str] = []
    horas_por_torre: dict[str, int] = {}
    incluir_qa: bool | None = None
    tiene_excel: bool = False
    perfiles_ambiguos: list[str] = []
    forma_pago: str | None = None
    fases_roadmap: list[str] = []
    herramientas: list[str] = []
    supuestos: list[str] = []


class ChatRequest(BaseModel):
    mensaje: str
    historial: list[MensajeChat] = []
    contexto_propuesta: ContextoPropuesta = ContextoPropuesta()


class ChatResponse(BaseModel):
    respuesta: str
    contexto_actualizado: ContextoPropuesta
    accion: str | None = None          # "generar_ppt"
    quick_options: list[str] = []
    config_propuesta: dict | None = None
