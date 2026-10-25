"""Central configuration module for VoiceOps 2026 ZentroMart Customer Support Agent."""
import os
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import List, Optional
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

# Ensure HuggingFace models load from local cache without network timeouts
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

# Base project directories
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
TESTS_DIR = PROJECT_ROOT / "tests"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
REPORTS_DIR = PROJECT_ROOT / "reports"

# Ensure local writable caches inside project root
os.environ.setdefault("KERAS_HOME", str(PROJECT_ROOT / ".keras"))
os.environ.setdefault("MPLCONFIGDIR", str(PROJECT_ROOT / ".matplotlib"))

# Dataset root resolution: check env var, then local dataset folder, then Capstone folder
def _resolve_dataset_dir() -> Path:
    env_path = os.getenv("DATASET_DIR")
    if env_path and Path(env_path).exists():
        return Path(env_path).resolve()
    
    candidates = [
        PROJECT_ROOT / "Capstone_Project_Dataset_FTTT_2026",
        PROJECT_ROOT / "dataset",
        PROJECT_ROOT.parent / "Capstone_Project_Dataset_FTTT_2026",
    ]
    for c in candidates:
        if c.exists() and (c / "data").exists() and (c / "kb").exists():
            return c.resolve()
    return candidates[0]

DATASET_DIR = _resolve_dataset_dir()
DATA_DIR = DATASET_DIR / "data"
KB_DIR = DATASET_DIR / "kb"
PRACTICE_DIR = DATASET_DIR / "practice"
TOOLS_DIR = DATASET_DIR / "tools"

# Reference date for the capstone (20 October 2026)
REFERENCE_DATE_STR = "2026-10-20"
REFERENCE_DATE = date(2026, 10, 20)

# Official official warehouse holidays (excluding Sundays)
OFFICIAL_HOLIDAYS = {
    date(2026, 8, 15),  # Independence Day
    date(2026, 10, 2),  # Gandhi Jayanti
    date(2026, 10, 19), # Warehouse closure (festival)
    date(2026, 11, 9),  # Warehouse closure (festival)
}

# Policy precedence order as specified in KB-00.1
POLICY_PRECEDENCE = [
    "policy",
    "agent_guide",
    "help",
    "faq",
    "marketing",
]

# Documents superseded or non-authoritative
SUPERSEDED_FILES = {"pol_returns_v3_superseded.md"}

# LLM Configuration
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini")  # options: gemini, openai, local
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-2.5-flash")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Embedding and Vector DB Configuration
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2")
RETRIEVAL_TOP_K = int(os.getenv("RETRIEVAL_TOP_K", "6"))
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.25"))

# Gnani.ai Configuration
GNANI_API_KEY = os.getenv("GNANI_API_KEY", "")
GNANI_STT_LANG = os.getenv("GNANI_STT_LANG", "en-IN")
GNANI_TTS_VOICE = os.getenv("GNANI_TTS_VOICE", "Kaveri")
GNANI_TTS_MODEL = os.getenv("GNANI_TTS_MODEL", "timbre-v2.5")
GNANI_TTS_LANG = os.getenv("GNANI_TTS_LANG", "en-IN")

def is_business_day(d: date) -> bool:
    """A business day is Monday to Saturday (weekday 0-5), excluding official holidays."""
    if d.weekday() == 6:  # Sunday is index 6
        return False
    if d in OFFICIAL_HOLIDAYS:
        return False
    return True

def add_business_days(start_date: date, num_days: int) -> date:
    """Add a specified number of business days to a given start date."""
    cur = start_date
    added = 0
    while added < num_days:
        cur += timedelta(days=1)
        if is_business_day(cur):
            added += 1
    return cur

def business_days_between(start_date: date, end_date: date) -> int:
    """Calculate the number of business days between start_date (exclusive) and end_date (inclusive)."""
    if start_date >= end_date:
        return 0
    cur = start_date + timedelta(days=1)
    count = 0
    while cur <= end_date:
        if is_business_day(cur):
            count += 1
        cur += timedelta(days=1)
    return count
