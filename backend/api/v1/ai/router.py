import base64
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.dependencies import get_db
from domain.ai.service import (
    chat as ai_chat,
    chat_with_proposal,
    replace_logo_in_pptx,
    review_and_modify_proposal,
    completar_descripciones_catalogo,
    completar_descripciones_y_pptx,
    sugerir_descripciones_pendientes,
    aplicar_descripciones_aprobadas,
)


class AIMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class AIChatRequest(BaseModel):
    messages: list[AIMessage]


class AIChatResponse(BaseModel):
    reply: str


class AIModifyProposalRequest(BaseModel):
    messages: list[AIMessage]
    content_b64: str
    instruction: str


class AIModifyProposalResponse(BaseModel):
    reply: str
    content_b64: str


router = APIRouter(prefix="/ai", tags=["IA"])


@router.post("/chat", response_model=AIChatResponse)
def chat_with_ai(request: AIChatRequest):
    try:
        reply = ai_chat([msg.dict() for msg in request.messages])
        return AIChatResponse(reply=reply)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc) or "Error interno en el servicio IA")


@router.post("/modificar-propuesta", response_model=AIModifyProposalResponse)
def modify_proposal(request: AIModifyProposalRequest):
    if not request.content_b64:
        raise HTTPException(status_code=400, detail="El contenido del documento es obligatorio.")
    if not request.instruction.strip():
        raise HTTPException(status_code=400, detail="La instrucción de modificación es obligatoria.")

    try:
        reply, modified_b64 = review_and_modify_proposal(
            [msg.dict() for msg in request.messages],
            request.content_b64,
            request.instruction.strip(),
        )
        return AIModifyProposalResponse(reply=reply, content_b64=modified_b64)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc) or "Error interno al modificar la propuesta")


class AIChatProposalRequest(BaseModel):
    messages: list[AIMessage]
    content_b64: str | None = None


class AIChatProposalResponse(BaseModel):
    reply: str
    content_b64: str | None = None
    modified: bool = False


@router.post("/chat-propuesta", response_model=AIChatProposalResponse)
def chat_with_proposal_endpoint(request: AIChatProposalRequest, db: Session = Depends(get_db)):
    pptx_bytes = base64.b64decode(request.content_b64) if request.content_b64 else None
    try:
        reply, modified_bytes = chat_with_proposal(
            [msg.dict() for msg in request.messages],
            pptx_bytes,
            db_session=db,
        )
        modified_b64 = base64.b64encode(modified_bytes).decode() if modified_bytes else None
        return AIChatProposalResponse(
            reply=reply,
            content_b64=modified_b64,
            modified=modified_bytes is not None,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc) or 'Error interno al procesar la propuesta')


class AICatalogoRequest(BaseModel):
    entity_type: str
    items: list[dict]


class AICatalogoResponse(BaseModel):
    completados: list[dict]
    total: int
    mensaje: str


class AICompletarDescripcionesRequest(BaseModel):
    content_b64: str | None = None


class AICompletarDescripcionesResponse(BaseModel):
    reply: str
    content_b64: str | None = None
    modified: bool = False


@router.post("/completar-descripciones", response_model=AICompletarDescripcionesResponse)
def completar_descripciones_endpoint(
    request: AICompletarDescripcionesRequest, db: Session = Depends(get_db)
):
    pptx_bytes = base64.b64decode(request.content_b64) if request.content_b64 else None
    try:
        reply, updated_bytes = completar_descripciones_y_pptx(
            pptx_bytes if pptx_bytes else b'',
            db_session=db,
        )
        modified_b64 = base64.b64encode(updated_bytes).decode() if updated_bytes else None
        return AICompletarDescripcionesResponse(
            reply=reply,
            content_b64=modified_b64,
            modified=updated_bytes is not None and pptx_bytes is not None,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc) or "Error al completar las descripciones con IA",
        )


class AISugerirDescripcionesRequest(BaseModel):
    content_b64: str | None = None


