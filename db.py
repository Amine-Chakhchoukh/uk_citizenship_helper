from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional


def _extract_data(res: Any) -> List[Dict[str, Any]]:
    """
    st_supabase_connection sometimes returns a dict like {"data": [...], "count": ...}
    supabase-py returns an APIResponse object with attribute `.data`.
    This helper supports both.
    """
    if res is None:
        return []
    if isinstance(res, dict):
        return res.get("data", []) or []
    # APIResponse from supabase-py
    data = getattr(res, "data", None)
    return data or []


def fetch_trips(supabase, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    q = supabase.table("trips").select("*").order("start_date", desc=True)
    if user_id:
        q = q.eq("user_id", user_id)

    # Depending on st_supabase_connection version, this may or may not require .execute()
    # We'll try .execute() first; if it errors, fall back to raw.
    try:
        res = q.execute()
    except Exception:
        res = q

    return _extract_data(res)


def insert_trip(
    supabase,
    start: date,
    end: date,
    note: str = "",
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "start_date": start.isoformat(),  # IMPORTANT: dates must be JSON-serialisable
        "end_date": end.isoformat(),
        "note": note or None,
    }
    if user_id:
        payload["user_id"] = user_id

    try:
        res = supabase.table("trips").insert(payload).execute()
    except Exception:
        res = supabase.table("trips").insert(payload)

    data = _extract_data(res)
    return data[0] if data else {}


def delete_trip(supabase, trip_id: int) -> None:
    try:
        supabase.table("trips").delete().eq("id", trip_id).execute()
    except Exception:
        supabase.table("trips").delete().eq("id", trip_id)