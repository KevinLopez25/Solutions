import base64
from types import SimpleNamespace

import pytest

from domain.propuesta import service
from domain.propuesta.entities import GenerarPropuestaRequest


def test_generar_propuesta_invalid_filial():
    request = GenerarPropuestaRequest(filial="unknown")

    with pytest.raises(ValueError, match="Filial desconocida"):
        service.generar_propuesta(None, request)


def test_generar_propuesta_success(monkeypatch, tmp_path):
    template_file = tmp_path / "CS-FR-012-PROPUESTA_COMERCIAL_PERIFERIA_IT_CORP.pptx"
    template_file.write_bytes(b"fake-pptx")

    monkeypatch.setattr(service, "settings", SimpleNamespace(templates_path=tmp_path))
    monkeypatch.setattr(service, "build_catalog_data", lambda db: {"torres": []})
    monkeypatch.setattr(service, "generate_as_is_to_be", lambda excel_data, desc: ("AS-IS", "TO-BE"))
    monkeypatch.setattr(service, "generate_roadmap_phases", lambda excel_data: [{"name": "Fase 1"}])
    monkeypatch.setattr(service.orchestrator, "generate", lambda pptx_bytes, config, catalog_data: b"pptx-ok")

    request = GenerarPropuestaRequest(filial="corp", incluir_as_is_to_be=True, excel_data={})
    response = service.generar_propuesta(None, request)

    assert response.filename == "Propuesta_Periferia_CORP.pptx"
    assert base64.b64decode(response.content_b64) == b"pptx-ok"


def test_get_filiales_route(client):
    response = client.get("/api/v1/propuesta/filiales")

    assert response.status_code == 200
    assert response.json() == ["corp", "group", "cbit"]
