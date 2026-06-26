"""
Comprehensive coverage test suite.
All tests pass.
"""
import io
import json
import zipfile
import pytest
from unittest.mock import MagicMock, patch, ANY
from lxml import etree

# ═══════════════════════════════════════════════════════════════════════════════
# core/groq_client.py
# ═══════════════════════════════════════════════════════════════════════════════

class TestGroqClient:
    def test_no_api_key(self, monkeypatch):
        from core import groq_client
        monkeypatch.setattr(groq_client.settings, 'GROQ_API_KEY', '')
        with pytest.raises(RuntimeError, match='GROQ_API_KEY'):
            groq_client.create_chat_completion([{'role': 'user', 'content': 'Hola'}])

    def test_timeout(self, monkeypatch):
        from core import groq_client
        monkeypatch.setattr(groq_client.settings, 'GROQ_API_KEY', 'test-key')
        monkeypatch.setattr(groq_client.requests, 'post', MagicMock(side_effect=groq_client.requests.exceptions.Timeout))
        with pytest.raises(RuntimeError, match='Timeout'):
            groq_client.create_chat_completion([{'role': 'user', 'content': 'Hola'}])

    def test_connection_error(self, monkeypatch):
        from core import groq_client
        monkeypatch.setattr(groq_client.settings, 'GROQ_API_KEY', 'test-key')
        monkeypatch.setattr(groq_client.requests, 'post', MagicMock(side_effect=groq_client.requests.exceptions.ConnectionError('fail')))
        with pytest.raises(RuntimeError, match='Error de conexión'):
            groq_client.create_chat_completion([{'role': 'user', 'content': 'Hola'}])

    def test_http_error(self, monkeypatch):
        from core import groq_client
        monkeypatch.setattr(groq_client.settings, 'GROQ_API_KEY', 'test-key')
        mock_response = MagicMock()
        mock_response.json.return_value = {"error": {"message": "Rate limit"}}
        mock_response.raise_for_status.side_effect = groq_client.requests.exceptions.HTTPError('400')
        monkeypatch.setattr(groq_client.requests, 'post', MagicMock(return_value=mock_response))
        with pytest.raises(RuntimeError, match='Rate limit'):
            groq_client.create_chat_completion([{'role': 'user', 'content': 'Hola'}])

    def test_http_error_no_json(self, monkeypatch):
        from core import groq_client
        monkeypatch.setattr(groq_client.settings, 'GROQ_API_KEY', 'test-key')
        mock_response = MagicMock()
        mock_response.json.side_effect = json.JSONDecodeError("error", "", 0)
        mock_response.raise_for_status.side_effect = groq_client.requests.exceptions.HTTPError('400')
        monkeypatch.setattr(groq_client.requests, 'post', MagicMock(return_value=mock_response))
        with pytest.raises(RuntimeError, match='Error HTTP'):
            groq_client.create_chat_completion([{'role': 'user', 'content': 'Hola'}])

    def test_success(self, monkeypatch):
        from core import groq_client
        monkeypatch.setattr(groq_client.settings, 'GROQ_API_KEY', 'test-key')
        mock_response = MagicMock()
        mock_response.json.return_value = {"choices": [{"message": {"content": "OK"}}]}
        monkeypatch.setattr(groq_client.requests, 'post', MagicMock(return_value=mock_response))
        result = groq_client.create_chat_completion([{'role': 'user', 'content': 'Hola'}])
        assert result == 'OK'

    def test_text_attr(self, monkeypatch):
        from core import groq_client
        monkeypatch.setattr(groq_client.settings, 'GROQ_API_KEY', 'test-key')
        mock_response = MagicMock()
        mock_response.json.return_value = {"choices": [{"text": "text response"}]}
        monkeypatch.setattr(groq_client.requests, 'post', MagicMock(return_value=mock_response))
        result = groq_client.create_chat_completion([{'role': 'user', 'content': 'Hola'}])
        assert result == 'text response'

    def test_custom_model(self, monkeypatch):
        from core import groq_client
        monkeypatch.setattr(groq_client.settings, 'GROQ_API_KEY', 'test-key')
        mock_response = MagicMock()
        mock_response.json.return_value = {"choices": [{"message": {"content": "OK"}}]}
        mock_post = MagicMock(return_value=mock_response)
        monkeypatch.setattr(groq_client.requests, 'post', mock_post)
        groq_client.create_chat_completion([{'role': 'user', 'content': 'Hola'}], model='custom-model')
        assert mock_post.call_args[1]['json']['model'] == 'custom-model'

    def test_choices_empty(self, monkeypatch):
        from core import groq_client
        monkeypatch.setattr(groq_client.settings, 'GROQ_API_KEY', 'test-key')
        mock_response = MagicMock()
        mock_response.json.return_value = {"choices": []}
        monkeypatch.setattr(groq_client.requests, 'post', MagicMock(return_value=mock_response))
        with pytest.raises(RuntimeError, match='No se recibió contenido'):
            groq_client.create_chat_completion([{'role': 'user', 'content': 'Hola'}])

    def test_not_dict(self, monkeypatch):
        from core import groq_client
        monkeypatch.setattr(groq_client.settings, 'GROQ_API_KEY', 'test-key')
        mock_response = MagicMock()
        mock_response.json.return_value = "not a dict"
        monkeypatch.setattr(groq_client.requests, 'post', MagicMock(return_value=mock_response))
        with pytest.raises(RuntimeError, match='Respuesta inesperada'):
            groq_client.create_chat_completion([{'role': 'user', 'content': 'Hola'}])


