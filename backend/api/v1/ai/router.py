from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from domain.ai.service import chat as ai_chat


class AIMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class AIChatRequest(BaseModel):
    messages: list[AIMessage]


class AIChatResponse(BaseModel):
    reply: str


router = APIRouter(prefix="/ai", tags=["IA"])


@router.post("/chat", response_model=AIChatResponse)
def chat_with_ai(request: AIChatRequest):
    try:
        reply = ai_chat([msg.dict() for msg in request.messages])
        return AIChatResponse(reply=reply)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc) or "Error interno en el servicio IA")
