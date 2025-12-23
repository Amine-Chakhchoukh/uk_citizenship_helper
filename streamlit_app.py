import re
from datetime import date

import streamlit as st
from st_supabase_connection import SupabaseConnection, execute_query

from calculator import find_earliest_application_date, check_candidate_date
from db import fetch_trips, insert_trip, delete_trip
from models import row_to_triprow
from auth import (
    handle_oauth_callback,
    current_user,
    sign_in_email_password,
    sign_up_email_password,
    sign_in_oauth,
    sign_out,
)

# Toggle for dev-only details (set in .streamlit/secrets.toml)
SHOW_DEV_DETAILS = bool(st.secrets.get("SHOW_DEV_DETAILS", False))


def format_date_uk(d: date) -> str:
    """Format date with weekday in UK style."""
    return d.strftime("%A %d/%m/%Y")


# -------------------------
# PAGE CONFIG
# -------------------------
st.set_page_config(page_title="UK Citizenship Absence Checker", page_icon="🇬🇧")

# -------------------------
# GLOBAL CSS
# -------------------------
st.markdown(
    """
    <style>
    /* Hide Streamlit's "Press Enter to submit form" hint */
    div[data-testid="InputInstructions"] {
        display: none !important;
    }

    /* Narrow + centre page like a real product */
    div.block-container {
        max-width: 880px;
        padding-top: 2.2rem;
    }

    /* ===== Fix ugly red focus borders (BaseWeb inputs) ===== */
    div[data-baseweb="base-input"] {
        border-radius: 12px !important;
        border: 1px solid #d1d5db !important;
        box-shadow: none !important;
    }

    div[data-baseweb="base-input"]:focus-within {
        border-color: #2563eb !important;
        box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.18) !important;
    }

    div[data-baseweb="base-input"] input {
        outline: none !important;
        box-shadow: none !important;
    }

    /* Buttons: softer, less Streamlit-y */
    div[data-testid="stButton"] > button {
        border-radius: 999px !important;
        padding: 0.65rem 1rem !important;
    }

    /* Reduce massive spacing around dividers */
    div[data-testid="stVerticalBlock"] > div:has(> hr) {
        margin-top: 0.6rem !important;
        margin-bottom: 0.6rem !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# -------------------------
# AUTH: handle OAuth redirect (Google)
# -------------------------
handle_oauth_callback()

# -------------------------
# SUPABASE CONNECTION (data)
# -------------------------
supabase = st.connection("supabase", type=SupabaseConnection)


# -------------------------
# Helper: friendlier auth errors
# -------------------------
def _friendly_auth_error(e: Exception) -> str:
    msg_raw = str(e)
    msg = msg_raw.lower()

    # Cooldown like: "you can only request this after 17 seconds."
    m = re.search(r"after\\s+(\\d+)\\s+seconds", msg)
    if m:
        secs = m.group(1)
        return f"Please wait {secs} seconds and try again."

    # Weak password
    if "password should be at least" in msg or "weakpassworderror" in msg:
        return "Password is too short. It must be at least 6 characters."

    # Email already has an account
    if "user already registered" in msg or "already been registered" in msg:
        return "This email already has an account. Please sign in (or reset your password)."

    # Generic rate limit
    if "rate limit" in msg or "too many requests" in msg or "429" in msg:
        return "Too many attempts in a short time. Please wait a bit and try again."

    # Email not confirmed yet
    if ("email not confirmed" in msg) or ("confirm" in msg and "email" in msg):
        return "Please confirm your email first (check your inbox), then sign in."

    # Wrong email / password
    if "invalid login credentials" in msg:
        return "Incorrect email or password."

    # Fallback
    return "Something went wrong. Please try again."


# -------------------------
# AUTH GATE
# -------------------------
user = current_user()

st.title("🇬🇧🇮🇹 Ari's App — UK Citizenship Absence Checker")
st.caption("Helper for EU / EEA citizens with pre-settled or settled status.")

if not user:
    st.info("Please sign in to view and save your trips.")

    if "auth_flash" in st.session_state:
        kind, msg = st.session_state.pop("auth_flash")
        if kind == "success":
            st.success(msg)
        elif kind == "info":
            st.info(msg)
        elif kind == "error":
            st.error(msg)

    if "auth_next_mode" in st.session_state:
        st.session_state["auth_mode"] = st.session_state.pop("auth_next_mode")

    left, mid, right = st.columns([1, 1.3, 1])

    with mid:
        auth_mode = st.radio(
            " ",
            ["Sign in", "Sign up"],
            horizontal=True,
            key="auth_mode",
        )

        if st.button("Continue with Google", use_container_width=True):
            sign_in_oauth("google")

        st.divider()
        st.caption("or")

        if auth_mode == "Sign in":
            with st.form("sign_in_form"):
                email = st.text_input("Email", placeholder="you@example.com")
                password = st.text_input(
                    "Password",
                    type="password",
                    placeholder="Your password",
                )
                submitted = st.form_submit_button("Sign in", use_container_width=True)

                if submitted:
                    try:
                        sign_in_email_password(email=email.strip(), password=password)
                        st.success("Signed in successfully.")
                        st.rerun()
                    except Exception as e:
                        st.error(_friendly_auth_error(e))
                        if SHOW_DEV_DETAILS:
                            with st.expander("Details (developer)"):
                                st.exception(e)

        else:
            with st.form("sign_up_form"):
                email = st.text_input("Email", placeholder="you@example.com", key="su_email")
                password = st.text_input(
                    "Password",
                    type="password",
                    key="su_pw",
                    help="At least 6 characters.",
                )
                password2 = st.text_input(
                    "Confirm password",
                    type="password",
                    key="su_pw2",
                )
                submitted = st.form_submit_button("Create account", use_container_width=True)

                if submitted:
                    if password != password2:
                        st.error("Passwords do not match.")
                    else:
                        try:
                            sign_up_email_password(email=email.strip(), password=password)
                            st.session_state["auth_flash"] = (
                                "success",
                                "Account created ✅\n\nCheck your inbox and click the confirmation link, then come back here and sign in.",
                            )
                            st.session_state["auth_next_mode"] = "Sign in"
                            st.rerun()
                        except Exception as e:
                            st.error(_friendly_auth_error(e))
                            if SHOW_DEV_DETAILS:
                                with st.expander("Details (developer)"):
                                    st.exception(e)

    st.stop()


# -------------------------
# SIDEBAR (LOGGED IN)
# -------------------------
with st.sidebar:
    st.markdown("### Account")
    st.write(f"Signed in as: **{user.email or '(no email)'}**")
    st.caption(f"User ID: {user.id}")
    if st.button("Sign out"):
        sign_out()
        st.rerun()


# -------------------------
# INTRO
# -------------------------
st.markdown(
    """
This tool estimates the **earliest date** you can apply for British citizenship based on:

- At most **90 days** outside the UK in the **last 12 months**
- At most **450 days** outside the UK in the **last 5 years**
- Being **physically present in the UK on the Home Office '5 years ago' test date**

It uses **whole days abroad** only — **departure and arrival days do *not* count** as absences.
"""
)


# -------------------------
# LOAD TRIPS FROM DB
# -------------------------
def refresh_trips_from_db():
    rows = fetch_trips(supabase, user_id=user.id)
    st.session_state.trip_rows = [row_to_triprow(r) for r in rows]


if "trip_rows" not in st.session_state:
    refresh_trips_from_db()


# -------------------------
# DEV DEBUG (USER-SCOPED)
# -------------------------
if SHOW_DEV_DETAILS:
    with st.expander("🐞 Developer debug: test Supabase connection"):
        try:
            rows = execute_query(
                supabase.table("trips")
                .select("*")
                .eq("user_id", user.id)
                .order("start_date", desc=True),
                ttl="10m",
            )
            st.success("Connected to Supabase successfully 🎉")
            st.write(rows)
        except Exception as e:
            st.error("Could not connect to Supabase.")
            st.exception(e)


# -------------------------
# 1. SHOW SAVED TRIPS
# -------------------------
st.header("1. Your saved trips")

if st.session_state.trip_rows:
    for idx, triprow in enumerate(st.session_state.trip_rows, start=1):
        t = triprow.trip
        days = t.full_absence_days()

        col_trip, col_btn = st.columns([6, 1])

        with col_trip:
            st.markdown(
                f"**Trip {idx}:** {format_date_uk(t.start)} → {format_date_uk(t.end)}"
            )
            st.write(f"- Full days abroad counted as absences: **{days}**")
            if t.note:
                st.write(f"- Note: _{t.note}_")

        with col_btn:
            if st.button("Delete", key=f"del_{triprow.id}"):
                delete_trip(supabase, triprow.id, user_id=user.id)
                refresh_trips_from_db()
                st.rerun()
else:
    st.info("No saved trips yet.")


# -------------------------
# 2. ADD NEW TRIP
# -------------------------
st.header("2. Add a new trip")

with st.form("add_trip_form"):
    col1, col2 = st.columns(2)

    start = col1.date_input("Date you LEFT the UK", value=date.today(), format="DD/MM/YYYY")
    end = col2.date_input("Date you RETURNED to the UK", value=date.today(), format="DD/MM/YYYY")

    note = st.text_input(
        "Optional note",
        placeholder="Xmas with parents, Ibiza trip, work travel…",
    )
    submitted = st.form_submit_button("Add trip")

    if submitted:
        if end < start:
            st.error("Return date cannot be before start date.")
        else:
            insert_trip(
                supabase,
                start=start,
                end=end,
                note=note.strip(),
                user_id=user.id,
            )
            refresh_trips_from_db()
            st.success("Trip added.")
            st.rerun()


# -------------------------
# 3. ABSENCE SUMMARY
# -------------------------
st.header("3. Choose 'today' and see your current position")

today = st.date_input("Assume today's date is", value=date.today(), format="DD/MM/YYYY")
st.caption(f"Using today as: {format_date_uk(today)}")

trips_for_calc = [tr.trip for tr in st.session_state.trip_rows]

if trips_for_calc:
    summary = check_candidate_date(trips_for_calc, candidate_date=today)
    st.write(f"- Last 12 months: **{summary.days_12_months}** / 90")
    st.write(f"- Last 5 years: **{summary.days_5_years}** / 450")
else:
    st.info("Add trips to see your absence summary.")


# -------------------------
# 4. EARLIEST ELIGIBLE DATE
# -------------------------
st.header("4. Calculate earliest eligible application date")

if st.button("Calculate earliest eligible application date"):
    result = find_earliest_application_date(trips_for_calc, today=today)

    if not result:
        st.error("No eligible date found within the next 10 years.")
    else:
        st.success(f"### Earliest eligible date: **{format_date_uk(result.candidate_date)}**")
        st.write(f"- Absences (12 months): **{result.days_12_months}**")
        st.write(f"- Absences (5 years): **{result.days_5_years}**")
        st.write(f"- Home Office presence test date: **{format_date_uk(result.presence_date_5y)}**")
        st.write(
            f"- Present in UK on that date: **{'Yes' if result.present_on_presence_date else 'No'}**"
        )

st.markdown("---")
st.caption(
    "This tool is for information only and does not constitute legal or immigration advice."
)