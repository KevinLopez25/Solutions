import base64
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from domain.ai.service import chat as ai_chat, chat_with_proposal, replace_logo_in_pptx, review_and_modify_proposal


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
def chat_with_proposal_endpoint(request: AIChatProposalRequest):
    pptx_bytes = base64.b64decode(request.content_b64) if request.content_b64 else None
    try:
        reply, modified_bytes = chat_with_proposal(
            [msg.dict() for msg in request.messages],
            pptx_bytes,
        )
        modified_b64 = base64.b64encode(modified_bytes).decode() if modified_bytes else None
        return AIChatProposalResponse(
            reply=reply,
            content_b64=modified_b64,
            modified=modified_bytes is not None,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc) or 'Error interno al procesar la propuesta')


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
