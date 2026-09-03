import json
import logging
import re
import time

import requests

from core.config import settings

logger = logging.getLogger(__name__)

# Reintentos automáticos ante rate limit (HTTP 429) de Groq.
# `groq/compound-mini` enruta internamente a `openai/gpt-oss-120b`, cuyo límite
# en el tier gratuito es 8.000 tokens/minuto (TPM). Ante "Rate limit reached",
# Groq indica cuándo reintentar; esperamos ese tiempo y reintentamos la misma
# petición en lugar de fallar de inmediato.
_RATE_LIMIT_STATUS = 429
_MAX_RATE_LIMIT_RETRIES = 5
_MAX_RETRY_WAIT_SECONDS = 5.0


def _extract_error_message(response) -> str:
    """Extrae el mensaje de error legible desde la respuesta JSON de Groq."""
    error_msg = f"HTTP {response.status_code}"
    try:
        error_data = response.json()
        if isinstance(error_data, dict) and "error" in error_data:
            error_msg = str(error_data["error"].get("message", error_msg))
    except Exception:
        pass
    return error_msg


def _retry_after_seconds(response) -> float:
    """Cuántos segundos esperar antes de reintentar tras un rate limit."""
    try:
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            try:
                return float(retry_after)
            except (TypeError, ValueError):
                pass
        match = re.search(
            r"try again in ([\d.]+)\s*s",
            _extract_error_message(response),
            re.IGNORECASE,
        )
        if match:
            return float(match.group(1))
    except Exception:
        pass
    return 1.0


def create_chat_completion(messages: list[dict[str, str]], model: str | None = None, max_tokens: int = 1024) -> str:
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
        "max_tokens": max_tokens,
        "top_p": 0.95,
    }
    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        for attempt in range(1, _MAX_RATE_LIMIT_RETRIES + 2):
            response = requests.post(url, headers=headers, json=payload, timeout=30)

            if response.status_code == _RATE_LIMIT_STATUS and attempt <= _MAX_RATE_LIMIT_RETRIES:
                wait_seconds = _retry_after_seconds(response)
                wait_seconds = max(0.5, min(wait_seconds, _MAX_RETRY_WAIT_SECONDS))
                logger.warning(
                    "Rate limit de Groq (intento %d/%d). Reintentando en %.1fs...",
                    attempt,
                    _MAX_RATE_LIMIT_RETRIES,
                    wait_seconds,
                )
                time.sleep(wait_seconds)
                continue

            response.raise_for_status()
            break
        data = response.json()
    except requests.exceptions.Timeout:
        raise RuntimeError("Timeout: Groq tardó demasiado en responder")
    except requests.exceptions.ConnectionError as e:
        raise RuntimeError(f"Error de conexión con Groq: {str(e)}")
    except requests.exceptions.HTTPError as e:
        error_msg = _extract_error_message(response)
        raise RuntimeError(f"Error HTTP de Groq: {error_msg}") from e

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
