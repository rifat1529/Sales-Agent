import json
import time
import requests
from .config import (OLLAMA_URL, MODEL, MAX_STEPS, MAX_TOOL_CALLS, TOKEN_BUDGET,
                     REQUEST_TIMEOUT, TEMPERATURE, TOP_P, TOP_K)
from .tools import schema_lookup, generate_sql, execute_sql, calculator

TOOLS = [
    {"type": "function", "function": {"name": "generate_sql", "description": "Generate one SQLite SELECT query for the user's question using the database schema. Call this before executing a new question.", "parameters": {"type": "object", "properties": {"question": {"type": "string"}}, "required": ["question"]}}},
    {"type": "function", "function": {"name": "execute_sql", "description": "Execute one read-only SQL SELECT and return rows or a clear error. Use the SQL returned by generate_sql.", "parameters": {"type": "object", "properties": {"sql": {"type": "string"}}, "required": ["sql"]}}},
    {"type": "function", "function": {"name": "schema_lookup", "description": "Return actual database table and column definitions.", "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {"name": "calculator", "description": "Evaluate a simple arithmetic expression using numbers already returned by tools.", "parameters": {"type": "object", "properties": {"expression": {"type": "string"}}, "required": ["expression"]}}},
]

def _chat(messages, sampling_options=None):
    response = requests.post(
        f"{OLLAMA_URL}/api/chat",
        json={
            "model": MODEL, "messages": messages, "tools": TOOLS, "stream": False,
            "options": sampling_options or {
                "temperature": TEMPERATURE,
                "top_p": TOP_P,
                "top_k": TOP_K,
            },
        },
        timeout=REQUEST_TIMEOUT
    )
    response.raise_for_status()
    data = response.json()
    message = data.get("message", {})
    tokens = data.get("prompt_eval_count", 0) + data.get("eval_count", 0)
    return message, tokens

def run_agent(question, max_steps=MAX_STEPS, token_budget=TOKEN_BUDGET,
              sampling_options=None, db_password=None, require_db_auth=False):
    """Hand-written bounded tool loop. Returns a structured result for every run."""
    started = time.perf_counter()
    calls, sql_written, total_tokens = [], [], 0
    status, final_answer = "error", ""
    messages = [
        {"role": "system", "content": (
            "You are a database calculation agent. You MUST use tools for every numerical "
            "answer. Never estimate, infer, or invent database values. First call generate_sql "
            "with the user's question, then call execute_sql with exactly the generated SQL. "
            "If SQL execution fails, use the error to correct the query and retry within the "
            "available steps. For questions not represented by the schema/data, explain that "
            "the database cannot answer. Base every factual number in the final answer on tool "
            "results. Use calculator only for arithmetic that cannot reasonably be done in SQL. "
            "Do not claim a query succeeded unless execute_sql returned ok=true."
        )},
        {"role": "user", "content": question}
    ]
    tool_count = 0
    try:
        for step in range(max_steps):
            message, tokens = _chat(messages, sampling_options=sampling_options)
            total_tokens += tokens
            if total_tokens > token_budget:
                status = "budget_cap"
                final_answer = "Stopped because the token budget was reached."
                break
            messages.append(message)
            tool_calls = message.get("tool_calls") or []
            if not tool_calls:
                final_answer = message.get("content", "").strip()
                status = "ok" if final_answer else "error"
                break

            for call in tool_calls:
                if tool_count >= MAX_TOOL_CALLS:
                    status = "step_cap"
                    final_answer = "Stopped because the tool-call limit was reached."
                    break
                fn = call.get("function", {})
                name = fn.get("name")
                args = fn.get("arguments") or {}
                if isinstance(args, str):
                    args = json.loads(args)
                tool_count += 1
                record = {"step": step + 1, "tool": name, "arguments": args}
                try:
                    if name == "generate_sql":
                        result = generate_sql(args["question"], schema_lookup(db_password=db_password, require_auth=require_db_auth), sampling_options=sampling_options)
                        sql_written.append(result["sql"])
                        total_tokens += result.get("tokens", 0)
                    elif name == "execute_sql":
                        result = execute_sql(args["sql"], db_password=db_password, require_auth=require_db_auth)
                    elif name == "schema_lookup":
                        result = {"schema": schema_lookup(db_password=db_password, require_auth=require_db_auth)}
                    elif name == "calculator":
                        result = calculator(args["expression"])
                    else:
                        result = {"ok": False, "error": f"Unknown tool: {name}"}
                except Exception as exc:
                    result = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
                record["result"] = result
                calls.append(record)
                messages.append({
                    "role": "tool",
                    "tool_name": name or "unknown",
                    "content": json.dumps(result, default=str)
                })
            else:
                continue
            break
        else:
            status = "step_cap"
            final_answer = f"Stopped after reaching the {max_steps}-step limit."
        if total_tokens > token_budget and status != "budget_cap":
            status = "budget_cap"
            final_answer = "Stopped because the token budget was reached."
    except requests.RequestException as exc:
        status = "error"
        final_answer = f"Could not reach local Ollama: {exc}. Is Ollama running and the model pulled?"
    except Exception as exc:
        status = "error"
        final_answer = f"{type(exc).__name__}: {exc}"

    return {
        "question": question, "tool_calls": calls, "sql_written": sql_written,
        "final_answer": final_answer, "status": status, "tokens": total_tokens,
        "elapsed_seconds": round(time.perf_counter() - started, 3)
    }
