@echo off
set PYTHONPATH=%cd%
python -m pytest --cov=. --cov-report=term-missing --cov-report=xml:coverage.xml