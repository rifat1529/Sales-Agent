from src import agent


def test_agent_returns_step_cap_when_model_never_finishes(monkeypatch):
    def fake_chat(messages, sampling_options=None):
        return ({"content": "", "tool_calls": []}, 1)
    # An empty assistant response is an error status, not an infinite loop.
    monkeypatch.setattr(agent, "_chat", fake_chat)
    result = agent.run_agent("test", max_steps=1, token_budget=100)
    assert result["status"] == "error"


def test_agent_enforces_token_budget(monkeypatch):
    def fake_chat(messages, sampling_options=None):
        return ({"content": "I cannot answer."}, 50)
    monkeypatch.setattr(agent, "_chat", fake_chat)
    result = agent.run_agent("test", max_steps=3, token_budget=10)
    assert result["status"] == "budget_cap"


def test_agent_handles_ollama_connection_error(monkeypatch):
    import requests
    def fake_chat(messages, sampling_options=None):
        raise requests.ConnectionError("offline")
    monkeypatch.setattr(agent, "_chat", fake_chat)
    result = agent.run_agent("test")
    assert result["status"] == "error"
    assert "local Ollama" in result["final_answer"]


def test_agent_ollama_payload_includes_sampling_options(monkeypatch):
    import src.agent as agent
    captured = {}
    class Response:
        def raise_for_status(self): pass
        def json(self): return {"message": {"content": "done"}, "prompt_eval_count": 1, "eval_count": 1}
    def fake_post(url, json, timeout):
        captured.update(json)
        return Response()
    monkeypatch.setattr(agent.requests, "post", fake_post)
    agent._chat([{"role": "user", "content": "hi"}])
    assert captured["options"]["temperature"] == agent.TEMPERATURE
    assert captured["options"]["top_p"] == agent.TOP_P
    assert captured["options"]["top_k"] == agent.TOP_K
