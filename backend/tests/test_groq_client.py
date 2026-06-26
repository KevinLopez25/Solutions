import pytest
import requests

from core import groq_client


class DummyResponse:
    def __init__(self, json_data, status_code=200, raise_http=False):
        self._json = json_data
        self.status_code = status_code
        self._raise_http = raise_http

    def raise_for_status(self):
        if self.status_code >= 400 or self._raise_http:
            raise requests.exceptions.HTTPError(f'{self.status_code} Error')

    def json(self):
        return self._json


def test_create_chat_completion_success(monkeypatch):
    monkeypatch.setattr(groq_client.settings, 'GROQ_API_KEY', 'fake_key')
    monkeypatch.setattr(groq_client.settings, 'GROQ_BASE_URL', 'https://api.groq.com/openai/v1')
    monkeypatch.setattr(groq_client.settings, 'GROQ_MODEL', 'test-model')

    def post(url, headers, json, timeout):
        assert json['model'] == 'test-model'
        return DummyResponse({'choices': [{'message': {'content': 'Hola'}}]})

    monkeypatch.setattr(groq_client.requests, 'post', post)

    result = groq_client.create_chat_completion([{'role': 'user', 'content': 'Hola'}])

    assert result == 'Hola'


def test_create_chat_completion_timeout(monkeypatch):
    monkeypatch.setattr(groq_client.settings, 'GROQ_API_KEY', 'fake_key')

    def post(url, headers, json, timeout):
        raise requests.exceptions.Timeout()

    monkeypatch.setattr(groq_client.requests, 'post', post)

    with pytest.raises(RuntimeError, match='Timeout: Groq tardó demasiado en responder'):
        groq_client.create_chat_completion([{'role': 'user', 'content': 'Hola'}])


def test_create_chat_completion_no_content_raises(monkeypatch):
    monkeypatch.setattr(groq_client.settings, 'GROQ_API_KEY', 'fake_key')

    def post(url, headers, json, timeout):
        return DummyResponse({'choices': [{'message': {}}]})

    monkeypatch.setattr(groq_client.requests, 'post', post)

    with pytest.raises(RuntimeError, match='No se recibió contenido de Groq'):
        groq_client.create_chat_completion([{'role': 'user', 'content': 'Hola'}])


def test_create_chat_completion_connection_error(monkeypatch):
    monkeypatch.setattr(groq_client.settings, 'GROQ_API_KEY', 'fake_key')

    def post(url, headers, json, timeout):
        raise requests.exceptions.ConnectionError('falló conexión')

    monkeypatch.setattr(groq_client.requests, 'post', post)

    with pytest.raises(RuntimeError, match='Error de conexión con Groq:'): 
        groq_client.create_chat_completion([{'role': 'user', 'content': 'Hola'}])


def test_create_chat_completion_http_error_raises(monkeypatch):
    monkeypatch.setattr(groq_client.settings, 'GROQ_API_KEY', 'fake_key')

    def post(url, headers, json, timeout):
        return DummyResponse({'error': {'message': 'Solicitud inválida'}}, status_code=400, raise_http=True)

    monkeypatch.setattr(groq_client.requests, 'post', post)

    with pytest.raises(RuntimeError, match='Error HTTP de Groq: Solicitud inválida'):
        groq_client.create_chat_completion([{'role': 'user', 'content': 'Hola'}])
