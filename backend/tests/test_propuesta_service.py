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


def test_generar_propuesta_uses_custom_template_name(monkeypatch, tmp_path):
    template_dir = tmp_path / "corp"
    template_dir.mkdir()
    custom_template = template_dir / "custom-template.pptx"
    custom_template.write_bytes(b"custom-pptx")

    monkeypatch.setattr(service, "settings", SimpleNamespace(templates_path=tmp_path))
    monkeypatch.setattr(service, "build_catalog_data", lambda db: {"torres": []})
    monkeypatch.setattr(service, "generate_as_is_to_be", lambda excel_data, desc: ("AS-IS", "TO-BE"))
    monkeypatch.setattr(service, "generate_roadmap_phases", lambda excel_data: [{"name": "Fase 1"}])

    captured = {}

    def fake_generate(pptx_bytes, config, catalog_data):
        captured["pptx_bytes"] = pptx_bytes
        return b"pptx-ok"

    monkeypatch.setattr(service.orchestrator, "generate", fake_generate)

    request = GenerarPropuestaRequest(filial="corp", template_name="custom-template.pptx", excel_data={})
    response = service.generar_propuesta(None, request)

    assert response.filename == "Propuesta_Periferia_CORP.pptx"
    assert base64.b64decode(response.content_b64) == b"pptx-ok"
    assert captured["pptx_bytes"] == b"custom-pptx"


def test_generar_propuesta_continues_when_ai_fails(monkeypatch, tmp_path):
    template_file = tmp_path / "CS-FR-012-PROPUESTA_COMERCIAL_PERIFERIA_IT_CORP.pptx"
    template_file.write_bytes(b"fake-pptx")

    monkeypatch.setattr(service, "settings", SimpleNamespace(templates_path=tmp_path))
    monkeypatch.setattr(service, "build_catalog_data", lambda db: {"torres": []})

    def fail_as_is(excel_data, desc):
        raise RuntimeError("groq rate limit")

    def fail_roadmap(excel_data):
        raise RuntimeError("roadmap failed")

    monkeypatch.setattr(service, "generate_as_is_to_be", fail_as_is)
    monkeypatch.setattr(service, "generate_roadmap_phases", fail_roadmap)
    monkeypatch.setattr(service.orchestrator, "generate", lambda pptx_bytes, config, catalog_data: b"pptx-ok")

    request = GenerarPropuestaRequest(filial="corp", incluir_as_is_to_be=True, excel_data={})
    response = service.generar_propuesta(None, request)

    assert response.filename == "Propuesta_Periferia_CORP.pptx"
    assert base64.b64decode(response.content_b64) == b"pptx-ok"


