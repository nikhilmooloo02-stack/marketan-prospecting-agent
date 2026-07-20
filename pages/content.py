"""
Content page of the MarkeTan dashboard: review, copy, and track generated
social media content.
"""
import streamlit as st

from db import get_connection

st.set_page_config(page_title="MarkeTan Content", layout="wide")
st.title("Content Library")
st.caption("Generated posts for MarkeTan's channels. Review, copy, post, and mark as used.")

STATUS_OPTIONS = ["draft", "posted", "discarded"]
TYPE_LABELS = {
    "educational": "📚 Educational",
    "promotional": "📣 Promotional",
    "demo": "🎯 Demo (sample clinic content)",
}


@st.cache_data(ttl=30)
def load_content():
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT id, content_type, platform, body, status, created_at
        FROM content
        ORDER BY created_at DESC
        """
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_status(content_id, new_status):
    conn = get_connection()
    conn.execute(
        "UPDATE content SET status = ? WHERE id = ?",
        (new_status, content_id),
    )
    conn.commit()
    conn.close()


posts = load_content()

# --- Summary ---
col1, col2, col3 = st.columns(3)
for col, status in zip([col1, col2, col3], STATUS_OPTIONS):
    count = sum(1 for p in posts if p["status"] == status)
    col.metric(status.title(), count)

st.divider()

# --- Filters ---
fcol1, fcol2 = st.columns(2)
with fcol1:
    type_filter = st.selectbox(
        "Content type",
        options=["All"] + list(TYPE_LABELS.keys()),
        format_func=lambda x: TYPE_LABELS.get(x, x),
    )
with fcol2:
    status_filter = st.selectbox("Status", options=["draft"] + [s for s in STATUS_OPTIONS if s != "draft"] + ["All"])

filtered = posts
if type_filter != "All":
    filtered = [p for p in filtered if p["content_type"] == type_filter]
if status_filter != "All":
    filtered = [p for p in filtered if p["status"] == status_filter]

st.write(f"Showing {len(filtered)} post(s)")

# --- Content list ---
for post in filtered:
    with st.container(border=True):
        left, right = st.columns([3, 1])

        with left:
            st.caption(f"{TYPE_LABELS.get(post['content_type'], post['content_type'])} — {post['platform'].title()}")
            st.code(post["body"], language=None, wrap_lines=True)

        with right:
            current = post["status"]
            new_status = st.selectbox(
                "Status",
                options=STATUS_OPTIONS,
                index=STATUS_OPTIONS.index(current) if current in STATUS_OPTIONS else 0,
                key=f"content_status_{post['id']}",
            )
            if new_status != current:
                update_status(post["id"], new_status)
                st.cache_data.clear()
                st.rerun()