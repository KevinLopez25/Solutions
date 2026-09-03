from infrastructure.generators.cronograma_excel import (
    BARRA_COLORES,
    ROLE_COLORS,
    _build_drawing,
    _pill_extra_columns,
    _calcular_semanas,
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
    assert _pill_extra_columns(roles, 7) == 0


def test_cronograma_colors_are_green_and_do_not_repeat_consecutively():
    colors = BARRA_COLORES + ROLE_COLORS

    assert all(color in {
        "166534", "15803D", "16A34A", "22C55E", "059669", "047857",
    } for color in colors)
    assert all(first != second for first, second in zip(BARRA_COLORES, BARRA_COLORES[1:]))
    assert all(first != second for first, second in zip(ROLE_COLORS, ROLE_COLORS[1:]))


def test_project_card_uses_project_name_and_sprint_zero_matches_normal_width():
    meta = {
        "fecha": "",
        "total_horas": 0,
        "duracion_meses": 0,
        "nombre_proyecto": "Proyecto SAP",
        "torre": "",
        "id_proyecto": "",
        "ROW_HDR_START": 1,
    }

    drawing = _build_drawing([], [], 4, meta, sin_semanas=False)

    assert "Proyecto SAP" in drawing
    assert "INFORMACIÓN DEL PROYECTO" not in drawing
    assert '<xdr:col>1</xdr:col><xdr:colOff>38100</xdr:colOff>' in drawing
    assert '<xdr:col>1</xdr:col><xdr:colOff>876300</xdr:colOff>' in drawing


def test_profile_label_is_used_when_present():
    meta = {
        "fecha": "",
        "total_horas": 0,
        "duracion_meses": 0,
        "nombre_proyecto": "",
        "torre": "",
        "id_proyecto": "",
        "ROW_HDR_START": 1,
    }

    drawing = _build_drawing(
        [{"torre": "Backend", "etiqueta": "Desarrollador Java", "semanas": 1}],
        [],
        1,
        meta,
        sin_semanas=False,
    )

    assert "Desarrollador Java" in drawing


def test_activity_name_is_used_as_profile_label_when_etiqueta_is_missing():
    meta = {
        "fecha": "",
        "total_horas": 0,
        "duracion_meses": 0,
        "nombre_proyecto": "",
        "torre": "",
        "id_proyecto": "",
        "ROW_HDR_START": 1,
    }

    drawing = _build_drawing(
        [{"torre": "Data", "actividad": "Analista de Datos", "semanas": 1}],
        [],
        1,
        meta,
        sin_semanas=False,
    )

    assert "Analista de Datos" in drawing


def test_profile_duration_divides_weekly_hours_then_people():
    assert _calcular_semanas(516, 42, 2) == 7


def test_multiple_profile_activities_remain_multiple_rows():
    meta = {
        "fecha": "",
        "total_horas": 0,
        "duracion_meses": 0,
        "nombre_proyecto": "",
        "torre": "",
        "id_proyecto": "",
        "ROW_HDR_START": 1,
    }

    drawing = _build_drawing(
        [
            {"torre": "Data", "etiqueta": "Analista de Datos", "semanas": 1},
            {"torre": "Data", "etiqueta": "Arquitecto de Datos", "semanas": 1},
        ],
        [],
        1,
        meta,
        sin_semanas=False,
    )

    assert drawing.count("Analista de Datos") == 1
    assert drawing.count("Arquitecto de Datos") == 1
