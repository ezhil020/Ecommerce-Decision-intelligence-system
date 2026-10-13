"""
Page 7 — AI Business Assistant (Powered by Ollama: Qwen2.5:3b)
"""
import streamlit as st
from config.settings import OLLAMA_BASE_URL, OLLAMA_MODEL
from agent.agent import get_agent
from views.ui_utils import section_header, COLORS, alert_banner


EXAMPLE_QUESTIONS = [
    "What was our total revenue and average order value?",
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
        'Natural-language business copilot powered locally by <b>Ollama (Qwen2.5:3b)</b>. '
        'Retrieves real database facts and synthesizes evidence-based answers.'
        '</p>',
        unsafe_allow_html=True,
    )

    agent = get_agent()
    is_connected, status_msg = agent.check_connection()

    if not is_connected:
        st.error(
            f"⚠️ **Ollama Service Not Reachable**\n\n"
            f"{status_msg}\n\n"
            f"**To get started:**\n"
            f"1. Ensure Ollama is running: `ollama serve`\n"
            f"2. Ensure the model is downloaded: `ollama pull {OLLAMA_MODEL}`\n"
            f"3. Configured host: `{OLLAMA_BASE_URL}`"
        )
        return

    # Engine Status Pill
    st.markdown(f"""
    <div style="
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: rgba(16, 185, 129, 0.1);
        border: 1px solid rgba(16, 185, 129, 0.25);
        border-radius: 20px;
        padding: 5px 14px;
        margin-bottom: 16px;
        font-size: 0.78rem;
        color: #6ee7b7;
    ">
        <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#10b981;box-shadow:0 0 8px #10b981;"></span>
        <b>Engine:</b> Ollama ({OLLAMA_MODEL}) &nbsp;|&nbsp; <b>Host:</b> {OLLAMA_BASE_URL} &nbsp;|&nbsp; <b>Privacy:</b> 100% Offline Local
    </div>
    """, unsafe_allow_html=True)

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
            placeholder="e.g. Which products need restocking? What is our net revenue and profit margin?",
            height=90,
            key="ai_query_input",
            value=st.session_state.pop("pending_query", ""),
        )
        submitted = st.form_submit_button("🔍 Investigate with Qwen2.5", use_container_width=True)

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

    with st.spinner("🤖 Investigating with Qwen2.5:3b… querying analytical database tools…"):
        try:
            agent = get_agent()
            result = agent.investigate(query)
        except Exception as e:
            st.error(f"Investigation failed: {e}")
            return

    entry = {
        "query": query,
        "answer": result["answer"],
        "tools_used": result["tools_used"],
        "error": result.get("error"),
    }
    st.session_state.chat_history.append(entry)
    st.rerun()


def _render_entry(entry: dict):
    """Render a single Q&A pair from chat history."""
    # User question
    st.markdown(f"""<div style="background:rgba(99,102,241,0.12);border-left:3px solid {COLORS['primary']};border-radius:8px;padding:12px 16px;margin:16px 0 8px;color:#e2e8f0;font-size:0.92rem;">
<strong>You:</strong> {entry['query']}
</div>""", unsafe_allow_html=True)

    # Tools used
    if entry.get("tools_used"):
        tool_badges = " ".join(
            f'<span style="background:rgba(139,92,246,0.2);color:#c4b5fd;'
            f'border:1px solid rgba(139,92,246,0.3);border-radius:20px;'
            f'padding:2px 10px;font-size:0.72rem;margin-right:4px">🔧 {t}</span>'
            for t in entry["tools_used"]
        )
        st.markdown(
            f'<div style="margin-bottom:8px;padding-left:4px">'
            f'<span style="color:#64748b;font-size:0.72rem">Database Tools Executed: </span>'
            f'{tool_badges}</div>',
            unsafe_allow_html=True,
        )

    # AI answer
    if entry.get("error"):
        st.error(entry["error"])
    else:
        st.markdown("""<div style="background:rgba(15,23,42,0.85);border:1px solid rgba(99,102,241,0.25);border-radius:10px;padding:18px 22px;margin-bottom:12px;color:#f1f5f9;">""", unsafe_allow_html=True)
        st.markdown(entry["answer"])
        st.markdown("</div>", unsafe_allow_html=True)
