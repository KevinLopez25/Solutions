import base64

from api.v1.ai import router as ai_router


def test_ai_chat_route_success(client, monkeypatch):
    monkeypatch.setattr(ai_router, "ai_chat", lambda messages: "Hola desde IA")

    response = client.post(
        "/api/v1/ai/chat",
        json={"messages": [{"role": "user", "content": "Hola"}]},
    )

    assert response.status_code == 200
    assert response.json() == {"reply": "Hola desde IA"}


def test_ai_productivity_route_success(client, monkeypatch):
    monkeypatch.setattr(
        ai_router,
        "clasificar_productividad_perfiles",
        lambda perfiles: [
            {**perfiles[0], "indice": 0, "productivo": True, "explicacion": "Desarrolla código."},
            {**perfiles[1], "indice": 1, "productivo": False, "explicacion": "Coordina al equipo."},
        ],
    )

    response = client.post(
        "/api/v1/ai/clasificar-productividad",
        json={"perfiles": [
            {"perfil": "Desarrollador Java", "torre": "Backend", "personas": 1},
            {"perfil": "Líder Técnico", "torre": "Backend", "personas": 1},
        ]},
    )

    assert response.status_code == 200
    assert response.json()["perfiles"][1]["productivo"] is False


def test_ai_modify_proposal_validation_errors(client):
    response = client.post(
        "/api/v1/ai/modificar-propuesta",
        json={"messages": [], "content_b64": "", "instruction": "   "},
    )

    assert response.status_code == 400
    assert "obligatorio" in response.json()["detail"]


def test_ai_chat_propuesta_route_success(client, monkeypatch):
    monkeypatch.setattr(ai_router, "chat_with_proposal", lambda messages, pptx_bytes, db_session=None: ("Respuesta", b"nuevo"))
    content_b64 = base64.b64encode(b"fakepptx").decode()

    response = client.post(
        "/api/v1/ai/chat-propuesta",
        json={"messages": [{"role": "user", "content": "hola"}], "content_b64": content_b64},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["reply"] == "Respuesta"
    assert body["modified"] is True
    assert base64.b64decode(body["content_b64"]) == b"nuevo"


def test_ai_replace_logo_route_success(client, monkeypatch):
    monkeypatch.setattr(ai_router, "replace_logo_in_pptx", lambda pptx_bytes, logo_bytes, logo_mime: b"pptx-modificado")
    content_b64 = base64.b64encode(b"fakepptx").decode()
    logo_b64 = base64.b64encode(b"fakeimage").decode()

    response = client.post(
        "/api/v1/ai/reemplazar-logo",
        json={"content_b64": content_b64, "logo_b64": logo_b64, "logo_mime": "image/png"},
    )

    assert response.status_code == 200
    assert base64.b64decode(response.json()["content_b64"]) == b"pptx-modificado"
