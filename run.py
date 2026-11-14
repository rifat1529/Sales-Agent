import argparse
import json
from src.db import build_database
from src.config import MODEL, TEMPERATURE, TOP_P, TOP_K
from src.agent import run_agent
from src.cli_helpers import prompt_sampling_options, prompt_database_password


def main():
    p = argparse.ArgumentParser(description="Interactive Local SQL AI Agent")
    p.add_argument("--build-db", action="store_true", help="Rebuild seeded SQLite database")
    p.add_argument("--question", nargs="*", help="Question to ask; omit for interactive prompt")
    p.add_argument("--temperature", type=float, help="Temperature from 0.0 to 2.0")
    p.add_argument("--top-p", type=float, help="Top P from 0.01 to 1.0")
    p.add_argument("--top-k", type=int, help="Top K positive integer")
    args = p.parse_args()

    if args.build_db:
        print("Database rebuilt:", build_database())
        return

    defaults = {
        "temperature": TEMPERATURE if args.temperature is None else args.temperature,
        "top_p": TOP_P if args.top_p is None else args.top_p,
        "top_k": TOP_K if args.top_k is None else args.top_k,
    }
    if not 0.0 <= defaults["temperature"] <= 2.0:
        p.error("--temperature must be between 0.0 and 2.0")
    if not 0.01 <= defaults["top_p"] <= 1.0:
        p.error("--top-p must be between 0.01 and 1.0")
    if defaults["top_k"] < 1:
        p.error("--top-k must be a positive integer")

    print("=" * 48)
    print("             LOCAL SQL AI AGENT")
    print("=" * 48)
    print(f"Model: {MODEL}")
    sampling = prompt_sampling_options(defaults)

    if args.question:
        question = " ".join(args.question)
    else:
        question = input("\nEnter your question:\n> ").strip()
    if not question:
        p.error("Question cannot be empty")

    password = prompt_database_password()
    print("\nRunning agent...\n")
    result = run_agent(
        question,
        sampling_options=sampling,
        db_password=password,
        require_db_auth=True,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
