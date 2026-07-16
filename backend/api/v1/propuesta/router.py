import traceback
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from core.dependencies import get_db
from domain.propuesta.entities import GenerarPropuestaRequest, GenerarPropuestaResponse
from domain.propuesta import service

router = APIRouter(prefix="/propuesta", tags=["Propuesta"])


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