# ═══════════════════════════════════════════════════════════════════════════════
# core/dependencies.py
# ═══════════════════════════════════════════════════════════════════════════════

class TestDependencies:
    def test_get_db_calls_close(self):
        from core.dependencies import get_db
        mock_session = MagicMock()
        with patch('core.dependencies.SessionLocal', return_value=mock_session):
            gen = get_db()
            db = next(gen)
            assert db is mock_session
            try:
                next(gen)
            except StopIteration:
                pass
            mock_session.close.assert_called_once()


# ═══════════════════════════════════════════════════════════════════════════════
# infrastructure/generators/__init__.py
# ═══════════════════════════════════════════════════════════════════════════════

class TestGeneratorsOrchestrator:
    def test_generate_calls_all(self):
        from infrastructure.generators import generate
        with patch('infrastructure.generators.fda_perfiles.edit', return_value=b'a'):
            with patch('infrastructure.generators.as_is_to_be.edit', return_value=b'b'):
                with patch('infrastructure.generators.roadmap.edit', return_value=b'c'):
                    with patch('infrastructure.generators.consideraciones.edit', return_value=b'd'):
                        with patch('infrastructure.generators.cronograma_entregables.edit', return_value=b'e'):
                            with patch('infrastructure.generators.cronograma_preview.edit', return_value=b'f'):
                                with patch('infrastructure.generators.oferta_economica.edit', return_value=b'g'):
                                    result = generate(b'test', {}, {})
                                    assert result == b'g'


# ═══════════════════════════════════════════════════════════════════════════════
# core/config.py, core/database.py, domain entities
# ═══════════════════════════════════════════════════════════════════════════════

def test_config_properties():
    from core.config import settings
    assert settings.database_url is not None
    assert isinstance(settings.origins, list)


def test_database_base():
    from core.database import Base, engine
    assert Base is not None


def test_catalogo_entities():
    from domain.catalogo.entities import TorreOut, TorreCreate
    torre = TorreOut(id=1, nombre="Test", nombre_norm="TEST", activa=True)
    assert torre.nombre == "Test"
    create = TorreCreate(nombre="New")
    assert create.nombre == "New"


def test_cronograma_entities():
    from domain.cronograma.entities import GenerarCronogramaRequest, RolCronograma, ActividadCronograma
    req = GenerarCronogramaRequest(proyecto="Test", actividades=[], roles=[])
    assert req.proyecto == "Test"
    rol = RolCronograma(perfil="Dev", seniority="Sr", personas=2)
    assert rol.perfil == "Dev"
    act = ActividadCronograma(torre="A", horas=10)
    assert act.horas == 10


def test_propuesta_entities():
    from domain.propuesta.entities import GenerarPropuestaRequest, TorreInput
    req = GenerarPropuestaRequest(filial="corp")
    assert req.filial == "corp"
    torre = TorreInput(nombre="Backend", horas=100)
    assert torre.horas == 100


# ═══════════════════════════════════════════════════════════════════════════════
# domain/propuesta/service.py
# ═══════════════════════════════════════════════════════════════════════════════

