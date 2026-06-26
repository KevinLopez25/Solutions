def test_get_catalogo_torres_empty(client):
    response = client.get("/api/v1/catalogo/torres")

    assert response.status_code == 200
    assert response.json() == []


def test_create_catalogo_torre(client):
    payload = {"nombre": "Router Torre"}
    response = client.post("/api/v1/catalogo/torres", json=payload)

    assert response.status_code == 201
    body = response.json()
    assert body["nombre"] == "Router Torre"
    assert body["nombre_norm"] == "ROUTER TORRE"


def test_catalogo_perfiles_crud(client):
    torre = client.post("/api/v1/catalogo/torres", json={"nombre": "Torre Perfil"}).json()

    perfil_payload = {
        "torre_id": torre["id"],
        "rol": "Desarrollador Test",
        "descripcion": "Prueba de perfil",
    }
    response = client.post("/api/v1/catalogo/perfiles", json=perfil_payload)
    assert response.status_code == 201
    perfil = response.json()
    assert perfil["rol"] == perfil_payload["rol"]

    list_response = client.get(f"/api/v1/catalogo/perfiles?torre_id={torre['id']}")
    assert list_response.status_code == 200
    assert any(item["id"] == perfil["id"] for item in list_response.json())

    update_payload = {"rol": "Dev Actualizado", "descripcion": "Actualizado"}
    update_response = client.put(f"/api/v1/catalogo/perfiles/{perfil['id']}", json=update_payload)
    assert update_response.status_code == 200
    assert update_response.json()["rol"] == "Dev Actualizado"

    delete_response = client.delete(f"/api/v1/catalogo/perfiles/{perfil['id']}")
    assert delete_response.status_code == 204
    assert client.get(f"/api/v1/catalogo/perfiles?torre_id={torre['id']}").json() == []


def test_catalogo_consideraciones_crud(client):
    torre = client.post("/api/v1/catalogo/torres", json={"nombre": "Torre Consid"}).json()

    consideracion_payload = {
        "texto": "Texto de consideración",
        "torre_id": torre["id"],
        "es_general": False,
        "orden": 1,
    }
    response = client.post("/api/v1/catalogo/consideraciones", json=consideracion_payload)
    assert response.status_code == 201
    consid = response.json()
    assert consid["texto"] == consideracion_payload["texto"]

    list_response = client.get(f"/api/v1/catalogo/consideraciones?torre_id={torre['id']}")
    assert list_response.status_code == 200
    assert any(item["id"] == consid["id"] for item in list_response.json())

    update_payload = {"texto": "Texto modificado", "orden": 2}
    update_response = client.put(f"/api/v1/catalogo/consideraciones/{consid['id']}", json=update_payload)
    assert update_response.status_code == 200
    assert update_response.json()["texto"] == "Texto modificado"

    delete_response = client.delete(f"/api/v1/catalogo/consideraciones/{consid['id']}")
    assert delete_response.status_code == 204
    assert client.get(f"/api/v1/catalogo/consideraciones?torre_id={torre['id']}").json() == []


def test_catalogo_entregables_crud(client):
    torre = client.post("/api/v1/catalogo/torres", json={"nombre": "Torre Entregable"}).json()

    entregable_payload = {"torre_id": torre["id"], "item": "Entregable 1", "orden": 1}
    response = client.post("/api/v1/catalogo/entregables", json=entregable_payload)
    assert response.status_code == 201
    entregable = response.json()
    assert entregable["item"] == entregable_payload["item"]

    list_response = client.get(f"/api/v1/catalogo/entregables?torre_id={torre['id']}")
    assert list_response.status_code == 200
    assert any(item["id"] == entregable["id"] for item in list_response.json())

    update_payload = {"item": "Entregable X", "orden": 5}
    update_response = client.put(f"/api/v1/catalogo/entregables/{entregable['id']}", json=update_payload)
    assert update_response.status_code == 200
    assert update_response.json()["item"] == "Entregable X"

    delete_response = client.delete(f"/api/v1/catalogo/entregables/{entregable['id']}")
    assert delete_response.status_code == 204
    assert client.get(f"/api/v1/catalogo/entregables?torre_id={torre['id']}").json() == []


def test_catalogo_fuera_alcance_crud(client):
    torre = client.post("/api/v1/catalogo/torres", json={"nombre": "Torre FDA"}).json()

    fda_payload = {"torre_id": torre["id"], "item": "Ítem FDA", "orden": 1}
    response = client.post("/api/v1/catalogo/fuera-del-alcance", json=fda_payload)
    assert response.status_code == 201
    fda = response.json()
    assert fda["item"] == fda_payload["item"]

    list_response = client.get(f"/api/v1/catalogo/fuera-del-alcance?torre_id={torre['id']}")
    assert list_response.status_code == 200
    assert any(item["id"] == fda["id"] for item in list_response.json())

    update_payload = {"item": "Ítem FDA modificado", "orden": 2}
    update_response = client.put(f"/api/v1/catalogo/fuera-del-alcance/{fda['id']}", json=update_payload)
    assert update_response.status_code == 200
    assert update_response.json()["item"] == "Ítem FDA modificado"

    delete_response = client.delete(f"/api/v1/catalogo/fuera-del-alcance/{fda['id']}")
    assert delete_response.status_code == 204
    assert client.get(f"/api/v1/catalogo/fuera-del-alcance?torre_id={torre['id']}").json() == []


def test_catalogo_update_perfil_not_found_returns_404(client):
    response = client.put("/api/v1/catalogo/perfiles/999", json={"rol": "X", "descripcion": "Y"})

    assert response.status_code == 404
    assert response.json()["detail"] == "Perfil no encontrado"


def test_catalogo_delete_torre_not_found_returns_404(client):
    response = client.delete("/api/v1/catalogo/torres/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Torre no encontrada"
