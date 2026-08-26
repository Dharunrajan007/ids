"""Root conftest: pytest inserts this file's directory (the project root)
into sys.path, which makes the `src` package importable no matter how the
test run is invoked (`pytest` or `python -m pytest`). No fixtures here —
shared fixtures live in tests/.
"""
