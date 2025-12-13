from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, Optional

from calculator import Trip


@dataclass(frozen=True)
class TripRow:
    """
    What we keep in session_state for UI:
    - id: Supabase row id (needed for delete)
    - trip: your existing Trip model (used by calculator)
    """
    id: int
    trip: Trip


def row_to_triprow(row: Dict[str, Any]) -> TripRow:
    return TripRow(
        id=int(row["id"]),
        trip=Trip(
            start=date.fromisoformat(row["start_date"]),
            end=date.fromisoformat(row["end_date"]),
            note=(row.get("note") or "").strip(),
        ),
    )