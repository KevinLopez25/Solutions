from fastapi import APIRouter
import subprocess
import re

router = APIRouter(prefix="/api/v1/quality", tags=["quality"])


def parse_coverage_from_output(stdout: str):
    lines = stdout.splitlines()
    coverage = []
    # Find header line
    start = None
    for i, l in enumerate(lines):
        if l.strip().startswith('Name') and 'Stmts' in l and 'Miss' in l and 'Cover' in l:
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
        # expect: name stmts miss cover% [missing]
        if len(parts) >= 4 and parts[-2].endswith('%'):
            cover = parts[-2]
            miss = parts[-3]
            stmts = parts[-4]
            name = ' '.join(parts[:-4])
            try:
                coverage.append({'file': name, 'stmts': int(stmts), 'miss': int(miss), 'cover': cover})
            except Exception:
                continue
    return coverage


@router.post('/run-tests')
def run_tests():
    """Run pytest on the server and return stdout, stderr and a parsed coverage table.

    Note: running tests on-demand can be expensive; this endpoint is intended
    for local/dev use. Consider adding auth/limits for production.
    """
    import os
    from pathlib import Path

    # Get the backend directory (parent of the api directory)
    backend_dir = Path(__file__).resolve().parent.parent.parent.parent

    cmd = ["python", "-m", "pytest", "-q", "--disable-warnings", "--cov=.", "--cov-report=term-missing"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300, cwd=str(backend_dir))
    except subprocess.TimeoutExpired as e:
        return {"success": False, "stdout": "", "stderr": f"Timeout: {e}", "tests_summary": None, "coverage": []}
    except Exception as e:
        return {"success": False, "stdout": "", "stderr": f"Error: {str(e)}", "tests_summary": None, "coverage": []}

    stdout = proc.stdout or ""
    stderr = proc.stderr or ""

    # Log for debugging
    if proc.returncode != 0 and not stdout and not stderr:
        stderr = f"pytest exited with code {proc.returncode} (no output captured)"

    # find tests summary (e.g., '54 passed, 2 warnings in 2.87s')
    tests_summary = None
    for l in reversed(stdout.splitlines()):
        if re.search(r'\b(passed|failed|skipped)\b', l):
            tests_summary = l
            break

    coverage = parse_coverage_from_output(stdout)

    return {
        "success": proc.returncode == 0,
        "stdout": stdout,
        "stderr": stderr,
        "tests_summary": tests_summary,
        "coverage": coverage,
    }
