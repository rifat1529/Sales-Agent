# Assignment 1 — Local SQL AI Agent (Report)

## 1. Architecture and design

The application uses a hand-written Python agent loop with Ollama's local `/api/chat` endpoint and `qwen2.5:3b`. The agent exposes four tools: `generate_sql`, `execute_sql`, `schema_lookup`, and `calculator`. `generate_sql` is a separate local-model call that receives the actual SQLite schema and returns one SELECT query as JSON. The agent then sends that query to `execute_sql`. The executor opens the database in read-only mode, validates the statement, applies a SQLite authorizer that denies writes/DDL, and enforces a row cap. Tool errors are returned to the model so it can repair SQL within the configured step and token budgets.

The database builder creates four related tables (`customers`, `products`, `orders`, `order_items`) from fixed seed `20261115`. The largest table contains at least 100 rows. Expected answers are computed by independent SQL in `src/expected_answers.py`, not by the agent.

## 2. Evaluation

Run `python evaluate.py` on the machine with Ollama and the selected model installed. Copy the actual values from `reports/generated_evaluation.json`:

- Questions: [fill from generated report]
- Trials per question: 3
- Total runs: [fill]
- pass@1: [fill]
- pass^3 (all three trials pass): [fill]
- At least one pass in three trials: [fill]
- Mean tokens / run: [fill]
- Mean seconds / run: [fill]

Do not report fabricated or unexecuted measurements.

## 3. Three most common failure types

Populate this section from `logs/run_log.jsonl` after evaluation. Suggested categories to inspect (only retain categories that actually occurred):

1. SQL generation error — e.g. wrong column, missing join, or incorrect aggregation.
2. Tool-loop / tool-call error — e.g. model returns malformed arguments or fails to call the required tool.
3. Answer-grounding / formatting error — e.g. SQL result is correct but the final response omits or misstates the returned value.

For each category, include its observed count and one real question/run example from the log.

## 4. Improvement and before/after

Record one actual change and run the same evaluation before and after. Example improvement: add the live schema to the SQL-generation prompt and explicitly define the revenue formula. Report the measured pass@1 and pass^3 before and after. If no baseline run was saved, do not invent before numbers; perform and retain both evaluations.

## 5. Reproducibility

The database is deterministic, the expected answer key is independent, and the full evaluation is run with three trials per question. The README contains setup, execution, testing, and evaluation commands.
