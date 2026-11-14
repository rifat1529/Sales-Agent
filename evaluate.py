from src.db import build_database
from src.evaluate import run_evaluation
from src.cli_helpers import prompt_sampling_options, prompt_database_password
from src.config import TEMPERATURE, TOP_P, TOP_K

if __name__ == "__main__":
    print("LOCAL SQL AI AGENT - EVALUATION")
    sampling = prompt_sampling_options({"temperature": TEMPERATURE, "top_p": TOP_P, "top_k": TOP_K})
    password = prompt_database_password()
    build_database()
    run_evaluation(trials=3, db_password=password, require_db_auth=True, sampling_options=sampling)
