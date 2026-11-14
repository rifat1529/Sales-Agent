from getpass import getpass
from .config import TEMPERATURE, TOP_P, TOP_K, DB_PRINCIPAL, DB_ACCESS_PASSWORD


def _prompt_float(label, default, minimum, maximum, include_zero=True):
    while True:
        raw = input(f"{label} [{default}]: ").strip()
        if not raw:
            return default
        try:
            value = float(raw)
            if minimum <= value <= maximum:
                return value
        except ValueError:
            pass
        print(f"Enter a number between {minimum} and {maximum}.")


def _prompt_int(label, default, minimum=1, maximum=1000):
    while True:
        raw = input(f"{label} [{default}]: ").strip()
        if not raw:
            return default
        try:
            value = int(raw)
            if minimum <= value <= maximum:
                return value
        except ValueError:
            pass
        print(f"Enter a whole number between {minimum} and {maximum}.")


def prompt_sampling_options(defaults=None):
    defaults = defaults or {"temperature": TEMPERATURE, "top_p": TOP_P, "top_k": TOP_K}
    print("\nMODEL CONFIGURATION")
    temperature = _prompt_float("Temperature (0.0-2.0)", defaults["temperature"], 0.0, 2.0)
    top_p = _prompt_float("Top P (0.01-1.0)", defaults["top_p"], 0.01, 1.0)
    top_k = _prompt_int("Top K", defaults["top_k"], 1, 1000)
    return {"temperature": temperature, "top_p": top_p, "top_k": top_k}


def prompt_database_password():
    print("\nDATABASE AUTHENTICATION")
    print(f"Database identity: {DB_PRINCIPAL}")
    if not DB_ACCESS_PASSWORD:
        raise RuntimeError(
            "DB_ACCESS_PASSWORD is not configured. Create a .env file from .env.example "
            "and set DB_ACCESS_PASSWORD before running the agent."
        )
    return getpass("Database password: ")