def test_generar_propuesta_enriches_missing_catalog_items_with_ai(monkeypatch, tmp_path):
    template_file = tmp_path / "CS-FR-012-PROPUESTA_COMERCIAL_PERIFERIA_IT_CORP.pptx"
    template_file.write_bytes(b"fake-pptx")

    created = []
    captured = {}

    monkeypatch.setattr(service, "settings", SimpleNamespace(templates_path=tmp_path))
    monkeypatch.setattr(service, "build_catalog_data", lambda db: {
        "fda_db": {},
        "perf_db": {"TORRE A": [{"rol": "Ingeniero SRE", "desc": "desc generada"}]},
        "consideraciones_db": {"GENERALES": ["Consideración generada"]},
        "entregables_db": [{"torre": "Torre A", "items": ["Entregable generado"]}],
    })
    monkeypatch.setattr(service, "generate_as_is_to_be", lambda excel_data, desc: ("AS-IS", "TO-BE"))
    monkeypatch.setattr(service, "generate_roadmap_phases", lambda excel_data: [{"name": "Fase 1"}])
    monkeypatch.setattr(service, "generate_profile_description", lambda perfil, torre=None: "Descripción de perfil generada")
    monkeypatch.setattr(service, "generate_consideration_description", lambda texto, torre=None: "Descripción de consideración generada")
    monkeypatch.setattr(service, "generate_entregable_description", lambda item, torre=None: "Descripción de entregable generada")
    monkeypatch.setattr(service, "generate_fuera_alcance_description", lambda item, torre=None: "Descripción de fuera de alcance generada")

    def fake_create_torre(db, nombre):
        return SimpleNamespace(id=1, nombre=nombre, nombre_norm=nombre.upper())

    def fake_create_perfil(db, torre_id, rol, descripcion):
        created.append(("perfil", rol, descripcion))
        return SimpleNamespace(id=10, torre_id=torre_id, rol=rol, descripcion=descripcion)

    def fake_create_consideracion(db, texto, torre_id, es_general, orden=0):
        created.append(("consideracion", texto, texto))
        return SimpleNamespace(id=20, torre_id=torre_id, texto=texto, es_general=es_general, orden=orden)

    def fake_create_entregable(db, torre_id, item, orden=0):
        created.append(("entregable", item, torre_id))
        return SimpleNamespace(id=30, torre_id=torre_id, item=item, orden=orden)

    def fake_create_fuera_alcance(db, torre_id, item, orden=0):
        created.append(("fda", item, torre_id))
        return SimpleNamespace(id=40, torre_id=torre_id, item=item, orden=orden)

    monkeypatch.setattr(service.repo, "create_torre", fake_create_torre)
    monkeypatch.setattr(service.repo, "create_perfil", fake_create_perfil)
    monkeypatch.setattr(service.repo, "create_consideracion", fake_create_consideracion)
    monkeypatch.setattr(service.repo, "create_entregable", fake_create_entregable)
    monkeypatch.setattr(service.repo, "create_fuera_alcance", fake_create_fuera_alcance)
    monkeypatch.setattr(service.repo, "get_perfiles", lambda db, torre_id=None: [])
    monkeypatch.setattr(service.repo, "get_consideraciones", lambda db, torre_id=None: [])
    monkeypatch.setattr(service.repo, "get_entregables", lambda db, torre_id=None: [])
    monkeypatch.setattr(service.repo, "get_fuera_alcance", lambda db, torre_id=None: [])

    def fake_generate(pptx_bytes, config, catalog_data):
        captured["catalog_data"] = catalog_data
        return b"pptx-ok"

    monkeypatch.setattr(service.orchestrator, "generate", fake_generate)

    request = GenerarPropuestaRequest(
        filial="corp",
        excel_data={
            "perfiles": [{"perfil": "Ingeniero SRE", "torre": "Torre A"}],
            "consideraciones": ["Consideración nueva"],
            "fda": ["Fuera de alcance nuevo"],
            "entregables": [{"torre": "Torre A", "items": ["Entregable nuevo"]}],
        },
    )

    response = service.generar_propuesta(None, request)

    assert response.filename == "Propuesta_Periferia_CORP.pptx"
    assert base64.b64decode(response.content_b64) == b"pptx-ok"
    assert any(item[0] == "perfil" and item[1] == "Ingeniero SRE" for item in created)
    assert any(item[0] == "consideracion" and item[1] == "Consideración nueva" for item in created)
    assert any(item[0] == "entregable" and item[1] == "Entregable nuevo" for item in created)
    assert any(item[0] == "fda" and item[1] == "Fuera de alcance nuevo" for item in created)
    assert captured["catalog_data"]["perf_db"]["TORRE A"][0]["desc"] == "desc generada"


