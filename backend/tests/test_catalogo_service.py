from domain.catalogo import service
from domain.catalogo.entities import TorreCreate


def test_create_and_list_torres(db_session):
    torre = service.create_torre(db_session, TorreCreate(nombre="Test Torre"))

    assert torre.id is not None
    assert torre.nombre == "Test Torre"
    assert len(service.list_torres(db_session)) == 1
    assert service.list_torres(db_session)[0].nombre == "Test Torre"


def test_delete_torre(db_session):
    torre = service.create_torre(db_session, TorreCreate(nombre="Eliminar Torre"))

    assert service.delete_torre(db_session, torre.id) is True
    assert all(t.id != torre.id for t in service.list_torres(db_session))
