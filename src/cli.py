import argparse
import json
from .agent import run_agent
from .db import build_database

def main():
    parser = argparse.ArgumentParser(description="Local SQL AI Agent")
    parser.add_argument("question", nargs="*", help="Question to ask")
    parser.add_argument("--rebuild-db", action="store_true")
    args = parser.parse_args()
    if args.rebuild_db:
        print("Database rebuilt:", build_database())
        return
    if not args.question:
        parser.error("Provide a question or use --rebuild-db")
    result = run_agent(" ".join(args.question))
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