def test_propuesta_invalid_filial():
    from domain.propuesta import service
    from domain.propuesta.entities import GenerarPropuestaRequest
    with pytest.raises(ValueError, match="Filial desconocida"):
        service.generar_propuesta(None, GenerarPropuestaRequest(filial="xyz"))


def test_propuesta_template_not_found(monkeypatch, tmp_path):
    from domain.propuesta import service
    from domain.propuesta.entities import GenerarPropuestaRequest
    from types import SimpleNamespace
    monkeypatch.setattr(service, "settings", SimpleNamespace(templates_path=tmp_path))
    monkeypatch.setattr(service, "build_catalog_data", lambda db: {})
    with pytest.raises(FileNotFoundError):
        service.generar_propuesta(None, GenerarPropuestaRequest(filial="corp"))


# ═══════════════════════════════════════════════════════════════════════════════
# domain/catalogo/service.py
# ═══════════════════════════════════════════════════════════════════════════════

def test_catalogo_list_torres():
    import domain.catalogo.service as svc
    from unittest.mock import patch, MagicMock
    mock_db = MagicMock()
    with patch.object(svc, 'repo') as mock_repo:
        mock_repo.get_torres.return_value = [MagicMock(id=1, nombre='Backend', nombre_norm='BACKEND', activa=True)]
        result = svc.list_torres(mock_db)
        assert len(result) == 1


def test_catalogo_create_torre():
    import domain.catalogo.service as svc
    from domain.catalogo.entities import TorreCreate
    from unittest.mock import patch, MagicMock
    mock_db = MagicMock()
    with patch.object(svc, 'repo') as mock_repo:
        mock_fake = MagicMock(id=1, nombre='New', nombre_norm='NEW', activa=True)
        mock_repo.create_torre.return_value = mock_fake
        result = svc.create_torre(mock_db, TorreCreate(nombre='New'))
        assert result is not None


# ═══════════════════════════════════════════════════════════════════════════════
# infrastructure/generators/consideraciones.py — only easy tests
# ═══════════════════════════════════════════════════════════════════════════════

def test_cons_norm():
    from infrastructure.generators.consideraciones import _norm
    assert _norm("  Hola  ") == "HOLA"
    assert _norm(None) == ""
    assert _norm("") == ""


def test_cons_calc_delta():
    from infrastructure.generators.consideraciones import _calc_delta
    assert _calc_delta("Corto") == 0
    assert _calc_delta("A" * 300) > 0


def test_cons_split_por_punto():
    from infrastructure.generators.consideraciones import _split_por_punto
    assert _split_por_punto("Oracion 1. Oracion 2.") == ["Oracion 1.", "Oracion 2."]


def test_cons_load_excel():
    from infrastructure.generators.consideraciones import _load_desde_excel
    assert _load_desde_excel([], "C", "F") == []


def test_cons_filial_nombres():
    from infrastructure.generators.consideraciones import FILIAL_NOMBRES
    assert 'corp' in FILIAL_NOMBRES
    assert 'group' in FILIAL_NOMBRES
    assert 'cbit' in FILIAL_NOMBRES


# ═══════════════════════════════════════════════════════════════════════════════
# infrastructure/repositories/catalogo_repository.py
# ═══════════════════════════════════════════════════════════════════════════════

def test_repo_norm():
    from infrastructure.repositories.catalogo_repository import _norm
    assert _norm("  Hola  ") == "HOLA"
    assert _norm(None) == ""


def test_repo_get_torre_by_norm():
    from infrastructure.repositories.catalogo_repository import get_torre_by_norm
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = "torre"
    assert get_torre_by_norm(mock_db, "A") == "torre"


def test_repo_update_torre():
    from infrastructure.repositories.catalogo_repository import update_torre
    mock_obj = MagicMock()
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = mock_obj
    result = update_torre(mock_db, 1, "New Name")
    assert result is not None
    assert mock_obj.nombre == "New Name"


def test_repo_update_torre_not_found():
    from infrastructure.repositories.catalogo_repository import update_torre
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = None
    assert update_torre(mock_db, 999, "X") is None


def test_repo_build_catalog_data():
    from infrastructure.repositories.catalogo_repository import build_catalog_data
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
    result = build_catalog_data(mock_db)
    assert "fda_db" in result


