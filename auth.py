from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Literal

import streamlit as st
from st_supabase_connection import SupabaseConnection


# -----------------------------
# Connection / state helpers
# -----------------------------

# IMPORTANT: this must match your secrets.toml connection name: [connections.supabase]
SUPABASE_CONN_NAME = "supabase"
SESSION_KEY = "auth_session"


def get_supabase() -> SupabaseConnection:
    return st.connection(
        name=SUPABASE_CONN_NAME,
        type=SupabaseConnection,
        ttl=None,
    )


def _session_from_state() -> Optional[dict]:
    return st.session_state.get(SESSION_KEY)


def _set_session(session: Optional[dict]) -> None:
    if session is None:
        st.session_state.pop(SESSION_KEY, None)
    else:
        st.session_state[SESSION_KEY] = session


# -----------------------------
# User model
# -----------------------------

@dataclass(frozen=True)
class AuthUser:
    id: str
    email: Optional[str] = None
    raw: Optional[dict] = None


def _to_auth_user(user_obj: Any) -> Optional[AuthUser]:
    if not user_obj:
        return None

    user_id = getattr(user_obj, "id", None) or (
        user_obj.get("id") if isinstance(user_obj, dict) else None
    )
    email = getattr(user_obj, "email", None) or (
        user_obj.get("email") if isinstance(user_obj, dict) else None
    )

    if not user_id:
        return None

    raw = user_obj if isinstance(user_obj, dict) else getattr(user_obj, "dict", lambda: None)()
    return AuthUser(id=user_id, email=email, raw=raw)


# -----------------------------
# Core auth functions
# -----------------------------

def current_user() -> Optional[AuthUser]:
    supabase = get_supabase()
    sess = _session_from_state()
    if not sess:
        return None

    # Re-hydrate auth client (best-effort)
    try:
        access_token = sess.get("access_token")
        refresh_token = sess.get("refresh_token")
        if access_token and refresh_token:
            supabase.auth.set_session(access_token, refresh_token)
    except Exception:
        pass

    try:
        res = supabase.auth.get_user()
        user_obj = getattr(res, "user", None) or (res.get("user") if isinstance(res, dict) else None) or res
        return _to_auth_user(user_obj)
    except Exception:
        return None


SignUpOutcome = Literal["SIGNED_IN", "NEEDS_EMAIL_CONFIRMATION"]


def sign_up_email_password(email: str, password: str) -> SignUpOutcome:
    """
    Returns:
      - "SIGNED_IN" if email confirmation is OFF (session returned)
      - "NEEDS_EMAIL_CONFIRMATION" if confirmation is ON (no session returned)
    """
    supabase = get_supabase()

    res = supabase.auth.sign_up({"email": email, "password": password})

    # If email confirmation is ON, GoTrue typically returns user but NO session.
    session_obj = getattr(res, "session", None) or (res.get("session") if isinstance(res, dict) else None)

    if session_obj:
        if isinstance(session_obj, dict):
            sess = session_obj
        else:
            sess = getattr(session_obj, "dict", lambda: None)() or {}
        _set_session(sess)
        return "SIGNED_IN"

    return "NEEDS_EMAIL_CONFIRMATION"


def sign_in_email_password(email: str, password: str) -> None:
    supabase = get_supabase()
    res = supabase.auth.sign_in_with_password({"email": email, "password": password})

    session_obj = getattr(res, "session", None) or (res.get("session") if isinstance(res, dict) else None)
    if not session_obj:
        raise RuntimeError("No session returned from sign-in.")

    if isinstance(session_obj, dict):
        sess = session_obj
    else:
        sess = getattr(session_obj, "dict", lambda: None)() or {}

    _set_session(sess)


def sign_in_oauth(provider: str, redirect_to: Optional[str] = None) -> None:
    supabase = get_supabase()

    redirect = redirect_to or st.secrets.get("SITE_URL") or _default_site_url()

    res = supabase.auth.sign_in_with_oauth(
        {"provider": provider, "options": {"redirect_to": redirect}}
    )
    url = getattr(res, "url", None) or (res.get("url") if isinstance(res, dict) else None)
    if not url:
        raise RuntimeError("OAuth did not return a redirect URL.")

    st.markdown(f"<meta http-equiv='refresh' content='0; url={url}'>", unsafe_allow_html=True)
    st.stop()


def _default_site_url() -> str:
    return "http://localhost:8501"


def handle_oauth_callback() -> None:
    """
    Handles Supabase redirect back when access/refresh tokens are present
    (commonly in the hash fragment).
    """
    params = st.query_params

    if _session_from_state():
        return

    access = params.get("access_token")
    refresh = params.get("refresh_token")

    if access and refresh:
        _set_session({"access_token": access, "refresh_token": refresh})
        st.query_params.clear()
        return

    if st.session_state.get("_oauth_bridge_ran"):
        return

    st.session_state["_oauth_bridge_ran"] = True
    st.components.v1.html(
        """
<script>
(function () {
  const h = window.location.hash;
  if (!h || h.length < 2) return;
  const qp = new URLSearchParams(h.substring(1));
  const access = qp.get("access_token");
  const refresh = qp.get("refresh_token");
  if (!access || !refresh) return;

  const url = new URL(window.location.href);
  url.hash = "";
  url.searchParams.set("access_token", access);
  url.searchParams.set("refresh_token", refresh);
  window.location.replace(url.toString());
})();
</script>
        """,
        height=0,
    )


def sign_out() -> None:
    supabase = get_supabase()
    try:
        supabase.auth.sign_out()
    except Exception:
        pass
    _set_session(None)