import sys
sys.path.insert(0, '.')

import requests
from core import groq_client


class DummyResponse:
    def __init__(self, code, data):
        self.status_code = code
        self._d = data
        self.headers = {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError(str(self.status_code))

    def json(self):
        return self._d


calls = {'n': 0}
def fake_post(url, headers, json, timeout):
    calls['n'] += 1
    if calls['n'] == 1:
        return DummyResponse(429, {'error': {'message': 'Rate limit reached ... Please try again in 1.5s.'}})
    return DummyResponse(200, {'choices': [{'message': {'content': 'Descripcion OK'}}]})

groq_client.settings.GROQ_API_KEY = 'fake'
groq_client.settings.GROQ_MODEL = 'groq/compound-mini'
groq_client.requests.post = fake_post
groq_client.time.sleep = lambda s: None

out = groq_client.create_chat_completion([{'role': 'user', 'content': 'x'}])
print('llamadas totales:', calls['n'])
print('salida:', out)
assert calls['n'] == 2, 'Debe reintentar exactamente 1 vez'
assert out == 'Descripcion OK', 'Debe devolver la respuesta del 2do intento'

# Caso: 429 persistente -> debe lanzar RuntimeError tras agotar reintentos
def always_429(url, headers, json, timeout):
    calls['n'] += 1
    return DummyResponse(429, {'error': {'message': 'Rate limit reached'}})

groq_client.requests.post = always_429
try:
    groq_client.create_chat_completion([{'role': 'user', 'content': 'x'}])
    raise SystemExit('ERROR: debio lanzar RuntimeError')
except RuntimeError as e:
    print('429 persistente ->', str(e)[:60], '... (OK)')

print('SIMULACION 429->RETRY: OK')