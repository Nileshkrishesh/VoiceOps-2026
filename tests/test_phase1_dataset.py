"""Pytest test suite for Phase 1: Dataset schema, integrity, and mock tools verification."""
import sys
import re
from pathlib import Path
from datetime import date
import pandas as pd
import pytest

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import (
    DATASET_DIR, DATA_DIR, KB_DIR, PRACTICE_DIR, TOOLS_DIR,
    REFERENCE_DATE, is_business_day, add_business_days, business_days_between
)

def test_dataset_directories_exist():
    """Verify that all core dataset directories exist."""
    assert DATASET_DIR.exists(), f"Dataset directory missing: {DATASET_DIR}"
    assert DATA_DIR.exists(), f"Data directory missing: {DATA_DIR}"
    assert KB_DIR.exists(), f"KB directory missing: {KB_DIR}"
    assert PRACTICE_DIR.exists(), f"Practice directory missing: {PRACTICE_DIR}"
    assert TOOLS_DIR.exists(), f"Tools directory missing: {TOOLS_DIR}"

def test_csv_row_counts():
    """Verify the exact row counts for all 9 dataset CSV files."""
    expected_counts = {
        DATA_DIR / "customers.csv": 300,
        DATA_DIR / "orders.csv": 1000,
        DATA_DIR / "order_items.csv": 1783,
        DATA_DIR / "products.csv": 70,
        DATA_DIR / "pincodes.csv": 36,
        DATA_DIR / "holidays.csv": 4,
        DATA_DIR / "support_logs.csv": 244,
        PRACTICE_DIR / "questions.csv": 52,
        PRACTICE_DIR / "conversations.csv": 96,
    }
    for file_path, count in expected_counts.items():
        assert file_path.exists(), f"Missing file: {file_path}"
        df = pd.read_csv(file_path, dtype=str)
        assert len(df) == count, f"{file_path.name}: expected {count} rows, got {len(df)}"

def test_kb_documents_count_and_metadata():
    """Verify that there are 21 KB documents and each has mandatory metadata."""
    kb_files = list(KB_DIR.glob("*.md"))
    assert len(kb_files) == 21, f"Expected 21 KB markdown files, found {len(kb_files)}"
    
    required_fields = ["doc_id:", "title:", "doc_type:", "effective_from:", "status:"]
    section_ids = []
    
    for doc in kb_files:
        content = doc.read_text(encoding="utf-8")
        for field in required_fields:
            assert field in content, f"Missing {field} in {doc.name}"
        
        # Collect section IDs
        matches = re.findall(r"^##\s*\[([^\]]+)\]", content, re.MULTILINE)
        section_ids.extend(matches)
        
    # Ensure all section IDs are unique across documents
    assert len(section_ids) == len(set(section_ids)), "Duplicate section IDs detected in KB"

def test_mock_tools_import_and_verification():
    """Verify that tools/tools.py imports correctly and enforces caller verification."""
    # Add tools path to sys.path
    if str(TOOLS_DIR.parent) not in sys.path:
        sys.path.insert(0, str(TOOLS_DIR.parent))
    
    from tools import lookup_order, create_ticket
    
    # 1. Without verification value
    res = lookup_order("89782837")
    assert res.get("verification_required") is True
    assert "items" not in res
    assert "status" not in res
    
    # 2. With invalid verification value
    bad_res = lookup_order("89782837", verification_value="0000")
    assert bad_res.get("verified") is False
    assert "items" not in bad_res
    
    # 3. Create ticket validation (too short summary rejected)
    short_ticket = create_ticket("too short")
    assert short_ticket.get("created") is False
    
    # 4. Valid summary creation
    valid_summary = "Customer claims delivered item had broken screen on order 89782837; requires human agent review."
    ticket = create_ticket(valid_summary, order_id="89782837", reason="high_value_damage")
    assert ticket.get("created") is True
    assert ticket.get("ticket_id").startswith("TKT")

def test_business_day_logic():
    """Verify business days counting (Mon-Sat, skipping Sundays & holidays)."""
    assert REFERENCE_DATE == date(2026, 10, 20)
    # 2026-10-18 was a Sunday -> not a business day
    assert not is_business_day(date(2026, 10, 18))
    # 2026-10-19 was a warehouse holiday -> not a business day
    assert not is_business_day(date(2026, 10, 19))
    # 2026-10-20 was a Tuesday -> business day
    assert is_business_day(date(2026, 10, 20))
    # 2026-10-24 was a Saturday -> business day
    assert is_business_day(date(2026, 10, 24))
    # 2026-10-25 was a Sunday -> not a business day
    assert not is_business_day(date(2026, 10, 25))
