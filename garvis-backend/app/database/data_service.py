"""A duckdb database where we keep all data in RAM for the whole lifetime."""

import duckdb
import os
from contextlib import contextmanager
from typing import Generator, Optional, Type


class DataService:
    _instance: Optional['DataService'] = None
    _db_path: Optional[str] = None
    _initialized: bool = False

    @classmethod
    def initialize(cls: Type['DataService'], db_path: str = "./data/garvis.duckdb") -> 'DataService':
        """Initialize the singleton instance with a database path."""
        if cls._instance is None:
            cls._instance = cls()
            cls._db_path = db_path

            if not os.path.exists(cls._db_path):
                raise FileNotFoundError(f"DuckDB file not found: {cls._db_path}")

            print(f"Using DuckDB database at: {cls._db_path}")
            with cls.connection() as con:
                con.execute("SELECT 1").fetchone()
            
            cls._initialized = True
        return cls._instance

    @classmethod
    @contextmanager
    def connection(cls: Type['DataService']) -> Generator[duckdb.DuckDBPyConnection, None, None]:
        """
        Create a new connection per usage, safe for web servers and concurrent requests.
        """
        con: duckdb.DuckDBPyConnection = duckdb.connect(cls._db_path, read_only=False)
        try:
            yield con
        finally:
            con.close()

    @classmethod
    def count_patients(cls: Type['DataService']) -> int:
        if not cls._initialized:
            raise RuntimeError("DataService not initialized. Call DataService.initialize() first.")
        with cls.connection() as con:
            return con.execute(
                """
                SELECT COUNT(*) FROM patient
            """
            ).fetchone()[0]