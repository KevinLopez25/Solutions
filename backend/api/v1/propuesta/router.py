import re
import traceback
import unicodedata
from pathlib import Path
import traceback
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from core.dependencies import get_db
from core.config import settings
from domain.propuesta.entities import GenerarPropuestaRequest, GenerarPropuestaResponse
from domain.propuesta import service

router = APIRouter(prefix="/propuesta", tags=["Propuesta"])

_TARJETAS_DIR = Path(settings.templates_path) / 'tarjetas_comerciales'

# Países donde se organizan las tarjetas comerciales.
# clave = slug de carpeta, valor = (nombre, bandera)
PAISES_TARJETAS = {
    'colombia': {'nombre': 'Colombia', 'bandera': '🇨🇴'},
    'ecuador':  {'nombre': 'Ecuador',  'bandera': '🇪🇨'},
    'mexico':   {'nombre': 'México',   'bandera': '🇲🇽'},
    'panama':   {'nombre': 'Panamá',   'bandera': '🇵🇦'},
    'peru':     {'nombre': 'Perú',     'bandera': '🇵🇪'},
}


def _normalizar_q(value: str) -> str:
    """Minúsculas sin tildes ni espacios redundantes, para búsquedas por fragmento."""
    s = unicodedata.normalize('NFKD', value or '')
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return re.sub(r'\s+', ' ', s.strip().lower())


def _pais_valido(pais: str | None) -> str:
    """Normaliza y valida el slug del país (minúsculas). Devuelve '' si no es válido."""
    clave = _normalizar_q(pais or '').lower()
    if clave in PAISES_TARJETAS:
        return clave
    # Permitir coincidencia por nombre o bandera
    for slug, meta in PAISES_TARJETAS.items():
        if _normalizar_q(slug).lower() == clave or _normalizar_q(meta['nombre']).lower() == clave:
            return slug
    return ''


@router.get("/paises-tarjetas")
def listar_paises_tarjetas():
    """Lista los países y su bandera, en orden definido."""
    orden = ['colombia', 'ecuador', 'mexico', 'panama', 'peru']
    return [
        {'slug': slug, 'nombre': PAISES_TARJETAS[slug]['nombre'],
         'bandera': PAISES_TARJETAS[slug]['bandera']}
        for slug in orden
        if slug in PAISES_TARJETAS
    ]


@router.get("/tarjetas-comerciales")
def listar_tarjetas_comerciales(pais: str | None = None, q: str | None = None):
    """Lista los PPTX de tarjetas comerciales del país (búsqueda por fragmento)."""
    slug = _pais_valido(pais or '') if pais else None
    if slug is None:
        # Sin país: no hay forma de saber; devolvemos vacío para forzar selección.
        return []
    carpeta_pais = _TARJETAS_DIR / slug if slug else _TARJETAS_DIR
    if not carpeta_pais.exists():
        return []
    q_norm = _normalizar_q(q) if q else ''
    results = []
    for f in sorted(carpeta_pais.iterdir()):
        if f.is_file() and f.suffix.lower() == '.pptx':
            nombre = f.stem.strip()
            if not q_norm or q_norm in _normalizar_q(nombre):
                meta = PAISES_TARJETAS.get(slug, {})
                results.append({
                    "nombre": nombre,
                    "archivo": f.name,
                    "pais": slug,
                    "bandera": meta.get('bandera', ''),
                })
    return results


@router.post("/tarjetas-comerciales/upload")
def subir_tarjeta_comercial(file: UploadFile = File(...), pais: str = Form(...)):
    """Sube el PPTX de una tarjeta comercial. El nombre del archivo = nombre del comercial."""
    if not file.filename or Path(file.filename).suffix.lower() != '.pptx':
        raise HTTPException(status_code=400, detail="El archivo debe ser .pptx")
    slug = _pais_valido(pais)
    if not slug:
        raise HTTPException(status_code=400, detail="País inválido. Válidos: " + ', '.join(PAISES_TARJETAS))
    carpeta_pais = _TARJETAS_DIR / slug
    carpeta_pais.mkdir(parents=True, exist_ok=True)
    safe = Path(file.filename).name
    destino = carpeta_pais / safe
    destino.write_bytes(file.file.read())
    return {
        "nombre": destino.stem,
        "archivo": destino.name,
        "pais": slug,
        "bandera": PAISES_TARJETAS[slug].get('bandera', ''),
    }


@router.delete("/tarjetas-comerciales/{pais}/{nombre}")
def eliminar_tarjeta_comercial(pais: str, nombre: str):
    """Elimina el PPTX de una tarjeta comercial por país y nombre (sin extensión)."""
    slug = _pais_valido(pais)
    if not slug:
        raise HTTPException(status_code=404, detail="País no encontrado u inválido")
    carpeta_pais = _TARJETAS_DIR / slug
    if not carpeta_pais.exists():
        raise HTTPException(status_code=404, detail="No se encontró la tarjeta")
    for cand in carpeta_pais.iterdir():
        if cand.is_file() and cand.suffix.lower() == '.pptx' and _normalizar_q(cand.stem) == _normalizar_q(nombre):
            cand.unlink()
            return {"eliminado": cand.name, "pais": slug}
    raise HTTPException(status_code=404, detail="Tarjeta no encontrada")


@router.post("/generar", response_model=GenerarPropuestaResponse)
def generar_propuesta(request: GenerarPropuestaRequest, db: Session = Depends(get_db)):
    try:
        return service.generar_propuesta(db, request)
    except (ValueError, FileNotFoundError) as exc:
        error_msg = str(exc).strip() or "Error de validación"
        raise HTTPException(status_code=400, detail=error_msg)
    except Exception as exc:
        traceback.print_exc()
        error_msg = str(exc).strip() or "Error interno del servidor"
        raise HTTPException(status_code=500, detail=error_msg)


@router.post("/plantillas/upload")
def upload_template(
    file: UploadFile = File(...),
    filial: str = Form(...),
    section: str = Form("default"),
    template_name: str | None = Form(None),
):
    safe_filial = str(filial or "").strip().lower()
    if safe_filial not in {"corp", "group", "cbit"}:
        raise HTTPException(status_code=400, detail="Filial inválida")

    safe_section = str(section or "default").strip().lower() or "default"
    destination_dir = Path(service.settings.templates_path) / safe_filial / safe_section
    destination_dir.mkdir(parents=True, exist_ok=True)

    original_name = (template_name or file.filename or "template.pptx").strip()
    path_obj = Path(original_name)
    safe_name = path_obj.name or "template.pptx"
    if not path_obj.suffix:
        safe_name = f"{safe_name}.pptx"
    destination_path = destination_dir / safe_name

    contents = file.file.read()
    destination_path.write_bytes(contents)

    return {
        "filial": safe_filial,
        "section": safe_section,
        "template_name": safe_name,
        "path": str(destination_path),
    }


@router.get("/filiales")
def get_filiales():
    return ["corp", "group", "cbit"]
