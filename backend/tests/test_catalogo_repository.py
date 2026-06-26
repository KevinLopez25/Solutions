"""
Tests para infrastructure/repositories/catalogo_repository.py
"""
import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session

from infrastructure.repositories import catalogo_repository as repo


class TestNorm:
    def test_norm_basic(self):
        assert repo._norm("  Hola Mundo  ") == "HOLA MUNDO"

    def test_norm_with_accents(self):
        assert repo._norm("Torre de Desarrollo") == "TORRE DE DESARROLLO"

    def test_norm_empty(self):
        assert repo._norm("") == ""
        assert repo._norm(None) == ""


class TestGetTorres:
    def test_get_torres_returns_all_active(self):
        mock_db = MagicMock(spec=Session)
        mock_query = mock_db.query.return_value
        mock_filtered = mock_query.filter.return_value
        mock_filtered.order_by.return_value.all.return_value = ["t1", "t2"]

        result = repo.get_torres(mock_db, solo_activas=True)
        assert result == ["t1", "t2"]
        mock_db.query.assert_called_once()

    def test_get_torres_includes_inactive(self):
        mock_db = MagicMock(spec=Session)
        mock_query = mock_db.query.return_value
        mock_query.order_by.return_value.all.return_value = ["t1"]

        result = repo.get_torres(mock_db, solo_activas=False)
        assert result == ["t1"]


class TestGetTorreById:
    def test_found(self):
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = "torre_obj"
        assert repo.get_torre_by_id(mock_db, 1) == "torre_obj"

    def test_not_found(self):
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        assert repo.get_torre_by_id(mock_db, 999) is None


class TestCreateTorre:
    def test_creates_and_commits(self):
        mock_db = MagicMock()
        result = repo.create_torre(mock_db, "Mi Torre")
        assert result is not None
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()


class TestUpdateTorre:
    def test_updates_existing(self):
        mock_obj = MagicMock()
        mock_obj.nombre = "Old"
        mock_obj.nombre_norm = "OLD"
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_obj

        result = repo.update_torre(mock_db, 1, "New Name")
        assert result is not None
        assert mock_obj.nombre == "New Name"
        mock_db.commit.assert_called_once()

    def test_update_not_found(self):
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        assert repo.update_torre(mock_db, 999, "X") is None


class TestDeleteTorre:
    def test_delete_existing(self):
        mock_obj = MagicMock()
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_obj
        assert repo.delete_torre(mock_db, 1) is True
        mock_db.delete.assert_called_once_with(mock_obj)
        mock_db.commit.assert_called_once()

    def test_delete_not_found(self):
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        assert repo.delete_torre(mock_db, 999) is False


class TestGetPerfiles:
    def test_get_all(self):
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.all.return_value = ["p1", "p2"]
        result = repo.get_perfiles(mock_db)
        assert result == ["p1", "p2"]

    def test_get_by_torre(self):
        mock_db = MagicMock()
        mock_q = mock_db.query.return_value
        mock_q.filter.return_value.filter.return_value.all.return_value = ["p1"]
        result = repo.get_perfiles(mock_db, torre_id=5)
        assert result == ["p1"]


class TestCreatePerfil:
    def test_creates_and_commits(self):
        mock_db = MagicMock()
        result = repo.create_perfil(mock_db, 1, "Dev", "Desc")
        assert result is not None
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()


class TestUpdatePerfil:
    def test_update_existing(self):
        mock_obj = MagicMock()
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_obj
        result = repo.update_perfil(mock_db, 1, "New Rol", "New Desc")
        assert result is not None
        assert mock_obj.rol == "New Rol"
        assert mock_obj.descripcion == "New Desc"
        mock_db.commit.assert_called_once()

    def test_update_not_found(self):
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        assert repo.update_perfil(mock_db, 999, "X", "Y") is None


class TestDeletePerfil:
    def test_delete_existing(self):
        mock_obj = MagicMock()
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_obj
        assert repo.delete_perfil(mock_db, 1) is True
        mock_db.delete.assert_called_once()

    def test_delete_not_found(self):
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        assert repo.delete_perfil(mock_db, 999) is False


