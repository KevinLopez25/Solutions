import re
import subprocess
import sys
from pathlib import Path

from fastapi import APIRouter

router = APIRouter(prefix="/quality", tags=["quality"])

_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent.parent

_EXCLUDE = [
    '--ignore=tests/test_quality_router.py',
    '--ignore=tests/test_integration.py',
    '--ignore=tests/test_performance.py',
    '--ignore=tests/test_load.py',
    '--ignore=tests/test_stress.py',
    '--ignore=tests/test_e2e.py',
    '--ignore=tests/test_slow.py',
    '--ignore=tests/test_system.py',
]


def _parse_coverage(stdout: str) -> list:
    lines = stdout.splitlines()
    coverage = []
    start = None
    for i, line in enumerate(lines):
        if line.strip().startswith('Name') and 'Stmts' in line and 'Cover' in line:
            start = i + 1
            break
    if start is None:
        return coverage
    for row in lines[start:]:
        if not row.strip():
            continue
        if row.strip().startswith('TOTAL'):
            parts = row.split()
            try:
                coverage.append({'file': parts[0], 'stmts': int(parts[1]), 'miss': int(parts[2]), 'cover': parts[3]})
            except Exception:
                pass
            break
        parts = row.split()
        if len(parts) >= 4 and parts[-2].endswith('%'):
            try:
                coverage.append({
                    'file': ' '.join(parts[:-4]),
                    'stmts': int(parts[-4]),
                    'miss':  int(parts[-3]),
                    'cover': parts[-2],
                })
            except Exception:
                continue
    return coverage


@router.post('/run-tests')
def run_tests():
    cmd = [
        sys.executable, '-m', 'pytest', '-q', '--disable-warnings', '--no-cov',
        '--tb=short', '--timeout=30',
    ] + _EXCLUDE
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=90, cwd=str(_BACKEND_DIR)
        )
    except subprocess.TimeoutExpired as exc:
        return {'success': False, 'stdout': '', 'stderr': f'Timeout: {exc}', 'tests_summary': None, 'coverage': []}
    except Exception as exc:
        return {'success': False, 'stdout': '', 'stderr': f'Error: {exc}', 'tests_summary': None, 'coverage': []}

    stdout = proc.stdout or ''
    stderr = proc.stderr or ''
    if proc.returncode != 0 and not stdout and not stderr:
        stderr = f'pytest exited with code {proc.returncode} (no output)'

    summary = None
    for line in reversed(stdout.splitlines()):
        if re.search(r'\b(passed|failed|skipped)\b', line):
            summary = line
            break

    return {
        'success': proc.returncode == 0,
        'stdout': stdout,
        'stderr': stderr,
        'tests_summary': summary,
        'coverage': [],
    }
