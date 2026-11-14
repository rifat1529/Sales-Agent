# Local SQL AI Agent — Assignment 1

A reproducible local-model SQL agent. The model is run by Ollama; all database values are obtained through read-only SQL tools. No hosted LLM API is used.

## Architecture

```text
Question
  -> Python agent loop (step + token budgets)
  -> Ollama qwen2.5:3b
       -> generate_sql tool (separate local Ollama call)
       -> execute_sql tool (SQLite read-only)
       -> schema_lookup / calculator tools
  -> tool results returned to model
  -> final answer + structured run record
```

**SQL-generation design:** the main agent calls `generate_sql`; that tool makes a separate local model call with the actual schema and asks for one SELECT statement. This keeps SQL generation separately testable and makes SQL errors easy to return to the agent for repair. The main agent then calls `execute_sql` with the generated SQL.

## Requirements

- Python 3.10+
- Ollama installed and running
- `qwen2.5:3b` (or a larger local model)

## Run in five commands

From this folder:

```bash
python -m venv .venv
```

Activate the environment (Windows PowerShell: `.venv\\Scripts\\Activate.ps1`; macOS/Linux: `source .venv/bin/activate`), then:

```bash
pip install -r requirements.txt
ollama pull qwen2.5:3b
python -m src.db
python run.py --question "How many customers are there?"
```

The activation step is a shell operation; if counting strictly, the full setup is six shell commands including activation. Once installed, rebuilding and asking a question takes two commands.

## Run tests and evaluation

```bash
pytest -q
python evaluate.py
```

`evaluate.py` rebuilds the seeded database, then runs every question three times. It writes:
- `logs/run_log.jsonl`: one JSON record per trial, including question, tool calls, SQL, answer, status, token count and elapsed time.
- `reports/generated_evaluation.json`: pass@1, pass^3, at-least-one-pass-in-three, per-question results and timing/token averages.

`pass@1` is the first trial's accuracy over questions. `pass^3` is the fraction of questions for which **all three** trials pass. The additional at-least-one-pass metric is reported separately to avoid confusing the two definitions.

## Database

`src/db.py` creates four related tables: customers, products, orders and order_items. The largest table has over 100 rows. Data is generated from fixed seed `20261115`; rebuilds are deterministic.

## Safety

- The database connection uses SQLite URI `mode=ro`.
- The executor accepts only a single SELECT or read-only WITH query.
- SQLite's authorizer independently denies writes, DDL, PRAGMA and attachment operations.
- Results are capped at `MAX_ROWS` (default 200).
- SQL errors are returned to the agent as tool results for bounded retry.

## Configuration

Environment variables: `OLLAMA_URL`, `OLLAMA_MODEL`, `SQL_MODEL`, `MAX_STEPS`, `MAX_TOOL_CALLS`, `TOKEN_BUDGET`, `MAX_ROWS`, `REQUEST_TIMEOUT`, `AGENT_DB_PATH`.

## Important evaluation note

The expected-answer key in `src/expected_answers.py` runs independent SQL directly against SQLite; it does not call the agent or reuse the agent's generated SQL. The two unanswerable questions refer to fields absent from the schema. The evaluation is intentionally performed against actual local Ollama runs. Do not fill in or claim pass rates until `python evaluate.py` has completed on the target machine.


## Ollama sampling parameters

Both the agent model call and the separate SQL-generator call receive these Ollama options:

- `TEMPERATURE=0.0` (allowed range 0.0–2.0)
- `TOP_P=0.9` (allowed range greater than 0 and up to 1.0)
- `TOP_K=20` (positive integer)

Copy `.env.example` as a reference, or set them as Windows PowerShell environment variables before running, for example:

```powershell
$env:TEMPERATURE="0.0"
$env:TOP_P="0.9"
$env:TOP_K="20"
```

## Database identity and audit trail

SQLite does not implement database usernames/passwords or per-user GRANT permissions. This project therefore uses an application-level identity `DB_PRINCIPAL=agent_readonly`, opens the database with `mode=ro`, enables SQLite `query_only`, disables trusted schema, and installs an authorizer that denies write/DDL actions. The database file itself should be protected with Windows filesystem permissions so only the intended OS account can read it.

Every SQL execution attempt is recorded in `logs/database_audit.jsonl`, separately from the read-only database. Each JSON record contains UTC timestamp, database file, application principal, read-only connection mode, SQL text, status, returned row count, and error (if any). Configure the identity with `$env:DB_PRINCIPAL="agent_readonly"`. This is auditable application identity, not native SQLite authentication. If real database username/password authentication and GRANT-based permissions are required, use PostgreSQL and create a dedicated role with SELECT-only grants.


## Interactive terminal mode and database password prompt

1. Install dependencies: `pip install -r requirements.txt`.
2. Copy `.env.example` to `.env` and replace `DB_ACCESS_PASSWORD` with a password you choose. Keep `.env` private; it is excluded by `.gitignore`.
3. Run `python run.py`. The terminal asks for Temperature, Top P and Top K (press Enter to keep defaults), then asks for a question if `--question` was not supplied, and finally prompts for the database password using a hidden input.
4. You can also supply a question and sampling defaults using `python run.py --question "How many customers are there?" --temperature 0.0 --top-p 0.9 --top-k 20`. The CLI still prompts for the database password.
5. Run `python evaluate.py` to enter sampling settings and the database password once before the 57-run evaluation.

Example PowerShell setup:

```powershell
Copy-Item .env.example .env
notepad .env
python run.py
```

**Security clarification:** SQLite has no native database username/password authentication. `DB_ACCESS_PASSWORD` is an application-level password gate checked by Python before the read-only SQLite connection is opened. The password is not sent to Ollama and is not written to the audit log. The `agent_readonly` name is an application identity. For actual database-server authentication and GRANT permissions, migrate to PostgreSQL and use a dedicated read-only role.
