"""
Page 7 — AI Business Assistant
"""
import json
import streamlit as st
from config.settings import GEMINI_API_KEY
from pages.ui_utils import section_header, COLORS, alert_banner


EXAMPLE_QUESTIONS = [
    "Why did sales fall this month?",
    "Which products need immediate restocking?",
    "Which category generated the highest profit?",
    "Which payment method has the most failures?",
    "Which products have high sales but low margins?",
    "Show me customers contributing the most revenue.",
    "Are there any unusual patterns in refunds?",
    "What does the next 6 months revenue look like?",
    "Which state generates the most revenue?",
    "Compare Q1 vs Q2 performance.",
]


def render(filters: dict):
    st.markdown("## AI Business Assistant")
    st.markdown(
        '<p style="color:#64748b;font-size:0.85rem;margin-top:-12px">'
        'Ask natural-language questions — the agent retrieves real data and provides evidence-based answers.'
        '</p>',
        unsafe_allow_html=True,
    )

    if not GEMINI_API_KEY:
        st.error(
            "🔑 **GEMINI_API_KEY not configured.**\n\n"
            "Please add your Google Gemini API key to the `.env` file:\n\n"
            "```\nGEMINI_API_KEY=your_key_here\n```\n\n"
            "Get a free key at [Google AI Studio](https://aistudio.google.com/)."
        )
        return

    # ── Chat history ───────────────────────────────────────────────────────────
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # ── Example questions ──────────────────────────────────────────────────────
    with st.expander("💡 Example questions to try", expanded=False):
        cols = st.columns(2)
        for i, q in enumerate(EXAMPLE_QUESTIONS):
            with cols[i % 2]:
                if st.button(q, key=f"eq_{i}", use_container_width=True):
                    st.session_state.pending_query = q

    # ── Input ──────────────────────────────────────────────────────────────────
    with st.form("ai_query_form", clear_on_submit=True):
        query = st.text_area(
            "Ask a business question",
            placeholder="e.g. Why did sales fall this month? Which products need restocking?",
            height=90,
            key="ai_query_input",
            value=st.session_state.pop("pending_query", ""),
        )
        submitted = st.form_submit_button("🔍 Investigate", use_container_width=True)

    if submitted and query.strip():
        _run_investigation(query.strip())

    # ── Chat history ───────────────────────────────────────────────────────────
    if st.session_state.chat_history:
        if st.button("🗑️ Clear conversation", key="clear_chat"):
            st.session_state.chat_history = []
            st.rerun()

        for entry in reversed(st.session_state.chat_history):
            _render_entry(entry)


def _run_investigation(query: str):
    """Run AI investigation and render result."""
    from agent.agent import get_agent

    with st.spinner("🤖 Investigating… querying analytical tools…"):
        try:
            agent = get_agent()
            result = agent.investigate(query)
        except ValueError as e:
            st.error(str(e))
            return
        except Exception as e:
            st.error(f"Investigation failed: {e}")
            return

    entry = {
        "query":       query,
        "answer":      result["answer"],
        "tools_used":  result["tools_used"],
        "error":       result.get("error"),
    }
    st.session_state.chat_history.append(entry)
    st.rerun()


def _render_entry(entry: dict):
    """Render a single Q&A pair from chat history."""
    # User question
    st.markdown(f"""
    <div style="
        background: rgba(99,102,241,0.12);
        border-left: 3px solid {COLORS['primary']};
        border-radius: 8px;
        padding: 12px 16px;
        margin: 16px 0 8px;
        color: #e2e8f0;
        font-size: 0.92rem;
    ">
        <strong>You:</strong> {entry['query']}
    </div>
    """, unsafe_allow_html=True)

    # Tools used
    if entry.get("tools_used"):
        tool_badges = " ".join(
            f'<span style="background:rgba(139,92,246,0.2);color:#c4b5fd;'
            f'border:1px solid rgba(139,92,246,0.3);border-radius:20px;'
            f'padding:2px 10px;font-size:0.72rem;margin-right:4px">{t}</span>'
            for t in entry["tools_used"]
        )
        st.markdown(
            f'<div style="margin-bottom:8px;padding-left:4px">'
            f'<span style="color:#64748b;font-size:0.72rem">Tools used: </span>'
            f'{tool_badges}</div>',
            unsafe_allow_html=True,
        )

    # AI answer
    if entry.get("error"):
        st.error(entry["error"])
    else:
        st.markdown(f"""
        <div style="
            background: rgba(15,15,35,0.8);
            border: 1px solid rgba(99,102,241,0.2);
            border-radius: 10px;
            padding: 16px 20px;
            margin-bottom: 8px;
            color: #e2e8f0;
            font-size: 0.88rem;
            line-height: 1.7;
        ">
            {entry['answer'].replace(chr(10), '<br>')}
        </div>
        """, unsafe_allow_html=True)
