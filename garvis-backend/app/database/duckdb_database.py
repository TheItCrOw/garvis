"""A duckdb database where we keep all data in RAM for the whole lifetime."""

import duckdb
import pandas as pd
import os
from contextlib import contextmanager


class DataService:
    def __init__(self, db_path="./data/garvis.duckdb"):
        self.db_path = db_path

        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"DuckDB file not found: {self.db_path}")

        print(f"Using DuckDB database at: {self.db_path}")
        with self.connection() as con:
            con.execute("SELECT 1").fetchone()

    @contextmanager
    def connection(self):
        """
        Create a new connection per usage, save for web servers and concurrent requests.
        """
        con = duckdb.connect(self.db_path, read_only=False)
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