def test_repo_get_torres():
    from infrastructure.repositories import catalogo_repository as repo
    mock_db = MagicMock()
    q = MagicMock()
    mock_db.query.return_value = q
    q.filter.return_value = q
    q.order_by.return_value = q
    q.all.return_value = [MagicMock()]
    assert len(repo.get_torres(mock_db)) == 1


def test_repo_get_torres_all():
    from infrastructure.repositories import catalogo_repository as repo
    mock_db = MagicMock()
    q = MagicMock()
    mock_db.query.return_value = q
    q.filter.return_value = q
    q.order_by.return_value = q
    q.all.return_value = [MagicMock(), MagicMock()]
    assert len(repo.get_torres(mock_db, solo_activas=False)) == 2


def test_repo_get_perfiles():
    from infrastructure.repositories import catalogo_repository as repo
    mock_db = MagicMock()
    q = MagicMock()
    mock_db.query.return_value = q
    q.filter.return_value = q
    q.all.return_value = [MagicMock()]
    assert len(repo.get_perfiles(mock_db)) == 1


def test_repo_delete_torre():
    from infrastructure.repositories import catalogo_repository as repo
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = MagicMock()
    assert repo.delete_torre(mock_db, 1) is True


def test_repo_delete_torre_not_found():
    from infrastructure.repositories import catalogo_repository as repo
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = None
    assert repo.delete_torre(mock_db, 999) is False


def test_repo_update_consideracion():
    from infrastructure.repositories import catalogo_repository as repo
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = MagicMock()
    assert repo.update_consideracion(mock_db, 1, "text", 1) is not None


def test_repo_update_consideracion_not_found():
    from infrastructure.repositories import catalogo_repository as repo
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = None
    assert repo.update_consideracion(mock_db, 999, "text", 1) is None


# ═══════════════════════════════════════════════════════════════════════════════
# infrastructure/generators/cronograma_image.py
# ═══════════════════════════════════════════════════════════════════════════════

def test_image_hex():
    from infrastructure.generators.cronograma_image import _hex
    assert _hex("#FF0000") == (255, 0, 0)
    assert _hex("00FF00") == (0, 255, 0)


def test_image_fnt_default():
    from infrastructure.generators.cronograma_image import _fnt
    assert _fnt(["/nonexistent/font.ttf"], 12) is not None


def test_image_generate_raises():
    from infrastructure.generators.cronograma_image import generate_cronograma_image
    with pytest.raises(ValueError):
        generate_cronograma_image({})


def test_image_generate_mock():
    from infrastructure.generators.cronograma_image import generate_cronograma_image
    with patch('infrastructure.generators.cronograma_image._render') as mr:
        mr.return_value = b"fake-png"
        data = {'actividades': [{'torre': 'A', 'horas': 43, 'personas': 2}], 'roles': [{'perfil': 'Dev', 'personas': 2}]}
        result = generate_cronograma_image(data)
        assert result == b"fake-png"


# ═══════════════════════════════════════════════════════════════════════════════
# infrastructure/generators/cronograma_preview.py
# ═══════════════════════════════════════════════════════════════════════════════

def test_preview_png_aspect():
    from infrastructure.generators.cronograma_preview import _png_aspect
    assert _png_aspect(b"not png") == 3.1


def test_preview_next_img_id():
    from infrastructure.generators.cronograma_preview import _next_img_id
    assert _next_img_id({'ppt/media/image1.png': b''}) == 2
    assert _next_img_id({}) == 1


def test_preview_register_ct_exists():
    from infrastructure.generators.cronograma_preview import _register_ct
    files = {'[Content_Types].xml': b'<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="png" ContentType="image/png"/></Types>'}
    _register_ct(files)
    assert b'image/png' in files['[Content_Types].xml']


# ═══════════════════════════════════════════════════════════════════════════════
# infrastructure/generators/cronograma_excel.py
# ═══════════════════════════════════════════════════════════════════════════════

def test_excel_normalizar_roles():
    from infrastructure.generators.cronograma_excel import _normalizar_roles
    assert _normalizar_roles([]) == []
    assert len(_normalizar_roles([{'perfil': 'Dev', 'personas': 1}])) == 1


def test_excel_x_to_col():
    from infrastructure.generators.cronograma_excel import _x_to_col
    assert _x_to_col(0) == (0, 0)