def test_generar_propuesta_uses_fallback_when_ai_description_fails(monkeypatch, tmp_path):
    template_file = tmp_path / "CS-FR-012-PROPUESTA_COMERCIAL_PERIFERIA_IT_CORP.pptx"
    template_file.write_bytes(b"fake-pptx")

    created = []
    captured = {}

    monkeypatch.setattr(service, "settings", SimpleNamespace(templates_path=tmp_path))
    monkeypatch.setattr(service, "build_catalog_data", lambda db: {"fda_db": {}, "perf_db": {}, "consideraciones_db": {}, "entregables_db": []})
    monkeypatch.setattr(service, "generate_as_is_to_be", lambda excel_data, desc: ("AS-IS", "TO-BE"))
    monkeypatch.setattr(service, "generate_roadmap_phases", lambda excel_data: [{"name": "Fase 1"}])
    monkeypatch.setattr(service, "generate_profile_description", lambda perfil, torre=None: (_ for _ in ()).throw(RuntimeError("groq down")))
    monkeypatch.setattr(service, "generate_consideration_description", lambda texto, torre=None: (_ for _ in ()).throw(RuntimeError("groq down")))
    monkeypatch.setattr(service, "generate_entregable_description", lambda item, torre=None: (_ for _ in ()).throw(RuntimeError("groq down")))
    monkeypatch.setattr(service, "generate_fuera_alcance_description", lambda item, torre=None: (_ for _ in ()).throw(RuntimeError("groq down")))

    def capture_create_torre(db, nombre):
        created.append(("torre", nombre))
        return SimpleNamespace(id=1, nombre=nombre, nombre_norm=nombre.upper())

    def capture_create_perfil(db, torre_id, rol, descripcion):
        created.append(("perfil", rol, descripcion))
        return SimpleNamespace(id=10, torre_id=torre_id, rol=rol, descripcion=descripcion)

    def capture_create_consideracion(db, texto, torre_id, es_general, orden=0):
        created.append(("consideracion", texto, orden))
        return SimpleNamespace(id=20, torre_id=torre_id, texto=texto, es_general=es_general, orden=orden)

    def capture_create_entregable(db, torre_id, item, orden=0):
        created.append(("entregable", item, orden))
        return SimpleNamespace(id=30, torre_id=torre_id, item=item, orden=orden)

    def capture_create_fuera_alcance(db, torre_id, item, orden=0):
        created.append(("fda", item, orden))
        return SimpleNamespace(id=40, torre_id=torre_id, item=item, orden=orden)

    monkeypatch.setattr(service.repo, "create_torre", capture_create_torre)
    monkeypatch.setattr(service.repo, "create_perfil", capture_create_perfil)
    monkeypatch.setattr(service.repo, "create_consideracion", capture_create_consideracion)
    monkeypatch.setattr(service.repo, "create_entregable", capture_create_entregable)
    monkeypatch.setattr(service.repo, "create_fuera_alcance", capture_create_fuera_alcance)
    monkeypatch.setattr(service.repo, "get_perfiles", lambda db, torre_id=None: [])
    monkeypatch.setattr(service.repo, "get_consideraciones", lambda db, torre_id=None: [])
    monkeypatch.setattr(service.repo, "get_entregables", lambda db, torre_id=None: [])
    monkeypatch.setattr(service.repo, "get_fuera_alcance", lambda db, torre_id=None: [])

    def fake_generate(pptx_bytes, config, catalog_data):
        captured["catalog_data"] = catalog_data
        return b"pptx-ok"

    monkeypatch.setattr(service.orchestrator, "generate", fake_generate)

    request = GenerarPropuestaRequest(
        filial="corp",
        excel_data={
            "perfiles": [{"perfil": "Ingeniero SRE", "torre": "Torre A"}],
            "consideraciones": ["Consideración nueva"],
            "fda": ["Fuera de alcance nuevo"],
            "entregables": [{"torre": "Torre A", "items": ["Entregable nuevo"]}],
        },
    )

    response = service.generar_propuesta(None, request)

    assert response.filename == "Propuesta_Periferia_CORP.pptx"
    assert base64.b64decode(response.content_b64) == b"pptx-ok"
    assert captured["catalog_data"]["perf_db"]["A"][0]["desc"] == "No se encontró este perfil en la base de datos"
    assert captured["catalog_data"]["consideraciones_db"]["GENERALES"] == ["Consideración nueva"]
    assert captured["catalog_data"]["entregables_db"][0]["items"] == ["Entregable nuevo"]
    assert captured["catalog_data"]["fda_db"][""] == ["Fuera de alcance nuevo"]
    assert created == []


def test_get_filiales_route(client):
    response = client.get("/api/v1/propuesta/filiales")

    assert response.status_code == 200
    assert response.json() == ["corp", "group", "cbit"]
