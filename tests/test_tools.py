from src.tools import calculator, _is_read_only_select

def test_calculator():
    assert calculator("(100-80)*100/80")["value"] == 25

def test_select_validation():
    assert _is_read_only_select("SELECT 1")[0]
    assert _is_read_only_select("WITH x AS (SELECT 1) SELECT * FROM x")[0]
    assert not _is_read_only_select("DELETE FROM x")[0]
    assert not _is_read_only_select("SELECT 1; SELECT 2")[0]


def test_ollama_sql_generator_payload_includes_sampling_options(monkeypatch):
    import src.tools as tools
    captured = {}
    class Response:
        def raise_for_status(self): pass
        def json(self): return {"message": {"content": '{"sql":"SELECT 1"}'}, "prompt_eval_count": 1, "eval_count": 2}
    def fake_post(url, json, timeout):
        captured.update(json)
        return Response()
    monkeypatch.setattr(tools.requests, "post", fake_post)
    tools.generate_sql("test", schema="t(id INTEGER)")
    assert captured["options"]["temperature"] == tools.TEMPERATURE
    assert captured["options"]["top_p"] == tools.TOP_P
    assert captured["options"]["top_k"] == tools.TOP_K
