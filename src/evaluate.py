import json
import re
import statistics
from pathlib import Path
from .agent import run_agent
from .expected_answers import QUESTIONS, compute_expected
from .config import ROOT, DB_PATH, TEMPERATURE, TOP_P, TOP_K

def _normalise_number(value):
    try:
        return float(str(value).replace(",", "").replace("$", "").replace("%", "").strip())
    except Exception:
        return None

def is_correct(run, expected, kind):
    if run["status"] != "ok":
        return False
    answer = run["final_answer"] or ""
    if kind == "unanswerable":
        low = answer.lower()
        return any(term in low for term in ["cannot answer", "not in the database", "not available", "does not contain", "no data", "not represented"])
    if kind == "text":
        return str(expected).lower() in answer.lower()
    if kind == "multi":
        values = expected if isinstance(expected, list) else [expected]
        nums = [_normalise_number(v) for v in re.findall(r"(?<![A-Za-z])[-+]?\d[\d,]*(?:\.\d+)?%?", answer)]
        nums = [n for n in nums if n is not None]
        return all(any(abs(n - float(v)) <= max(0.02, abs(float(v))*0.001) for n in nums) for v in values if v is not None)
    target = _normalise_number(expected)
    nums = [_normalise_number(v) for v in re.findall(r"(?<![A-Za-z])[-+]?\d[\d,]*(?:\.\d+)?%?", answer)]
    return target is not None and any(n is not None and abs(n-target) <= max(0.02, abs(target)*0.001) for n in nums)

def run_evaluation(trials=3, db_password=None, require_db_auth=False, sampling_options=None):
    expected = compute_expected()
    all_runs = []
    for item in QUESTIONS:
        for trial in range(1, trials+1):
            result = run_agent(item["question"], db_password=db_password, require_db_auth=require_db_auth, sampling_options=sampling_options)
            result.update({"question_id": item["id"], "trial": trial})
            result["pass"] = is_correct(result, expected[item["id"]], item["kind"])
            all_runs.append(result)
            print(f'{item["id"]} trial {trial}: {result["status"]}, pass={result["pass"]}')
    logs = ROOT / "logs"
    logs.mkdir(exist_ok=True)
    with (logs / "run_log.jsonl").open("w", encoding="utf-8") as f:
        for record in all_runs:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    per_question = {}
    for item in QUESTIONS:
        subset = [r for r in all_runs if r["question_id"] == item["id"]]
        per_question[item["id"]] = {
            "pass_at_1": bool(subset and subset[0]["pass"]),
            "pass_at_3": any(r["pass"] for r in subset),
            "all_three_pass": all(r["pass"] for r in subset),
            "passed_trials": sum(r["pass"] for r in subset),
            "trials": len(subset)
        }
    pass1 = sum(v["pass_at_1"] for v in per_question.values()) / len(QUESTIONS)
    pass3 = sum(v["all_three_pass"] for v in per_question.values()) / len(QUESTIONS)
    any_pass3 = sum(v["pass_at_3"] for v in per_question.values()) / len(QUESTIONS)
    summary = {
        "model": __import__("src.config", fromlist=["MODEL"]).MODEL,
        "questions": len(QUESTIONS), "trials_per_question": trials,
        "total_runs": len(all_runs), "pass_at_1": round(pass1, 4),
        "pass_pow_3": round(pass3, 4),
        "at_least_one_pass_in_three": round(any_pass3, 4),
        "per_question": per_question,
        "mean_tokens": round(statistics.mean(r["tokens"] for r in all_runs), 1),
        "mean_seconds": round(statistics.mean(r["elapsed_seconds"] for r in all_runs), 3)
    }
    (ROOT / "reports" / "generated_evaluation.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))
    return summary

if __name__ == "__main__":
    run_evaluation(trials=3)
