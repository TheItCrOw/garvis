import app.constants.agentic_assistant_constants as agent_constants
import duckdb
import re
import hashlib
from langchain_core.callbacks import BaseCallbackHandler

class AssertImageSent(BaseCallbackHandler):
    def __init__(self, *, raise_if_missing: bool = True):
        self.raise_if_missing = raise_if_missing

    def on_chat_model_start(self, serialized, messages, **kwargs):
        found = False
        for batch in messages:
            #only get the very last message and detect if there is a passed image
            for msg in batch[-1:]:
                for url in iter_image_urls(getattr(msg, "content", None)):
                    if isinstance(url, str) and "base64," in url:
                        b64 = url.split("base64,", 1)[1]
                        h = hashlib.sha256(b64.encode("utf-8")).hexdigest()[:12]
                        print(f"[probe] image data url detected, sha256[:12]={h}, b64_len={len(b64)}")
                        found = True

        if self.raise_if_missing and not found:
            raise RuntimeError("No base64 image block found in LLM input messages.")

def iter_image_urls(content):
    if isinstance(content, list):
        for part in content:
            if not isinstance(part, dict):
                continue
            t = part.get("type")
            if t in ("image_url", "input_image"):
                image_url = part.get("image_url")
                if isinstance(image_url, dict):
                    yield image_url.get("url")
                elif isinstance(image_url, str):
                    yield image_url


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