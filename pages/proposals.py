"""
Proposals page of the MarkeTan dashboard: review, copy, and track proposals
generated for clinics that have replied.
"""
import streamlit as st

from db import get_connection
from config import APP_PASSWORD

st.set_page_config(page_title="MarkeTan Proposals", layout="wide")

if APP_PASSWORD:
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        st.title("MarkeTan Proposals")
        entered = st.text_input("Password", type="password")
        if st.button("Enter"):
            if entered == APP_PASSWORD:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Incorrect password")
        st.stop()

st.title("Proposals")
st.caption("Generated proposals for clinics that have replied. Review, copy, and send.")

STATUS_OPTIONS = ["draft", "sent", "accepted", "declined"]


@st.cache_data(ttl=30)
def load_proposals():
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT p.id, p.package_recommended, p.body, p.status, p.created_at,
               c.name AS clinic_name, c.city
        FROM proposals p
        JOIN clinics c ON c.id = p.clinic_id
        ORDER BY p.created_at DESC
        """
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_status(proposal_id, new_status):
    conn = get_connection()
    conn.execute(
        "UPDATE proposals SET status = ? WHERE id = ?",
        (new_status, proposal_id),
    )
    conn.commit()
    conn.close()


proposals = load_proposals()

if not proposals:
    st.info("No proposals yet. These are generated automatically when a clinic's "
             "status is marked 'Replied' on the Prospects page.")
else:
    col1, col2, col3, col4 = st.columns(4)
    for col, status in zip([col1, col2, col3, col4], STATUS_OPTIONS):
        count = sum(1 for p in proposals if p["status"] == status)
        col.metric(status.title(), count)

    st.divider()
    st.write(f"Showing {len(proposals)} proposal(s)")

    for proposal in proposals:
        with st.container(border=True):
            left, right = st.columns([3, 1])

            with left:
                st.subheader(proposal["clinic_name"])
                st.caption(f"{proposal['city']} — Recommended package: {proposal['package_recommended']}")
                st.code(proposal["body"], language=None, wrap_lines=True)

            with right:
                current = proposal["status"]
                new_status = st.selectbox(
                    "Status",
                    options=STATUS_OPTIONS,
                    index=STATUS_OPTIONS.index(current) if current in STATUS_OPTIONS else 0,
                    key=f"proposal_status_{proposal['id']}",
                )
                if new_status != current:
                    update_status(proposal["id"], new_status)
                    st.cache_data.clear()
                    st.rerun()
