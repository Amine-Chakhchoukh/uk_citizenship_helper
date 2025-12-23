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
    data = getattr(res, "data", None)
    return data or []


def fetch_trips(supabase, user_id: str) -> List[Dict[str, Any]]:
    """
    Fetch trips for one user (newest first).
    """
    q = (
        supabase.table("trips")
        .select("*")
        .eq("user_id", user_id)
        .order("start_date", desc=True)
    )

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
    user_id: str = "",
) -> Dict[str, Any]:
    """
    Insert one trip for one user.
    """
    if not user_id:
        raise ValueError("user_id is required to insert a trip.")

    payload: Dict[str, Any] = {
        "user_id": user_id,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "note": note or None,
    }

    try:
        res = supabase.table("trips").insert(payload).execute()
    except Exception:
        res = supabase.table("trips").insert(payload)

    data = _extract_data(res)
    return data[0] if data else {}


def delete_trip(supabase, trip_id: int, user_id: str) -> None:
    """
    Delete one trip, scoped to the user.
    """
    if not user_id:
        raise ValueError("user_id is required to delete a trip.")

    q = supabase.table("trips").delete().eq("id", trip_id).eq("user_id", user_id)

    try:
        q.execute()
    except Exception:
        q