import sqlite3
from src.db import build_database
from src.expected_answers import QUESTIONS, compute_expected

def test_seeded_database_has_four_related_tables(tmp_path):
    db = tmp_path / "test.db"
    counts = build_database(db, seed=1234)
    assert counts["customers"] >= 3
    assert counts["products"] >= 3
    assert counts["orders"] >= 100
    assert counts["order_items"] >= 100
    con = sqlite3.connect(db)
    names = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"customers", "products", "orders", "order_items"} <= names
    con.close()

def test_seed_is_reproducible(tmp_path):
    a, b = tmp_path / "a.db", tmp_path / "b.db"
    build_database(a, seed=77)
    build_database(b, seed=77)
    ca, cb = sqlite3.connect(a), sqlite3.connect(b)
    assert ca.execute("SELECT * FROM order_items ORDER BY order_item_id").fetchall() == cb.execute("SELECT * FROM order_items ORDER BY order_item_id").fetchall()
    ca.close(); cb.close()

def test_question_set_has_at_least_15_and_unanswerable():
    assert len(QUESTIONS) >= 15
    assert sum(q["kind"] == "unanswerable" for q in QUESTIONS) >= 2

def test_expected_answers_are_computed_by_independent_sql(tmp_path, monkeypatch):
    db = tmp_path / "expected.db"
    build_database(db)
    answers = compute_expected(db)
    assert answers["Q01"] == 120
    assert answers["Q18"] is None
