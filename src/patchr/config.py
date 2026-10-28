"""Settings from the environment and the repository's .env file."""
import os
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNS_ROOT = REPO_ROOT / ".runs"
TRACES_ROOT = REPO_ROOT / "traces" / "phase1"


def load_dotenv(path: Path = REPO_ROOT / ".env") -> None:
    """Load KEY=VALUE lines without overriding variables that are already set."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.removeprefix("export ").strip()
        value = value.strip().strip('"').strip("'")
        if not os.environ.get(key):
            os.environ[key] = value


load_dotenv()

# Bounds that keep a run finite and within free-tier quotas.
MAX_STEPS_PER_TURN = int(os.environ.get("PATCHR_MAX_STEPS_PER_TURN") or 12)
MAX_TURNS = int(os.environ.get("PATCHR_MAX_TURNS") or 20)
MAX_LLM_CALLS = int(os.environ.get("PATCHR_MAX_LLM_CALLS") or 60)


@dataclass(frozen=True)
class ModelSettings:
    base_url: str
    model_id: str
    api_key: str = field(repr=False)
    rpm: float = 0
    temperature: float | None = None


def model_settings() -> ModelSettings:
    load_dotenv()
    model_id = os.environ.get("MODEL_ID", "").strip()
    api_key = os.environ.get("MODEL_API_KEY") or os.environ.get("GEMINI_API_KEY", "")
    if not model_id:
        raise SystemExit("MODEL_ID is not set. Add it to .env (see .env.example) or run with --fake.")
    if not api_key:
        raise SystemExit("MODEL_API_KEY is not set. Add it to .env (see .env.example) or run with --fake.")
    temperature = os.environ.get("MODEL_TEMPERATURE")
    return ModelSettings(
        base_url=os.environ.get("MODEL_BASE_URL") or "https://generativelanguage.googleapis.com/v1beta/openai/",
        model_id=model_id,
        api_key=api_key,
        rpm=float(os.environ.get("MODEL_RPM") or 0),
        temperature=float(temperature) if temperature else None,
    )
