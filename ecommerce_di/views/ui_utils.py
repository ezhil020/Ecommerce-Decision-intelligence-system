"""
Shared UI utilities: formatting, chart themes, KPI cards.
"""
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

# ── Color palette ─────────────────────────────────────────────────────────────
COLORS = {
    "primary":   "#6366f1",   # indigo
    "secondary": "#8b5cf6",   # violet
    "success":   "#10b981",   # emerald
    "warning":   "#f59e0b",   # amber
    "danger":    "#ef4444",   # red
    "info":      "#3b82f6",   # blue
    "muted":     "#94a3b8",   # slate
}

CHART_BG    = "rgba(0,0,0,0)"
GRID_COLOR  = "rgba(255,255,255,0.07)"
TEXT_COLOR  = "#e2e8f0"

CATEGORY_COLORS = px.colors.qualitative.Vivid


def chart_layout(fig: go.Figure, title: str = "", height: int = 380) -> go.Figure:
    """Apply consistent dark theme to every chart."""
    fig.update_layout(
        title=dict(text=title, font=dict(size=15, color=TEXT_COLOR, family="Inter")),
        paper_bgcolor=CHART_BG,
        plot_bgcolor=CHART_BG,
        font=dict(color=TEXT_COLOR, family="Inter, sans-serif", size=12),
        height=height,
        margin=dict(l=16, r=16, t=44, b=16),
        legend=dict(
            bgcolor="rgba(30,30,50,0.6)",
            bordercolor="rgba(255,255,255,0.1)",
            borderwidth=1,
            font=dict(size=11),
        ),
        xaxis=dict(
            gridcolor=GRID_COLOR,
            linecolor="rgba(255,255,255,0.1)",
            tickfont=dict(size=11),
            showgrid=False,
        ),
        yaxis=dict(
            gridcolor=GRID_COLOR,
            linecolor=GRID_COLOR,
            tickfont=dict(size=11),
            showgrid=True,
        ),
        hoverlabel=dict(
            bgcolor="rgba(15,15,30,0.95)",
            bordercolor="rgba(99,102,241,0.5)",
            font=dict(color="#f8fafc", size=12),
        ),
    )
    return fig


# ── Number formatting ─────────────────────────────────────────────────────────

def fmt_currency(val: float, symbol: str = "₹") -> str:
    if val is None:
        return "—"
    if abs(val) >= 1_00_00_000:   # crore
        return f"{symbol}{val/1_00_00_000:.2f} Cr"
    if abs(val) >= 1_00_000:      # lakh
        return f"{symbol}{val/1_00_000:.2f} L"
    if abs(val) >= 1_000:
        return f"{symbol}{val/1_000:.1f} K"
    return f"{symbol}{val:,.0f}"


def fmt_number(val: float) -> str:
    if val is None:
        return "—"
    if abs(val) >= 1_00_00_000:
        return f"{val/1_00_00_000:.2f} Cr"
    if abs(val) >= 1_00_000:
        return f"{val/1_00_000:.2f} L"
    if abs(val) >= 1_000:
        return f"{val/1_000:.1f} K"
    return f"{val:,.0f}"


def fmt_pct(val: float) -> str:
    if val is None:
        return "—"
    return f"{val*100:.1f}%" if abs(val) <= 1 else f"{val:.1f}%"


def delta_badge(change: float | None) -> str:
    if change is None:
        return ""
    pct = change * 100
    icon = "↑" if pct >= 0 else "↓"
    color = "#10b981" if pct >= 0 else "#ef4444"
    return f'<span style="color:{color};font-size:0.78rem;font-weight:600">{icon} {abs(pct):.1f}%</span>'


# ── KPI card ──────────────────────────────────────────────────────────────────

def kpi_card(title: str, value: str, subtitle: str = "", delta_html: str = "",
             icon: str = "📊", accent: str = COLORS["primary"]):
    html = f"""
<div style="
background: linear-gradient(135deg,rgba(30,30,60,0.85),rgba(20,20,45,0.9));
border: 1px solid rgba(99,102,241,0.2);
border-left: 3px solid {accent};
border-radius: 12px;
padding: 18px 20px 14px;
margin-bottom: 4px;
box-shadow: 0 4px 20px rgba(0,0,0,0.3);
">
<div style="font-size:1.4rem;margin-bottom:4px">{icon}</div>
<div style="color:#94a3b8;font-size:0.72rem;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:4px">{title}</div>
<div style="color:#f1f5f9;font-size:1.55rem;font-weight:700;line-height:1.1">{value}</div>
{f'<div style="margin-top:6px">{delta_html}</div>' if delta_html else ''}
{f'<div style="color:#64748b;font-size:0.7rem;margin-top:3px">{subtitle}</div>' if subtitle else ''}
</div>
"""
    st.markdown(html, unsafe_allow_html=True)


# ── Section header ────────────────────────────────────────────────────────────

def section_header(title: str, subtitle: str = ""):
    html = f"""
<div style="margin: 24px 0 16px">
<h3 style="color:#e2e8f0;margin:0;font-size:1.1rem;font-weight:600">{title}</h3>
{f'<p style="color:#64748b;font-size:0.8rem;margin:2px 0 0">{subtitle}</p>' if subtitle else ''}
</div>
"""
    st.markdown(html, unsafe_allow_html=True)


# ── Empty state ───────────────────────────────────────────────────────────────

def empty_state(message: str, icon: str = "📭"):
    html = f"""
<div style="
text-align:center;padding:48px 24px;
background:rgba(30,30,60,0.5);
border:1px dashed rgba(99,102,241,0.2);
border-radius:12px;margin:16px 0;
">
<div style="font-size:2.5rem;margin-bottom:12px">{icon}</div>
<div style="color:#64748b;font-size:0.9rem">{message}</div>
</div>
"""
    st.markdown(html, unsafe_allow_html=True)


# ── Alert banner ──────────────────────────────────────────────────────────────

def alert_banner(msg: str, kind: str = "warning"):
    color_map = {"warning": "#f59e0b", "error": "#ef4444",
                 "info": "#3b82f6", "success": "#10b981"}
    color = color_map.get(kind, "#6366f1")
    html = f"""
<div style="
background: rgba(0,0,0,0.3);
border-left: 3px solid {color};
border-radius: 6px;padding: 10px 14px;
margin:8px 0;color:#e2e8f0;font-size:0.85rem;
">{msg}</div>
"""
    st.markdown(html, unsafe_allow_html=True)
