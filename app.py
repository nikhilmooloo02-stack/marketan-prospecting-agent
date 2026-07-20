"""
MarkeTan Prospecting Dashboard — Streamlit app.

Shows good-fit clinics with their outreach drafts, and lets the user update
each clinic's outreach status directly from the browser (no command line).

Run locally with: streamlit run app.py
"""
import streamlit as st

from db import get_connection

st.set_page_config(page_title="MarkeTan Prospects", layout="wide")
st.title("MarkeTan Prospecting Dashboard")
st.caption("Clinics found and scored against MarkeTan's ideal-client profile.")

STATUS_OPTIONS = ["not_contacted", "sent", "replied", "booked", "declined"]


@st.cache_data(ttl=30)
def load_clinics():
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT id, name, city, fit_score, fit_reasoning,
               outreach_status, outreach_message
        FROM clinics
        WHERE fit_label = 'good_fit' AND outreach_status != 'duplicate'
        ORDER BY fit_score DESC
        """
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_status(clinic_id, new_status):
    conn = get_connection()
    conn.execute(
        "UPDATE clinics SET outreach_status = ? WHERE id = ?",
        (new_status, clinic_id),
    )
    conn.commit()
    conn.close()


clinics = load_clinics()

# --- Summary counts ---
col1, col2, col3, col4, col5 = st.columns(5)
for col, status in zip([col1, col2, col3, col4, col5], STATUS_OPTIONS):
    count = sum(1 for c in clinics if c["outreach_status"] == status)
    col.metric(status.replace("_", " ").title(), count)

st.divider()

# --- Filter ---
city_filter = st.selectbox(
    "Filter by city",
    options=["All"] + sorted(set(c["city"] for c in clinics if c["city"])),
)

filtered = clinics if city_filter == "All" else [c for c in clinics if c["city"] == city_filter]

st.write(f"Showing {len(filtered)} clinic(s)")

# --- Clinic list ---
for clinic in filtered:
    with st.container(border=True):
        left, right = st.columns([3, 1])

        with left:
            st.subheader(clinic["name"])
            st.caption(f"{clinic['city']} — Fit score: {clinic['fit_score']}/100")
            st.write(f"**Why it's a fit:** {clinic['fit_reasoning']}")
            with st.expander("Outreach message"):
                st.write(clinic["outreach_message"])

        with right:
            current = clinic["outreach_status"]
            new_status = st.selectbox(
                "Status",
                options=STATUS_OPTIONS,
                index=STATUS_OPTIONS.index(current) if current in STATUS_OPTIONS else 0,
                key=f"status_{clinic['id']}",
            )
            if new_status != current:
                update_status(clinic["id"], new_status)
                st.cache_data.clear()
                st.rerun()