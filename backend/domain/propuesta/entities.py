from pydantic import BaseModel, ConfigDict


class TorreInput(BaseModel):
    model_config = ConfigDict(extra='allow')
    nombre: str
    horas: int = 0
    personas: int = 1


class PerfilInput(BaseModel):
    model_config = ConfigDict(extra='allow')
    perfil: str
    torre: str = ""
    seniority: str = ""
    personas: int = 1
    horas: int = 0


class EntregableGrupo(BaseModel):
    model_config = ConfigDict(extra='allow')
    torre: str
    items: list[str] = []


class AlcanceItem(BaseModel):
    model_config = ConfigDict(extra='allow')
    titulo: str
    descripcion: str = ""


class AlcanceTorre(BaseModel):
    model_config = ConfigDict(extra='allow')
    torre: str
    items: list[AlcanceItem] = []


class OpcionesPills(BaseModel):
    model_config = ConfigDict(extra='allow')
    perfiles: bool = False
    fda: bool = False
    entregables: bool = False
    consideraciones: bool = False
    usar_ia_alcances: bool = False


class ExcelData(BaseModel):
    model_config = ConfigDict(extra='allow')
    torres: list[TorreInput] = []
    cliente: str = ""
    proyecto: str = ""
    perfiles: list[PerfilInput] = []
    consideraciones: list[str] = []
    fda: list[str] = []
    entregables: list[EntregableGrupo] = []
    alcances: list[AlcanceTorre] = []
    filename: str = ""


class PerfilManual(BaseModel):
    model_config = ConfigDict(extra='allow')
    rol: str
    desc: str = ""
    torre: str = ""


class Actividad(BaseModel):
    model_config = ConfigDict(extra='allow')
    torre: str
    actividad: str
    horas: int = 0
    personas: int = 1


class GenerarPropuestaRequest(BaseModel):
    model_config = ConfigDict(extra='allow')
    filial: str                          # "corp" | "group" | "cbit"
    excel_data: ExcelData = ExcelData()
    torres_seleccionadas: list[str] = []
    opciones: OpcionesPills = OpcionesPills()
    perfiles_manuales: list[PerfilManual] = []
    incluir_qa: bool = True
    incluir_as_is_to_be: bool = False
    as_is_description: str = ""
    horas_semanales: float = 42
    cronograma_por_perfiles: bool = False
    actividades: list[Actividad] = []
    roles: list[PerfilInput] = []
    template_name: str | None = None
    template_section: str | None = None
    tarjeta_comercial: str | None = None
    tarjeta_comercial_pais: str | None = None


class GenerarPropuestaResponse(BaseModel):
    filename: str
    content_b64: str                     # base64-encoded PPTX
