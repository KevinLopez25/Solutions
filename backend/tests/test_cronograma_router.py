import base64

from domain.cronograma import service as cronograma_service


def test_generar_cronograma_route_success(client, monkeypatch):
    monkeypatch.setattr(cronograma_service.cronograma_excel, "generate_cronograma", lambda config: b"xlsx-bytes")
    payload = {
        "proyecto": "Mi Proyecto",
        "actividades": [{"torre": "DevOps", "horas": 8}],
    }

    response = client.post("/api/v1/cronograma/generar", json=payload)

    assert response.status_code == 200
    assert response.json()["filename"] == "Cronograma_Mi Proyecto.xlsx"
    assert base64.b64decode(response.json()["content_b64"]) == b"xlsx-bytes"


def test_generar_cronograma_route_error_when_no_actividades(client, monkeypatch):
    def raise_value_error(config):
        raise ValueError("No hay actividades")

    monkeypatch.setattr(cronograma_service.cronograma_excel, "generate_cronograma", raise_value_error)
    response = client.post("/api/v1/cronograma/generar", json={"proyecto": "Demo", "actividades": []})

    assert response.status_code == 500
    assert "Error interno" in response.json()["detail"]
