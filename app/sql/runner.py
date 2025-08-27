import os, re, sqlite3, pandas as pd
from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.getenv("DB_PATH", "data/rounds.db")
ALLOWED_TABLES = {"app_metrics"}
BLOCKED = re.compile(r";|--|/\*|\*/", re.IGNORECASE)

# Keep comments/multi-statements blocked, but allow ONE trailing semicolon
def _sanitize(sql: str) -> str:
    if not isinstance(sql, str) or not sql.strip():
        raise ValueError("Empty SQL")
    sql = sql.strip()
    # allow a single trailing semicolon
    if sql.endswith(";"):
        sql = sql[:-1].strip()

    # block any remaining semicolons or SQL comments
    if ";" in sql or "--" in sql or "/*" in sql or "*/" in sql:
        raise ValueError("Unsafe SQL detected")

    # (simple allowlist placeholder – we only use app_metrics in this demo)
    # You can expand this if you add more tables later.
    return sql

def run_sql(sql: str) -> pd.DataFrame:
    sql = _sanitize(sql)
    con = sqlite3.connect(DB_PATH)
    try:
        df = pd.read_sql_query(sql, con)
    finally:
        con.close()
    return df