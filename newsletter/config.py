import os
from dotenv import load_dotenv

load_dotenv()

REQUIRED_VARS = [
    "GROQ_API_KEY_1",
    "TAVILY_API_KEY",
    "RESEND_API_KEY",
    "SUPABASE_URL",
    "SUPABASE_SERVICE_ROLE_KEY",
    "NEWSLETTER_FROM_EMAIL",
    "BASE_URL",
]

OPTIONAL_VARS = {
    "GROQ_API_KEY_2": "",
    "GROQ_API_KEY_3": "",
    "NEWSLETTER_REPLY_TO": "",
    "ADMIN_EMAIL": "",
    "ADMIN_TRIGGER_TOKEN": "",
    "ADMIN_SESSION_SECRET": "changeme",
    "NEWSLETTER_NAME": "PeopleOS Brief",
    "SUPABASE_ANON_KEY": "",
    "ADMIN_TEST_EMAIL": "",
    # Timing
    "SECTION_SEARCH_DELAY_SECONDS": "3",
    "GROQ_SECTION_DELAY_SECONDS": "15",
    "GROQ_RETRY_DELAY_SECONDS": "20",
    "GROQ_KEY_COOLDOWN_SECONDS": "20",
    # Generation limits
    "MAX_CANDIDATES_PER_SECTION": "8",
    "MAX_SNIPPET_CHARS": "300",
    "MAX_GROQ_RETRIES_PER_SECTION": "3",
    # Archive
    "ARCHIVE_RETENTION_DAYS": "180",
    # GitHub Actions dispatch
    "GITHUB_OWNER": "",
    "GITHUB_REPO": "",
    "GITHUB_WORKFLOW_FILE": "daily-brief.yml",
    "GITHUB_PAT_FOR_WORKFLOW_DISPATCH": "",
}


def validate_config(required: list[str] | None = None) -> None:
    check = required if required is not None else REQUIRED_VARS
    missing = [v for v in check if not os.getenv(v)]
    if missing:
        raise EnvironmentError(
            f"Missing required environment variables: {', '.join(missing)}\n"
            "Copy .env.example to .env and fill in values."
        )


def get(key: str, default: str = "") -> str:
    return os.getenv(key, OPTIONAL_VARS.get(key, default))


def get_int(key: str) -> int:
    return int(get(key, OPTIONAL_VARS.get(key, "0")))


def groq_keys() -> list[str]:
    keys = []
    for i in (1, 2, 3):
        k = os.getenv(f"GROQ_API_KEY_{i}", "").strip()
        if k:
            keys.append(k)
    if not keys:
        raise EnvironmentError("No Groq API keys found. Set GROQ_API_KEY_1.")
    return keys


def tavily_key() -> str:
    return os.environ["TAVILY_API_KEY"]

def resend_key() -> str:
    return os.environ["RESEND_API_KEY"]

def supabase_url() -> str:
    return os.environ["SUPABASE_URL"]

def supabase_service_key() -> str:
    return os.environ["SUPABASE_SERVICE_ROLE_KEY"]

def from_email() -> str:
    return os.environ["NEWSLETTER_FROM_EMAIL"]

def reply_to() -> str:
    return os.getenv("NEWSLETTER_REPLY_TO", from_email())

def base_url() -> str:
    return os.environ["BASE_URL"].rstrip("/")

def newsletter_name() -> str:
    return os.getenv("NEWSLETTER_NAME", "PeopleOS Brief")

def admin_test_email() -> str:
    return os.getenv("ADMIN_TEST_EMAIL", "")

def admin_trigger_token() -> str:
    return os.getenv("ADMIN_TRIGGER_TOKEN", "")

def archive_retention_days() -> int:
    return int(os.getenv("ARCHIVE_RETENTION_DAYS", "180"))

def section_search_delay() -> float:
    return float(get("SECTION_SEARCH_DELAY_SECONDS"))

def groq_section_delay() -> float:
    return float(get("GROQ_SECTION_DELAY_SECONDS"))

def groq_retry_delay() -> float:
    return float(get("GROQ_RETRY_DELAY_SECONDS"))

def groq_key_cooldown() -> float:
    return float(get("GROQ_KEY_COOLDOWN_SECONDS"))

def max_candidates_per_section() -> int:
    return int(get("MAX_CANDIDATES_PER_SECTION"))

def max_snippet_chars() -> int:
    return int(get("MAX_SNIPPET_CHARS"))

def max_groq_retries_per_section() -> int:
    return int(get("MAX_GROQ_RETRIES_PER_SECTION"))
