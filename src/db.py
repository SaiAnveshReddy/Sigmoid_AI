"""
Shared DuckDB connection helper.
"""
from __future__ import annotations

import duckdb


def get_connection(database_path: str) -> duckdb.DuckDBPyConnection:
    """Return a DuckDB connection to the given database path."""
    return duckdb.connect(database_path)
