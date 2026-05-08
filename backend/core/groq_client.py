import json
import requests
import logging

from core.config import settings

logger = logging.getLogger(__name__)


def create_chat_completion(messages: list[dict[str, str]], model: str | None = None) -> str:
    if not settings.GROQ_API_KEY:
        raise RuntimeError(
            "La variable de entorno GROQ_API_KEY no está configurada. "
            "Agrega tu clave en el archivo .env"
        )

    model = model or settings.GROQ_MODEL
    url = f"{settings.GROQ_BASE_URL}/chat/completions"
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": 1024,
        "top_p": 0.95,
    }
    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.Timeout:
        raise RuntimeError("Timeout: Groq tardó demasiado en responder")
    except requests.exceptions.ConnectionError as e:
        raise RuntimeError(f"Error de conexión con Groq: {str(e)}")
    except requests.exceptions.HTTPError as e:
        error_msg = str(e)
        try:
            error_data = response.json()
            if isinstance(error_data, dict) and "error" in error_data:
                error_msg = error_data["error"].get("message", error_msg)
        except Exception:
            pass
        raise RuntimeError(f"Error HTTP de Groq: {error_msg}")

    if not isinstance(data, dict):
        raise RuntimeError("Respuesta inesperada desde Groq: se esperaba un diccionario JSON")

    message = None
    choices = data.get("choices") or []
    if len(choices) > 0:
        choice = choices[0]
        message = choice.get("message") or choice.get("text")

    if isinstance(message, dict):
        content = message.get("content")
    else:
        content = message

    if not content:
        raise RuntimeError(f"No se recibió contenido de Groq: {json.dumps(data, ensure_ascii=False)}")

    return str(content).strip()
