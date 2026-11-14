from pathlib import Path
import os
import secrets

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
except ImportError:
    pass

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = Path(os.getenv("AGENT_DB_PATH", ROOT / "data" / "sales.db"))
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
SQL_MODEL = os.getenv("SQL_MODEL", MODEL)
MAX_STEPS = int(os.getenv("MAX_STEPS", "8"))
MAX_TOOL_CALLS = int(os.getenv("MAX_TOOL_CALLS", "12"))
MAX_ROWS = int(os.getenv("MAX_ROWS", "200"))
TOKEN_BUDGET = int(os.getenv("TOKEN_BUDGET", "6000"))
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "180"))

# Ollama sampling options (applied to both the agent and SQL-generator calls).
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.0"))
TOP_P = float(os.getenv("TOP_P", "0.9"))
TOP_K = int(os.getenv("TOP_K", "20"))
if not 0.0 <= TEMPERATURE <= 2.0:
    raise ValueError("TEMPERATURE must be between 0.0 and 2.0")
if not 0.0 < TOP_P <= 1.0:
    raise ValueError("TOP_P must be greater than 0 and at most 1.0")
if TOP_K < 1:
    raise ValueError("TOP_K must be a positive integer")

# SQLite has no built-in database users/passwords. This is an application-level
# service identity recorded in the audit trail, not SQLite authentication.
DB_PRINCIPAL = os.getenv("DB_PRINCIPAL", "agent_readonly")
AUDIT_LOG_PATH = Path(os.getenv("AUDIT_LOG_PATH", ROOT / "logs" / "database_audit.jsonl"))

# Application-level password gate for SQLite (not native SQLite authentication).
DB_ACCESS_PASSWORD = os.getenv("DB_ACCESS_PASSWORD", "")
