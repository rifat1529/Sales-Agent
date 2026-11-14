import json
import re
import sqlite3
import secrets
from datetime import datetime, timezone
from pathlib import Path
from .config import (DB_PATH, MAX_ROWS, OLLAMA_URL, SQL_MODEL, REQUEST_TIMEOUT,
                     TEMPERATURE, TOP_P, TOP_K, DB_PRINCIPAL, AUDIT_LOG_PATH, DB_ACCESS_PASSWORD)
import requests

def _readonly_connection(db_path):
    """Open SQLite in read-only mode. SQLite itself has no user/password accounts."""
    db_uri = f"file:{Path(db_path).resolve().as_posix()}?mode=ro"
    con = sqlite3.connect(db_uri, uri=True)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA query_only = ON")
    con.execute("PRAGMA trusted_schema = OFF")
    return con

def _write_audit(sql, status, rows_returned=0, error=None, db_path=DB_PATH):
    """Append an audit record outside the read-only database file."""
    record = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "database": str(Path(db_path).resolve()),
        "principal": DB_PRINCIPAL,
        "connection_mode": "read-only",
        "operation": "SELECT" if _is_read_only_select(sql)[0] else "REJECTED",
        "sql": sql,
        "status": status,
        "rows_returned": rows_returned,
        "error": error,
    }
    AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with AUDIT_LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")

def _check_database_password(db_password=None, require_auth=False):
    """Validate the app-level password gate before a protected SQLite connection."""
    if not require_auth:
        return True, None
    if not DB_ACCESS_PASSWORD:
        return False, "Database password is not configured. Set DB_ACCESS_PASSWORD in the .env file."
    if not isinstance(db_password, str) or not secrets.compare_digest(db_password, DB_ACCESS_PASSWORD):
        return False, "Database authentication failed: incorrect password"
    return True, None


def schema_lookup(db_password=None, require_auth=False):
    """Return the live SQLite schema using a read-only connection."""
    allowed, auth_error = _check_database_password(db_password, require_auth)
    if not allowed:
        raise PermissionError(auth_error)
    con = _readonly_connection(DB_PATH)
    try:
        rows = con.execute("""
            SELECT name, sql FROM sqlite_master
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """).fetchall()
        return "\n\n".join(f"{row['name']}:\n{row['sql']}" for row in rows)
    finally:
        con.close()

def _ollama_chat(messages, model=SQL_MODEL, json_mode=False, sampling_options=None):
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": sampling_options or {
            "temperature": TEMPERATURE,
            "top_p": TOP_P,
            "top_k": TOP_K,
        },
    }
    if json_mode:
        payload["format"] = "json"
    response = requests.post(
        f"{OLLAMA_URL}/api/chat", json=payload, timeout=REQUEST_TIMEOUT
    )
    response.raise_for_status()
    data = response.json()
    return data["message"]["content"], data.get("prompt_eval_count", 0) + data.get("eval_count", 0)

def generate_sql(question, schema=None, sampling_options=None):
    """Ask a local Ollama model to translate one question into a single read-only SQL SELECT."""
    schema = schema or schema_lookup()
    messages = [
        {"role": "system", "content": (
            "You are a careful SQLite SQL generator. Return JSON only with exactly one key: sql. "
            "The value must be one SQLite SELECT query. Never write INSERT, UPDATE, DELETE, DROP, "
            "ALTER, CREATE, PRAGMA, ATTACH, or multiple statements. Use only tables and columns "
            "in the schema. Do not calculate or invent result values. Use joins when needed. "
            "For revenue use quantity * unit_price * (1 - discount_pct / 100.0). "
            "Apply order status filters only when the question explicitly asks about a status. "
            "Never add unrelated WHERE conditions. For simple counts, count all records "
            "unless the user specifies a filter."
        )},
        {"role": "user", "content": f"Schema:\n{schema}\n\nQuestion: {question}\nReturn JSON: {{\"sql\":\"SELECT ...\"}}"}
    ]
    content, tokens = _ollama_chat(messages, json_mode=True, sampling_options=sampling_options)
    try:
        parsed = json.loads(content)
        sql = parsed["sql"]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise ValueError(f"SQL generator returned invalid JSON: {content[:500]}") from exc
    if not isinstance(sql, str) or not sql.strip():
        raise ValueError("SQL generator returned an empty SQL query")
    return {"sql": sql.strip(), "tokens": tokens}

def _is_read_only_select(sql):
    if not isinstance(sql, str) or not sql.strip():
        return False, "SQL query is empty"
    cleaned = sql.strip()
    # One optional trailing semicolon is accepted; internal semicolons are rejected.
    if cleaned.endswith(";"):
        cleaned = cleaned[:-1].rstrip()
    if ";" in cleaned:
        return False, "Multiple SQL statements are not allowed"
    first = re.match(r"^\s*([A-Za-z]+)", cleaned)
    if not first or first.group(1).upper() not in {"SELECT", "WITH"}:
        return False, "Only SELECT queries (including read-only WITH queries) are allowed"
    return True, cleaned

