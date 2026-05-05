from pydantic import BaseModel


class TorreInput(BaseModel):
    nombre: str
    horas: int = 0


class PerfilInput(BaseModel):
    perfil: str
    torre: str = ""


class EntregableGrupo(BaseModel):
    torre: str
    items: list[str] = []


class OpcionesPills(BaseModel):
    perfiles: bool = False
    fda: bool = False
    entregables: bool = False
    consideraciones: bool = False


class ExcelData(BaseModel):
    torres: list[TorreInput] = []
    cliente: str = ""
    proyecto: str = ""
    perfiles: list[PerfilInput] = []
    consideraciones: list[str] = []
    fda: list[str] = []
    entregables: list[EntregableGrupo] = []


class PerfilManual(BaseModel):
    rol: str
    desc: str = ""
    torre: str = ""


class GenerarPropuestaRequest(BaseModel):
    filial: str                          # "corp" | "group" | "cbit"
    excel_data: ExcelData = ExcelData()
    torres_seleccionadas: list[str] = []
    opciones: OpcionesPills = OpcionesPills()
    perfiles_manuales: list[PerfilManual] = []
    incluir_qa: bool = True


class GenerarPropuestaResponse(BaseModel):
    filename: str
    content_b64: str                     # base64-encoded PPTX