class AISugerirDescripcionesResponse(BaseModel):
    sugerencias: list[dict]
    reply: str


@router.post("/sugerir-descripciones", response_model=AISugerirDescripcionesResponse)
def sugerir_descripciones_endpoint(
    request: AISugerirDescripcionesRequest, db: Session = Depends(get_db)
):
    pptx_bytes = base64.b64decode(request.content_b64) if request.content_b64 else None
    try:
        result = sugerir_descripciones_pendientes(
            pptx_bytes if pptx_bytes else b'',
            db_session=db,
        )
        return AISugerirDescripcionesResponse(
            sugerencias=result.get('sugerencias', []),
            reply=result.get('reply', ''),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc) or "Error al sugerir descripciones con IA",
        )


class AIAplicarDescripcionesRequest(BaseModel):
    content_b64: str | None = None
    descripciones: list[dict]


class AIAplicarDescripcionesResponse(BaseModel):
    reply: str
    content_b64: str | None = None
    modified: bool = False


@router.post("/aplicar-descripciones", response_model=AIAplicarDescripcionesResponse)
def aplicar_descripciones_endpoint(
    request: AIAplicarDescripcionesRequest, db: Session = Depends(get_db)
):
    pptx_bytes = base64.b64decode(request.content_b64) if request.content_b64 else None
    if not pptx_bytes:
        raise HTTPException(status_code=400, detail="El contenido del documento es obligatorio.")
    if not request.descripciones:
        raise HTTPException(status_code=400, detail="La lista de descripciones está vacía.")
    try:
        reply, updated_bytes = aplicar_descripciones_aprobadas(
            pptx_bytes,
            request.descripciones,
            db_session=db,
        )
        modified_b64 = base64.b64encode(updated_bytes).decode() if updated_bytes else None
        return AIAplicarDescripcionesResponse(
            reply=reply,
            content_b64=modified_b64,
            modified=updated_bytes is not None and updated_bytes != pptx_bytes,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc) or "Error al aplicar las descripciones aprobadas",
        )


@router.post("/completar-catalogo", response_model=AICatalogoResponse)
def completar_catalogo_endpoint(request: AICatalogoRequest, db: Session = Depends(get_db)):
    valid_types = {'perfil', 'consideracion', 'entregable', 'fda'}
    if request.entity_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo inválido: '{request.entity_type}'. Válidos: {', '.join(valid_types)}"
        )
    if not request.items:
        raise HTTPException(status_code=400, detail="La lista de ítems está vacía.")

    try:
        completados = completar_descripciones_catalogo(
            entity_type=request.entity_type,
            items=request.items,
            db_session=db,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc) or "Error al completar descripciones del catálogo")

    return AICatalogoResponse(
        completados=completados,
        total=len(completados),
        mensaje=f"Se completaron {len(completados)} descripciones de {len(request.items)} ítems solicitados." if completados else
                "No se pudo completar ninguna descripción. Verifica que los ítems tengan datos válidos."
    )


class AIReplaceLogoRequest(BaseModel):
    content_b64: str
    logo_b64: str
    logo_mime: str = 'image/png'


class AIReplaceLogoResponse(BaseModel):
    content_b64: str


@router.post("/reemplazar-logo", response_model=AIReplaceLogoResponse)
def replace_logo(request: AIReplaceLogoRequest):
    if not request.content_b64:
        raise HTTPException(status_code=400, detail="El contenido del documento es obligatorio.")
    if not request.logo_b64:
        raise HTTPException(status_code=400, detail="La imagen del logo es obligatoria.")
    try:
        logo_bytes = base64.b64decode(request.logo_b64)
        pptx_bytes = base64.b64decode(request.content_b64)
        modified_bytes = replace_logo_in_pptx(pptx_bytes, logo_bytes, request.logo_mime)
        modified_b64 = base64.b64encode(modified_bytes).decode()
        return AIReplaceLogoResponse(content_b64=modified_b64)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc) or "Error interno al reemplazar el logo")