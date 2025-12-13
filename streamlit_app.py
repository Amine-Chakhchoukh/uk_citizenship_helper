import streamlit as st
from datetime import date, datetime
from calculator import Trip, find_earliest_application_date, check_candidate_date
from st_supabase_connection import SupabaseConnection, execute_query


# -------------------------
# Helpers
# -------------------------

def format_date_uk(d: date) -> str:
    """Format with weekday in UK style, e.g. 'Tuesday 02/12/2025'."""
    return d.strftime("%A %d/%m/%Y")


# -------------------------
# Page + Supabase setup
# -------------------------

st.set_page_config(page_title="UK Citizenship Absence Checker", page_icon="🇬🇧")

# Initialise Supabase connection (cached by Streamlit; creds from .streamlit/secrets.toml)
supabase_conn = st.connection("supabase", type=SupabaseConnection, ttl=None)

# Small developer-only check so you can see if Supabase is alive
with st.expander("🐞 Developer debug: test Supabase connection"):
    try:
        rows = execute_query(
            supabase_conn.table("trips").select("*"),  # change to "mytable" if needed
            ttl="10m",
        )
        st.success("Connected to Supabase successfully 🎉")
        st.write("Rows from `trips` table (if any):")
        st.write(rows)
    except Exception as e:
        st.error("Could not connect to Supabase.")
        st.exception(e)


# -------------------------
# Title + intro
# -------------------------

st.title("🇬🇧🇮🇹 Ari's App — UK Citizenship Absence Checker")
st.caption("Helper for EU / EEA citizens with pre-settled or settled status.")

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
# 1. ENTER TRIPS
# -------------------------

st.header("1. Enter your trips outside the UK")

# First run in this browser session: try to load trips from Supabase
if "trips" not in st.session_state:
    try:
        resp = (
            supabase_conn
            .table("trips")                # Supabase table name
            .select("*")
            .order("start_date")
            .execute()
        )
        rows = resp.data or []

        trips = []
        for row in rows:
            start = row["start_date"]
            end = row["end_date"]

            # Supabase normally gives date objects, but be defensive
            if isinstance(start, str):
                start = datetime.fromisoformat(start).date()
            if isinstance(end, str):
                end = datetime.fromisoformat(end).date()

            note = row.get("note") or ""
            trips.append(Trip(start=start, end=end, note=note))

        st.session_state.trips = trips

    except Exception as e:
        st.session_state.trips = []
        st.warning(
            "Could not load saved trips from Supabase. "
            "Starting with an empty list instead."
        )

with st.form("add_trip_form"):
    col1, col2 = st.columns(2)

    start = col1.date_input(
        "Date you LEFT the UK",
        value=date.today(),
        format="DD/MM/YYYY",
    )

    end = col2.date_input(
        "Date you RETURNED to the UK",
        value=date.today(),
        format="DD/MM/YYYY",
    )

    note = st.text_input(
        "Optional note/label for this trip (e.g. 'Xmas at parents in Italy')",
        value="",
        placeholder="Trip to Paris, Xmas in Italy, Ibiza weekend…",
    )

    submitted = st.form_submit_button("Add trip")
    if submitted:
        if end < start:
            st.error("Return date cannot be before start date.")
        else:
            clean_note = note.strip()

            # 1) Add to local state
            new_trip = Trip(start=start, end=end, note=clean_note)
            st.session_state.trips.append(new_trip)

            label = f"{format_date_uk(start)} → {format_date_uk(end)}"
            if clean_note:
                label += f" — {clean_note}"
            st.success(f"Added trip: {label}")

            # 2) Persist to Supabase (best-effort)
            try:
                (
                    supabase_conn
                    .table("trips")
                    .insert(
                        {
                            "start_date": start.isoformat(),
                            "end_date": end.isoformat(),
                            "note": clean_note or None,
                        }
                    )
                    .execute()
                )
            except Exception as e:
                st.warning(
                    "Trip added locally but could not be saved to Supabase. "
                    f"(Details: {e})"
                )

# -------------------------
# 2. LIST TRIPS (NEWEST FIRST) + DELETE BUTTONS
# -------------------------

