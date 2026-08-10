import re
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient

from api.v1.quality.router import parse_coverage_from_output, router
from api.v1.router import api_router
from fastapi import FastAPI
from tests.conftest import db_session


SAMPLE_COVERAGE = """\
Name                                                  Stmts   Miss  Cover   Missing
-----------------------------------------------------------------------------------
backend/main.py                                        44     44     0%   1-70
domain/ai/service.py                                  391    353    10%   94-230
infrastructure/generators/roadmap.py                  101     79    22%   20-25
-----------------------------------------------------------------------------------
TOTAL                                                4252   2408    43%
"""


def _build_app():
    application = FastAPI(lifespan=None)
    application.include_router(api_router)
    application.include_router(router)
    return application


def _build_client(app):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides.clear()
    from core.dependencies import get_db
    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def test_parse_coverage_from_output_basic():
    rows = parse_coverage_from_output(SAMPLE_COVERAGE)
    files = {row["file"]: row for row in rows}

    assert "backend/main.py" in files
    assert files["backend/main.py"]["stmts"] == 44
    assert files["backend/main.py"]["miss"] == 44
    assert files["backend/main.py"]["cover"] == "0%"
    assert files["domain/ai/service.py"]["stmts"] == 391
    assert files["domain/ai/service.py"]["cover"] == "10%"


def test_parse_coverage_from_output_missing_header():
    rows = parse_coverage_from_output("no header here\n")
    assert rows == []


def test_parse_coverage_from_output_totals():
    rows = parse_coverage_from_output(SAMPLE_COVERAGE)
    last = rows[-1]
    assert last["file"] == "TOTAL"
    assert last["stmts"] == 4252
    assert last["miss"] == 2408
    assert last["cover"] == "43%"


def test_run_tests_endpoint_returns_json_shape():
    mock_result = MagicMock()
    mock_result.stdout = SAMPLE_COVERAGE
    mock_result.stderr = ""
    mock_result.returncode = 0

    with patch("api.v1.quality.router.subprocess.run", return_value=mock_result):
        app = _build_app()
        client = _build_client(app)

        response = client.post("/api/v1/quality/run-tests")

        assert response.status_code == 200
        body = response.json()
        assert "success" in body
        assert "tests_summary" in body
        assert "coverage" in body
        assert isinstance(body["coverage"], list)
