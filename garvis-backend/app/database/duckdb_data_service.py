import duckdb
import os
from contextlib import contextmanager
from typing import Generator


class DataService:
    def __init__(self, db_path: str = "./data/garvis.duckdb") -> None:
        self.db_path: str = db_path

        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"DuckDB file not found: {self.db_path}")

        print(f"Using DuckDB database at: {self.db_path}")
        with self.connection() as con:
            con.execute("SELECT 1").fetchone()

    @contextmanager
    def connection(self) -> Generator[duckdb.DuckDBPyConnection, None, None]:
        """
        Create a new connection per usage, safe for web servers and concurrent requests.
        """
        con: duckdb.DuckDBPyConnection = duckdb.connect(self.db_path, read_only=False)
        try:
            yield con
        finally:
            con.close()

    def count_patients(self) -> int:
        with self.connection() as con:
            return con.execute(
                """
                SELECT COUNT(*) FROM patient
            """
            ).fetchone()[0]