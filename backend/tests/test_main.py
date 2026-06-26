"""
Tests para main.py y server.py
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# We test the health endpoint and the app creation
from main import app


client = TestClient(app)


class TestHealth:
    def test_health_endpoint(self):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_app_title(self):
        assert app.title == "Solutions API"
        assert app.version == "2.0.0"


class TestCORS:
    def test_cors_headers(self):
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            }
        )
        assert response.status_code == 200


@pytest.mark.parametrize("filial", ["corp", "group", "cbit"])
def test_filiales_route(filial):
    response = client.get("/api/v1/propuesta/filiales")
    assert response.status_code == 200
    assert filial in response.json()


class TestRouterRegistration:
    def test_routes_loaded(self):
        routes = [route.path for route in app.routes]
        assert "/api/v1/catalogo/torres" in routes
        assert "/api/v1/propuesta/generar" in routes
        assert "/api/v1/cronograma/generar" in routes
        assert "/api/v1/ai/chat" in routes
        assert any("quality" in r for r in routes)
        assert "/health" in routes