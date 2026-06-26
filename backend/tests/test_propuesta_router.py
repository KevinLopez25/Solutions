import base64
from types import SimpleNamespace

from domain.propuesta import service as propuesta_service


def test_generar_propuesta_route_success(client, monkeypatch, tmp_path):
    template_file = tmp_path / "CS-FR-012-PROPUESTA_COMERCIAL_PERIFERIA_IT_CORP.pptx"
    template_file.write_bytes(b"fake-pptx")

    monkeypatch.setattr(propuesta_service, "settings", SimpleNamespace(templates_path=tmp_path))
    monkeypatch.setattr(propuesta_service, "build_catalog_data", lambda db: {"torres": []})
    monkeypatch.setattr(propuesta_service, "generate_as_is_to_be", lambda excel_data, desc: ("AS-IS", "TO-BE"))
    monkeypatch.setattr(propuesta_service, "generate_roadmap_phases", lambda excel_data: [{"name": "Fase 1"}])
    monkeypatch.setattr(propuesta_service.orchestrator, "generate", lambda pptx_bytes, config, catalog_data: b"generated-pptx")

    payload = {"filial": "corp", "incluir_as_is_to_be": True, "excel_data": {}}
    response = client.post("/api/v1/propuesta/generar", json=payload)

    assert response.status_code == 200
    assert response.json()["filename"] == "Propuesta_Periferia_CORP.pptx"
    assert base64.b64decode(response.json()["content_b64"]) == b"generated-pptx"


def test_generar_propuesta_route_template_not_found(client, monkeypatch, tmp_path):
    monkeypatch.setattr(propuesta_service, "settings", SimpleNamespace(templates_path=tmp_path))
    monkeypatch.setattr(propuesta_service, "build_catalog_data", lambda db: {})
    monkeypatch.setattr(propuesta_service.orchestrator, "generate", lambda pptx_bytes, config, catalog_data: b"")

    response = client.post("/api/v1/propuesta/generar", json={"filial": "corp"})
    assert response.status_code == 400
    assert "Plantilla no encontrada" in response.json()["detail"]


def test_get_filiales_route(client):
    response = client.get("/api/v1/propuesta/filiales")

    assert response.status_code == 200
    assert response.json() == ["corp", "group", "cbit"]


def test_generar_propuesta_route_validation_error(client, monkeypatch):
    def raise_validation_error(db, request):
        raise ValueError("Validación fallida")

    monkeypatch.setattr(propuesta_service, "generar_propuesta", raise_validation_error)

    response = client.post("/api/v1/propuesta/generar", json={"filial": "corp"})

    assert response.status_code == 400
    assert response.json()["detail"] == "Validación fallida"
