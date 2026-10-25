"""Tools adapter wrapping the official ZentroMart mock tools.

Provides safe access to:
- lookup_order(order_id, verification_value=None)
- create_ticket(summary, order_id=None, reason=None, intent=None)
"""
import sys
import os
from pathlib import Path
from typing import Dict, Any, Optional

from src.config import TOOLS_DIR

# Ensure tools directory is in sys.path
if str(TOOLS_DIR.parent) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR.parent))

from tools import lookup_order as _raw_lookup_order
from tools import create_ticket as _raw_create_ticket

def lookup_order(order_id: str, verification_value: Optional[str] = None) -> Dict[str, Any]:
    """Execute order lookup through official mock tool with caller verification gate."""
    return _raw_lookup_order(order_id=order_id, verification_value=verification_value)

def create_ticket(
    summary: str,
    order_id: Optional[str] = None,
    reason: Optional[str] = None,
    intent: Optional[str] = None,
) -> Dict[str, Any]:
    """Log an escalation or handover ticket through the official mock tool."""
    return _raw_create_ticket(
        summary=summary,
        order_id=order_id,
        reason=reason,
        intent=intent,
    )