def execute_sql(sql, db_path=DB_PATH, row_limit=MAX_ROWS, db_password=None, require_auth=False):
    """Execute exactly one read-only SELECT and write a separate audit record."""
    # SQLite has no native users/passwords. This optional application-level gate
    # checks the secret configured outside the source code before opening the DB.
    allowed, auth_error = _check_database_password(db_password, require_auth)
    if not allowed:
        audit_status = "AUTH_CONFIG_ERROR" if not DB_ACCESS_PASSWORD else "AUTH_FAILED"
        _write_audit(sql, audit_status, error=auth_error, db_path=db_path)
        return {"ok": False, "error": auth_error, "rows": [],
                "database_principal": DB_PRINCIPAL, "connection_mode": "read-only"}

    valid, result = _is_read_only_select(sql)
    if not valid:
        response = {"ok": False, "error": result, "rows": [],
                    "database_principal": DB_PRINCIPAL, "connection_mode": "read-only"}
        _write_audit(sql, "REJECTED", error=result, db_path=db_path)
        return response
    if not isinstance(row_limit, int) or row_limit < 1:
        error = "row_limit must be a positive integer"
        _write_audit(sql, "REJECTED", error=error, db_path=db_path)
        return {"ok": False, "error": error, "rows": [],
                "database_principal": DB_PRINCIPAL, "connection_mode": "read-only"}

    query = result
    con = None
    try:
        con = _readonly_connection(db_path)
        denied = {
            sqlite3.SQLITE_INSERT, sqlite3.SQLITE_UPDATE, sqlite3.SQLITE_DELETE,
            sqlite3.SQLITE_CREATE_INDEX, sqlite3.SQLITE_CREATE_TABLE,
            sqlite3.SQLITE_CREATE_TEMP_INDEX, sqlite3.SQLITE_CREATE_TEMP_TABLE,
            sqlite3.SQLITE_CREATE_TEMP_TRIGGER, sqlite3.SQLITE_CREATE_TEMP_VIEW,
            sqlite3.SQLITE_CREATE_TRIGGER, sqlite3.SQLITE_CREATE_VIEW,
            sqlite3.SQLITE_DROP_INDEX, sqlite3.SQLITE_DROP_TABLE,
            sqlite3.SQLITE_DROP_TEMP_INDEX, sqlite3.SQLITE_DROP_TEMP_TABLE,
            sqlite3.SQLITE_DROP_TEMP_TRIGGER, sqlite3.SQLITE_DROP_TEMP_VIEW,
            sqlite3.SQLITE_DROP_TRIGGER, sqlite3.SQLITE_DROP_VIEW,
            sqlite3.SQLITE_ALTER_TABLE, sqlite3.SQLITE_ATTACH, sqlite3.SQLITE_DETACH,
            sqlite3.SQLITE_PRAGMA, sqlite3.SQLITE_TRANSACTION,
        }
        def authorizer(action, arg1, arg2, database, trigger):
            return sqlite3.SQLITE_DENY if action in denied else sqlite3.SQLITE_OK
        con.set_authorizer(authorizer)

        wrapped = f"SELECT * FROM ({query}) AS agent_result LIMIT {row_limit}"
        cursor = con.execute(wrapped)
        columns = [d[0] for d in cursor.description or []]
        rows = [dict(row) for row in cursor.fetchall()]
        response = {
            "ok": True, "columns": columns, "rows": rows,
            "row_count": len(rows), "truncated_or_limited": len(rows) >= row_limit,
            "database_principal": DB_PRINCIPAL, "connection_mode": "read-only",
            "database": Path(db_path).name,
        }
        _write_audit(sql, "SUCCESS", rows_returned=len(rows), db_path=db_path)
        return response
    except sqlite3.Error as exc:
        error = f"{type(exc).__name__}: {exc}"
        _write_audit(sql, "ERROR", error=error, db_path=db_path)
        return {"ok": False, "error": error, "rows": [],
                "database_principal": DB_PRINCIPAL, "connection_mode": "read-only"}
    finally:
        if con is not None:
            con.close()

def calculator(expression):
    """Small arithmetic helper; deliberately supports only basic numeric arithmetic."""
    if not isinstance(expression, str) or not re.fullmatch(r"[0-9eE+\-*/(). %]+", expression):
        return {"ok": False, "error": "Unsupported calculator expression"}
    try:
        value = eval(expression, {"__builtins__": {}}, {})
        if not isinstance(value, (int, float)):
            raise ValueError("Expression did not produce a number")
        return {"ok": True, "value": value}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
