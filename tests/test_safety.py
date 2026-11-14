import sqlite3
from src.db import build_database
from src.tools import execute_sql

def test_select_works(tmp_path):
    db = tmp_path / "safe.db"
    build_database(db)
    result = execute_sql("SELECT COUNT(*) AS n FROM customers", db_path=db)
    assert result["ok"] is True
    assert result["rows"][0]["n"] == 120

def test_rejects_write_and_ddl_statements(tmp_path):
    db = tmp_path / "safe.db"
    build_database(db)
    for sql in [
        "DROP TABLE customers", "DELETE FROM customers",
        "UPDATE customers SET city='X'", "INSERT INTO customers VALUES (999,'x','x','x','2025-01-01')",
        "CREATE TABLE evil(id INTEGER)", "PRAGMA table_info(customers)"
    ]:
        result = execute_sql(sql, db_path=db)
        assert result["ok"] is False, sql

def test_rejects_multiple_statements(tmp_path):
    db = tmp_path / "safe.db"
    build_database(db)
    result = execute_sql("SELECT 1; SELECT 2", db_path=db)
    assert result["ok"] is False

def test_row_limit_is_applied(tmp_path):
    db = tmp_path / "safe.db"
    build_database(db)
    result = execute_sql("SELECT * FROM order_items", db_path=db, row_limit=7)
    assert result["ok"] is True
    assert len(result["rows"]) == 7


def test_audit_log_records_principal_query_and_status(tmp_path, monkeypatch):
    import json
    import src.tools as tools
    db = tmp_path / "audit.db"
    audit = tmp_path / "audit.jsonl"
    build_database(db)
    monkeypatch.setattr(tools, "AUDIT_LOG_PATH", audit)
    result = tools.execute_sql("SELECT COUNT(*) AS n FROM customers", db_path=db)
    assert result["ok"] is True
    assert result["database_principal"] == "agent_readonly"
    assert result["connection_mode"] == "read-only"
    record = json.loads(audit.read_text(encoding="utf-8").splitlines()[-1])
    assert record["principal"] == "agent_readonly"
    assert record["status"] == "SUCCESS"
    assert record["sql"] == "SELECT COUNT(*) AS n FROM customers"
    assert record["rows_returned"] == 1


def test_rejected_query_is_audited(tmp_path, monkeypatch):
    import json
    import src.tools as tools
    db = tmp_path / "audit.db"
    audit = tmp_path / "audit.jsonl"
    build_database(db)
    monkeypatch.setattr(tools, "AUDIT_LOG_PATH", audit)
    result = tools.execute_sql("DROP TABLE customers", db_path=db)
    assert result["ok"] is False
    record = json.loads(audit.read_text(encoding="utf-8").splitlines()[-1])
    assert record["status"] == "REJECTED"
    assert record["operation"] == "REJECTED"



def test_database_password_gate_rejects_wrong_password(tmp_path, monkeypatch):
    import src.tools as tools
    db = tmp_path / "auth.db"
    build_database(db)
    monkeypatch.setattr(tools, "DB_ACCESS_PASSWORD", "correct-horse")
    result = tools.execute_sql("SELECT 1", db_path=db, db_password="wrong", require_auth=True)
    assert result["ok"] is False
    assert "authentication failed" in result["error"].lower()


def test_database_password_gate_accepts_correct_password(tmp_path, monkeypatch):
    import src.tools as tools
    db = tmp_path / "auth.db"
    build_database(db)
    monkeypatch.setattr(tools, "DB_ACCESS_PASSWORD", "correct-horse")
    result = tools.execute_sql("SELECT 1 AS value", db_path=db, db_password="correct-horse", require_auth=True)
    assert result["ok"] is True
    assert result["rows"][0]["value"] == 1
