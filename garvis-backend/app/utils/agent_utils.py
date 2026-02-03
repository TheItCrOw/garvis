import app.constants.agentic_assistant_constants as agent_constants
import duckdb
import re

def sanitize_sql(sql: str) -> str:

    _SQL_DISALLOWED = re.compile(agent_constants.DISALLOWED_SQL,re.IGNORECASE)

    sql = (sql or "").strip().strip("`")
    sql = re.sub(r"^```(sql)?\s*|\s*```$", "", sql, flags=re.IGNORECASE).strip()

    # block multi-statements
    if ";" in sql:
        raise ValueError("Only a single SQL statement is allowed (no semicolons).")

    if _SQL_DISALLOWED.search(sql):
        raise ValueError("Only read-only queries are allowed (SELECT / WITH).")

    if not re.match(r"^(SELECT|WITH)\b", sql, flags=re.IGNORECASE):
        raise ValueError("Query must start with SELECT or WITH.")

    # keep results manageable
    if not re.search(r"\bLIMIT\b", sql, flags=re.IGNORECASE):
        sql = f"{sql}\nLIMIT 200"
    return sql

def schema_markdown(conn: duckdb.DuckDBPyConnection) -> str:
    tables = [r[0] for r in conn.execute("SHOW TABLES").fetchall()]
    if not tables:
        return "(no tables found)"
    out = []
    for t in tables:
        cols = conn.execute(f"DESCRIBE {t}").fetchall()
        out.append(f"### {t}")
        for c in cols:
            out.append(f"- {c[0]}: {c[1]}")
        out.append("")
    return "\n".join(out).strip()