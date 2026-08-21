from infrastructure.generators.cronograma_excel import (
    _build_drawing,
    _pill_extra_columns,
)


def test_role_pills_expand_without_truncating_labels():
    roles = [
        {
            "perfil": "Consultor SAP C4C",
            "seniority": "SENIOR",
            "personas": 1,
        },
        {
            "perfil": "Gerente de Proyecto SAP",
            "seniority": "MANAGER",
            "personas": 1,
        },
    ]
    meta = {
        "fecha": "",
        "total_horas": 0,
        "duracion_meses": 0,
        "nombre_proyecto": "",
        "torre": "",
        "id_proyecto": "",
        "ROW_HDR_START": 2,
    }

    drawing = _build_drawing([], roles, 7, meta, sin_semanas=False)

    assert "Consultor SAP C4C" in drawing
    assert "Gerente de Proyecto SAP" in drawing
    assert "…" not in drawing
    assert _pill_extra_columns(roles, 7) > 0