class TestConsideraciones:
    def test_get_consideraciones_all(self):
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = ["c1"]
        assert repo.get_consideraciones(mock_db) == ["c1"]

    def test_get_consideraciones_by_torre(self):
        mock_db = MagicMock()
        mock_q = mock_db.query.return_value
        mock_q.filter.return_value.filter.return_value.order_by.return_value.all.return_value = ["c1"]
        assert repo.get_consideraciones(mock_db, torre_id=1) == ["c1"]

    def test_create_consideracion(self):
        mock_db = MagicMock()
        result = repo.create_consideracion(mock_db, "Texto", 1, True, 0)
        assert result is not None
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_update_consideracion(self):
        mock_obj = MagicMock()
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_obj
        result = repo.update_consideracion(mock_db, 1, "Nuevo texto", 5)
        assert result is not None
        assert mock_obj.texto == "Nuevo texto"
        assert mock_obj.orden == 5

    def test_update_consideracion_not_found(self):
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        assert repo.update_consideracion(mock_db, 999, "X", 0) is None

    def test_delete_consideracion(self):
        mock_obj = MagicMock()
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_obj
        assert repo.delete_consideracion(mock_db, 1) is True
        mock_db.delete.assert_called_once()

    def test_delete_consideracion_not_found(self):
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        assert repo.delete_consideracion(mock_db, 999) is False


class TestEntregables:
    def test_get_entregables(self):
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = ["e1"]
        assert repo.get_entregables(mock_db) == ["e1"]

    def test_get_entregables_by_torre(self):
        mock_db = MagicMock()
        mock_q = mock_db.query.return_value
        mock_q.filter.return_value.filter.return_value.order_by.return_value.all.return_value = ["e1"]
        assert repo.get_entregables(mock_db, torre_id=1) == ["e1"]

    def test_create_entregable(self):
        mock_db = MagicMock()
        result = repo.create_entregable(mock_db, 1, "Item", 0)
        assert result is not None
        mock_db.add.assert_called_once()

    def test_update_entregable(self):
        mock_obj = MagicMock()
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_obj
        result = repo.update_entregable(mock_db, 1, "New Item", 3)
        assert result is not None
        assert mock_obj.item == "New Item"
        assert mock_obj.orden == 3

    def test_update_entregable_not_found(self):
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        assert repo.update_entregable(mock_db, 999, "X", 0) is None

    def test_delete_entregable(self):
        mock_obj = MagicMock()
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_obj
        assert repo.delete_entregable(mock_db, 1) is True

    def test_delete_entregable_not_found(self):
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        assert repo.delete_entregable(mock_db, 999) is False


class TestFueraAlcance:
    def test_get_fuera_alcance(self):
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = ["f1"]
        assert repo.get_fuera_alcance(mock_db) == ["f1"]

    def test_create_fuera_alcance(self):
        mock_db = MagicMock()
        result = repo.create_fuera_alcance(mock_db, 1, "Item", 0)
        assert result is not None
        mock_db.add.assert_called_once()

    def test_update_fuera_alcance(self):
        mock_obj = MagicMock()
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_obj
        result = repo.update_fuera_alcance(mock_db, 1, "New", 2)
        assert result is not None
        assert mock_obj.item == "New"

    def test_update_fuera_alcance_not_found(self):
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        assert repo.update_fuera_alcance(mock_db, 999, "X", 0) is None

    def test_delete_fuera_alcance(self):
        mock_obj = MagicMock()
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_obj
        assert repo.delete_fuera_alcance(mock_db, 1) is True

    def test_delete_fuera_alcance_not_found(self):
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        assert repo.delete_fuera_alcance(mock_db, 999) is False


class TestBuildCatalogData:
    def test_build_catalog_data_empty(self):
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
        result = repo.build_catalog_data(mock_db)
        assert result == {
            "fda_db": {},
            "perf_db": {},
            "consideraciones_db": {},
            "entregables_db": [],
        }

    def test_build_catalog_data_with_data(self):
        mock_db = MagicMock()

        # Mock torres
        torre1 = MagicMock()
        torre1.id = 1
        torre1.nombre = "Torre Backend"
        torre1.nombre_norm = "TORRE BACKEND"

        # Mock get_torres
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [torre1]

        # Mock get_fuera_alcance
        fda1 = MagicMock()
        fda1.torre_id = 1
        fda1.item = "No incluye X"
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.side_effect = [
            [torre1],  # torres
            [fda1],    # fda
            [],        # perfiles
            [],        # consideraciones
            [],        # entregables
        ]

        result = repo.build_catalog_data(mock_db)
        assert "fda_db" in result