if st.session_state.trips:
    st.subheader("Your trips")

    # Keep original indices so delete works correctly
    indexed_trips = list(enumerate(st.session_state.trips))
    # Sort by start date DESC (newest first)
    indexed_trips.sort(key=lambda it: it[1].start, reverse=True)

    for display_idx, (orig_idx, t) in enumerate(indexed_trips, start=1):
        days = t.full_absence_days()

        col_trip, col_btn = st.columns([6, 1])

        with col_trip:
            title = (
                f"**Trip {display_idx}:** "
                f"{format_date_uk(t.start)} → {format_date_uk(t.end)}"
            )
            bullet_lines = []
            if getattr(t, "note", None):
                bullet_lines.append(f"- Note: _{t.note}_")
            bullet_lines.append(
                f"- Full days abroad counted as absences: **{days}**"
            )

            st.markdown(title + "\n" + "\n".join(bullet_lines))

        with col_btn:
            if st.button("Delete", key=f"del_{orig_idx}"):
                # Remove from local state using original index
                removed = st.session_state.trips.pop(orig_idx)

                # Also try to remove matching row(s) from Supabase
                try:
                    (
                        supabase_conn
                        .table("trips")
                        .delete()
                        .eq("start_date", removed.start)
                        .eq("end_date", removed.end)
                        .eq("note", removed.note or None)
                        .execute()
                    )
                except Exception as e:
                    st.warning(
                        "Trip deleted locally but could not be deleted from Supabase. "
                        f"(Details: {e})"
                    )

                st.rerun()

    with st.expander("How are absence days counted?"):
        st.markdown(
            """
### Home Office rule for counting absences

- Only **full days abroad** are counted.
- The day you **leave** the UK and the day you **return** do **not** count.
- This comes from the official nationality guidance (Guide AN, October 2025):

> “We only count whole days' absences from the UK.  
> We will not count the dates when you leave and enter the UK as absences.”

#### Examples
- Leave **1 Jan**, return **2 Jan** → **0 days** absent  
- Leave **1 Jan**, return **3 Jan** → **1 day** absent (2 Jan)  
- Leave **10 Jun**, return **20 Jun** → **9 days** absent (11–19 Jun)
            """
        )
else:
    st.info(
        "No trips added yet. Add at least one if you've ever left the UK in the last 5 years."
    )

# -------------------------
# 3. 'TODAY' + ABSENCE SUMMARY
# -------------------------

st.header("2. Choose 'today' and see your current position")

today = st.date_input(
    "Assume today's date is",
    value=date.today(),
    format="DD/MM/YYYY",
)
st.caption(f"Using today as: {format_date_uk(today)}")

if st.session_state.trips:
    summary = check_candidate_date(st.session_state.trips, candidate_date=today)

    st.markdown("#### Absence summary relative to this date")
    st.write(
        f"- Last 12 months: **{summary.days_12_months}** days (limit 90)"
    )
    st.write(
        f"- Last 5 years: **{summary.days_5_years}** days (limit 450)"
    )

    rem_12 = 90 - summary.days_12_months
    rem_5 = 450 - summary.days_5_years

    if rem_12 >= 0:
        st.write(
            f"- You can still be absent **{rem_12}** more days in the last 12 months before reaching 90."
        )
    else:
        st.write(
            f"- You are **{-rem_12}** days **over** the 90-day limit for the last 12 months."
        )

    if rem_5 >= 0:
        st.write(
            f"- You can still be absent **{rem_5}** more days in the last 5 years before reaching 450."
        )
    else:
        st.write(
            f"- You are **{-rem_5}** days **over** the 450-day limit for the last 5 years."
        )

# -------------------------
# 4. EARLIEST ELIGIBLE DATE
# -------------------------

st.header("3. Calculate earliest eligible application date")

if st.button("Calculate earliest eligible application date"):
    result = find_earliest_application_date(
        st.session_state.trips,
        today=today,
    )

    if result is None:
        st.error(
            "No eligible date found within the next 10 years based on the current trips."
        )
    else:
        st.success(
            f"### Earliest eligible date: **{format_date_uk(result.candidate_date)}**"
        )

        st.markdown("#### Breakdown for that date")
        st.write(
            f"- Absence days in the last 12 months: **{result.days_12_months}** (must be ≤ 90)"
        )
        st.write(
            f"- Absence days in the last 5 years: **{result.days_5_years}** (must be ≤ 450)"
        )
        st.write(
            f"- Date used for the '5 years ago' presence test: "
            f"**{format_date_uk(result.presence_date_5y)}**"
        )
        st.write(
            f"- Present in the UK on that test date: "
            f"**{'Yes' if result.present_on_presence_date else 'No'}**"
        )

        with st.expander("Why this specific '5 years ago' date?"):
            st.markdown(
                """
The Home Office requires you to have been **physically present in the UK**
on a specific date at the start of the 5-year qualifying period.

In the official guidance (Guide AN, October 2025), the example says:

> If your application is received on **05/01/2022**,  
> you should have been physically present in the UK on **06/01/2017**.

That corresponds to:

- Take the application date  
- Subtract **5 years**  
- Then move **one day forward**

This app follows that rule: the date shown above is exactly that
**Home Office test date**, and we check whether you were in the UK on it.
                """
            )

st.markdown("---")
st.caption(
    "This tool is for information only and does not constitute legal or immigration advice. "
    "Always check the latest rules on GOV.UK or with an immigration advisor."
)
