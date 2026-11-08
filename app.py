"""
אבחון שלב חברה – לפי מסגרת "האבולוציה של חברה" (סטארטאפ → צמיחה → ערך).
הרצה:  streamlit run app.py
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import analysis
import sec_data
from analysis import STAGES, Config

st.set_page_config(page_title="אבחון שלב חברה", page_icon="📈", layout="wide")

# ---------------------------------------------------------------------------
# עיצוב RTL
# ---------------------------------------------------------------------------
st.markdown(
    """
<style>
html, body, [data-testid="stAppViewContainer"], [data-testid="stSidebar"] { direction: rtl; }
[data-testid="stMarkdownContainer"], .stTextInput, .stSlider, .stExpander, .stTabs { direction: rtl; text-align: right; }
[data-testid="stMetricValue"], [data-testid="stMetricDelta"] { direction: ltr; text-align: right; }
.ltr { direction: ltr; unicode-bidi: embed; display: inline-block; }
.stage-card { border-radius: 14px; padding: 18px 22px; color: white; margin-bottom: 8px; }
.stage-card h2 { margin: 0 0 6px 0; color: white; font-size: 1.7rem; }
.stage-card p { margin: 0; font-size: 0.98rem; line-height: 1.55; opacity: 0.95; }
.badge { display:inline-block; padding: 3px 10px; border-radius: 999px; font-size: 0.85rem;
         background: rgba(255,255,255,0.22); margin-top: 10px; margin-left: 6px; }
.risk-row { display:flex; justify-content:space-between; gap:12px; padding:6px 0;
            border-bottom: 1px solid rgba(128,128,128,0.18); }
.risk-pts { font-weight: 700; direction: ltr; min-width: 42px; text-align:left; }
.small-note { font-size: 0.85rem; opacity: 0.7; }
</style>
""",
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# פורמט
# ---------------------------------------------------------------------------
def money(x, cur="USD"):
    if x is None or (isinstance(x, float) and (np.isnan(x) or np.isinf(x))):
        return "—"
    sym = "\u200e$" if cur == "USD" else f"\u200e{cur} "
    a = abs(x)
    sign = "-" if x < 0 else ""
    if a >= 1e12:
        return f"{sign}{sym}{a/1e12:.2f}T"
    if a >= 1e9:
        return f"{sign}{sym}{a/1e9:.2f}B"
    if a >= 1e6:
        return f"{sign}{sym}{a/1e6:.1f}M"
    if a >= 1e3:
        return f"{sign}{sym}{a/1e3:.0f}K"
    return f"{sign}{sym}{a:.0f}"


def pct(x, plus=True):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "—"
    if np.isinf(x):
        return "מאפס"
    return "\u200e" + (f"{x:+.0%}" if plus else f"{x:.0%}")


def num(x, d=1):
    if x is None or (isinstance(x, float) and (np.isnan(x) or np.isinf(x))):
        return "—"
    return f"{x:,.{d}f}"


def months(x):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "—"
    if x >= 120:
        return "10+ שנים"
    return f"{x:.0f} חודשים"


# ---------------------------------------------------------------------------
# נתונים (עם cache)
# ---------------------------------------------------------------------------
@st.cache_data(ttl=7 * 86400, show_spinner=False)
def cached_ticker_map(ua):
    return sec_data.load_ticker_map(ua)


@st.cache_data(ttl=12 * 3600, show_spinner=False)
def cached_facts(cik, ua):
    return sec_data.fetch_company_facts(cik, ua)


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def cached_prices(ticker):
    return sec_data.fetch_prices(ticker)


def load(ticker, ua):
    ticker = ticker.strip().upper()
    tmap = cached_ticker_map(ua)
    key = ticker if ticker in tmap else ticker.replace(".", "-")
    if key not in tmap:
        raise sec_data.SecError(
            f"הטיקר {ticker} לא נמצא ברשימת ה-SEC. הכלי תומך בחברות שמגישות דוחות ל-SEC "
            "(נסחרות בארה\"ב). מניות שנסחרות רק בתל אביב אינן נתמכות."
        )
    info = tmap[key]
    facts = cached_facts(info["cik"], ua)
    data = sec_data.build_company_data(facts, ticker, facts.get("entityName") or info["name"], info["cik"])
    prices, last, mcap = cached_prices(ticker)
    data.prices, data.last_price = prices, last
    if mcap is None and last is not None and "shares" in data.balance and data.balance["shares"].notna().any():
        mcap = last * float(data.balance["shares"].dropna().iloc[-1])
    data.market_cap = mcap
    if prices is None:
        data.warnings.append("לא הצלחתי למשוך מחירים מ-yfinance – מדדי שווי ותשואה לא יוצגו.")
    return data


# ---------------------------------------------------------------------------
# סרגל צד
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ הגדרות")
    default_ua = os.environ.get("SEC_USER_AGENT", "")
    try:
        default_ua = default_ua or st.secrets.get("SEC_USER_AGENT", "")
    except Exception:
        pass
    ua = st.text_input(
        "User-Agent ל-SEC (שם + מייל)",
        value=default_ua or sec_data.DEFAULT_UA,
        help="SEC מבקשת שכל בקשה תזדהה בשם ומייל. לדוגמה: 'Shimon research shimon@mail.com'",
    )
    if "example.com" in ua:
        st.caption("💡 מומלץ להחליף לשם ומייל שלך – SEC עלולה לחסום זיהוי גנרי.")
    with st.expander("ספי אבחון (מתקדם)"):
        st.caption("ספים שקבענו לפי ההיגיון בסרטון. אפשר לשנות לפי שיקול דעתך.")
        cfg = Config(
            startup_rev=st.number_input("הכנסות שנתיות מתחתן = סטארטאפ ($M)", 1, 500, 25) * 1e6,
            early_rev=st.number_input("סף 'חברה צעירה' למעבר סטארטאפ→צמיחה ($M)", 50, 5000, 1000) * 1e6,
            growth_min=st.slider("צמיחה שנתית מינימלית לחברת צמיחה", 0.05, 0.60, 0.20, 0.01),
            value_max=st.slider("צמיחה מקסימלית לחברת ערך", 0.0, 0.20, 0.08, 0.01),
            approaching_q=st.slider("'מתקרבת לרווח' = רווח צפוי תוך X רבעונים", 1, 8, 4),
        )
    st.divider()
    st.caption(
        "מקורות: דוחות XBRL רשמיים מ-SEC EDGAR, מחירים מ-Yahoo Finance (yfinance). "
        "אין צורך במפתח API."
    )
    if st.button("נקה cache"):
        st.cache_data.clear()
        st.success("נוקה")

# ---------------------------------------------------------------------------
# קלט
# ---------------------------------------------------------------------------
st.title("📈 אבחון שלב חברה")
st.markdown("סטארטאפ ← צמיחה ← ערך: באיזה שלב באבולוציה החברה נמצאת, ומה רמת הסיכון ביחס לשלב.")

examples = ["ASTS", "QS", "TE", "LMND", "PLTR", "SOFI", "HOOD", "KO"]
if "ticker_input" not in st.session_state:
    st.session_state.ticker_input = ""


def _set_ticker(t):
    st.session_state.ticker_input = t


c1, c2 = st.columns([3, 1])
with c1:
    st.text_input("טיקר", key="ticker_input", placeholder="לדוגמה: LMND", label_visibility="collapsed")
with c2:
    st.button("אבחן", type="primary", width="stretch")

ex_cols = st.columns(len(examples))
for col, ex in zip(ex_cols, examples):
    col.button(ex, width="stretch", on_click=_set_ticker, args=(ex,))

ticker = st.session_state.ticker_input.strip().upper()
if not ticker:
    st.info("הכנס טיקר של חברה שנסחרת בארה\"ב, או בחר אחת מהדוגמאות מהסרטון.")
    st.stop()

try:
    with st.spinner(f"מושך דוחות של {ticker} מ-SEC…"):
        data = load(ticker, ua)
        dg = analysis.diagnose(data, cfg)
except sec_data.SecError as e:
    st.error(str(e))
    st.stop()
except Exception as e:
    st.error(f"שגיאה לא צפויה: {e}")
    st.stop()

L = dg.latest
cur = data.currency

# ---------------------------------------------------------------------------
# כותרת
# ---------------------------------------------------------------------------
qe = L["quarter_end"]
st.subheader(f"{data.name}  ·  {data.ticker}")
st.markdown(
    f"<span class='small-note'>רבעון אחרון מדווח: <span class='ltr'>{qe.date() if qe is not None else '—'}</span>"
    f"  ·  מחיר: <span class='ltr'>{('$' + format(data.last_price, ',.2f')) if data.last_price else '—'}</span>"
    f"  ·  שווי שוק: <span class='ltr'>{money(data.market_cap)}</span></span>",
    unsafe_allow_html=True,
)
for w in data.warnings:
    st.warning(w)

# ---------------------------------------------------------------------------
# כרטיס שלב + סיכון
# ---------------------------------------------------------------------------
left, right = st.columns([3, 2])
with left:
    color = STAGES[dg.stage]["color"]
    badges = ""
    if dg.approaching_profit:
        badges += f"<span class='badge'>⏳ מתקרבת לרווח נקי (~{dg.breakeven['months']} חודשים לפי המגמה)</span>"
    if dg.runway["self_funded"]:
        badges += "<span class='badge'>💰 מממנת את עצמה</span>"
    elif dg.runway["months_fcf"] is not None:
        badges += f"<span class='badge'>🔥 קופה ל-{months(dg.runway['months_fcf'])}</span>"
    st.markdown(
        f"<div class='stage-card' style='background:{color}'>"
        f"<div style='font-size:0.9rem;opacity:0.85'>השלב באבולוציה</div>"
        f"<h2>{dg.stage_he}</h2><p>{dg.explain}</p>{badges}</div>",
        unsafe_allow_html=True,
    )

with right:
    risk_color = "#22C55E" if dg.risk_score < 25 else "#F59E0B" if dg.risk_score < 50 else "#EF4444" if dg.risk_score < 75 else "#991B1B"
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=dg.risk_score,
        number={"suffix": " / 100"},
        title={"text": f"רמת סיכון: {dg.risk_level}"},
        gauge={
            "axis": {"range": [0, 100]},
            "bar": {"color": risk_color},
            "steps": [
                {"range": [0, 25], "color": "rgba(34,197,94,0.15)"},
                {"range": [25, 50], "color": "rgba(245,158,11,0.15)"},
                {"range": [50, 75], "color": "rgba(239,68,68,0.15)"},
                {"range": [75, 100], "color": "rgba(153,27,27,0.2)"},
            ],
        },
    ))
    fig.update_layout(height=230, margin=dict(l=20, r=20, t=50, b=0))
    st.plotly_chart(fig, width="stretch")

# ---------------------------------------------------------------------------
# מדדים
# ---------------------------------------------------------------------------
m1, m2, m3, m4, m5 = st.columns(5)
g_now = L["revenue_yoy"]
m1.metric("הכנסות (12 ח')", money(L["revenue_ttm"], cur),
          (pct(g_now) + " בשנה") if g_now is not None and not pd.isna(g_now) else None)
m2.metric(f"רווח נקי (12 ח') · שולי רווח {pct(L['net_margin_ttm'], False)}", money(L["net_income_ttm"], cur))
m3.metric("תזרים חופשי (12 ח')", money(L["fcf_ttm"], cur))
m4.metric("מזומן + ני\"ע", money(L["liquid"], cur))
m5.metric("חוב פיננסי", money(L["debt"], cur))

m6, m7, m8, m9, m10 = st.columns(5)
m6.metric("קופה (לפי תזרים)", "לא שורפת ✓" if dg.runway["self_funded"] else months(dg.runway["months_fcf"]))
m7.metric("דילול שנתי", pct(L["dilution_yoy"]), delta_color="off")
m8.metric("מכפיל מכירות P/S", num(L["ps"]))
m9.metric("מכפיל רווח P/E", num(L["pe"]) if not pd.isna(L["pe"]) else "אין רווח")
m10.metric("תנודתיות שנתית", pct(L["volatility"], False))

# ---------------------------------------------------------------------------
# סיכון + מה לבדוק
# ---------------------------------------------------------------------------
st.divider()
a, b = st.columns(2)
with a:
    st.markdown("#### ⚠️ ממה מורכב הסיכון")
    rows = "".join(
        f"<div class='risk-row'><span>{t}</span><span class='risk-pts' style='color:#EF4444'>+{p}</span></div>"
        for p, t in dg.risk_reasons
    )
    rows += "".join(
        f"<div class='risk-row'><span>{t}</span><span class='risk-pts' style='color:#22C55E'>{p}</span></div>"
        for p, t in dg.positives
    )
    st.markdown(rows, unsafe_allow_html=True)

with b:
    st.markdown("#### 🔍 מה לבדוק בשלב הזה")
    for w in dg.watch:
        st.markdown(f"- {w}")

    if dg.stage in ("startup", "startup_to_growth", "growth_loss", "loss_slow", "declining"):
        st.markdown("#### 🧮 כמה זמן הקופה מחזיקה")
        rf, rn = dg.runway["months_fcf"], dg.runway["months_ni"]
        st.markdown(
            f"- לפי **תזרים חופשי** (מדויק יותר): **{'מממנת את עצמה' if dg.runway['self_funded'] else months(rf)}**\n"
            f"- לפי **הפסד נקי** (השיטה מהסרטון): **{months(rn)}**"
        )
        if rf is not None and rn is not None and abs(rf - rn) / max(rf, rn, 1) > 0.3:
            st.caption("הפער בין השיטות נובע בעיקר מהוצאות שלא יוצאות מהקופה (כמו תגמול במניות) או מהשקעות הון.")
        be = dg.breakeven
        if be["trend"] == "narrowing" and be["months"]:
            covers = rf is None or be["months"] <= rf
            st.markdown(
                f"- **הערכת רווח נקי:** לפי מגמת ההפסדים בתקופות האחרונות – בעוד ~{be['months']} חודשים "
                f"(R²={be['r2']:.2f}). {'✅ הקופה מספיקה עד אז' if covers else '❌ הקופה לא מספיקה עד אז – צפוי גיוס'}"
            )
        elif be["trend"] == "widening":
            st.markdown("- **הערכת רווח נקי:** ההפסדים מתרחבים – אין מגמה לרווח.")
        elif be["trend"] == "flat":
            st.markdown("- **הערכת רווח נקי:** ההפסדים יציבים – אין מגמה ברורה לרווח.")

# ---------------------------------------------------------------------------
# גרפים
# ---------------------------------------------------------------------------
st.divider()
m = dg.metrics
tabs = st.tabs(["מסלול האבולוציה", "הכנסות", "רווח נקי", "מזומן מול חוב", "מניות (דילול)", "נתונים גולמיים"])

with tabs[0]:
    fig = go.Figure()
    hist = dg.history
    idx = list(hist.index)
    for i, t in enumerate(idx):
        s = hist.iloc[i]
        if s == "unknown":
            continue
        x0 = t
        x1 = idx[i + 1] if i + 1 < len(idx) else t + pd.Timedelta(days=91)
        fig.add_vrect(x0=x0, x1=x1, fillcolor=STAGES[s]["color"], opacity=0.22, line_width=0, layer="below")
    seen = set()
    for s in hist.values:
        if s != "unknown" and s not in seen:
            seen.add(s)
            fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers",
                                     marker=dict(size=12, color=STAGES[s]["color"], symbol="square"),
                                     name=STAGES[s]["he"]))
    if data.prices is not None and len(data.prices):
        p = data.prices[data.prices.index >= (idx[0] - pd.Timedelta(days=90))] if idx else data.prices
        fig.add_trace(go.Scatter(x=p.index, y=p.values, name="מחיר מניה", line=dict(color="#111827", width=1.6)))
        for _, ev in dg.events.iterrows():
            fig.add_vline(x=ev["event_date"], line_dash="dash", line_color="#10B981")
        fig.update_yaxes(title="מחיר ($)", type="log" if st.toggle("סקאלה לוגריתמית", value=True) else "linear")
    else:
        fig.add_trace(go.Scatter(x=m.index, y=m["revenue_ttm"], name="הכנסות 12 ח'"))
    fig.update_xaxes(type="date")
    fig.update_layout(height=460, legend=dict(orientation="h", y=-0.15), margin=dict(t=20))
    st.plotly_chart(fig, width="stretch")
    st.caption("הרקע צבוע לפי השלב שאובחן בכל רבעון. קו ירוק מקווקו = מועד פרסום הדוח שבו החברה עברה לרווח נקי.")

    if len(dg.events):
        st.markdown("##### 💥 אירועי מעבר לרווח נקי – ומה קרה למניה מאז")
        ev = dg.events.copy()
        show = pd.DataFrame({
            "רבעון": ev["quarter_end"].dt.date,
            "פרסום הדוח": ev["event_date"].dt.date,
            "מחיר בפרסום": ev.get("price_at_event", pd.Series(dtype=float)).map(lambda x: f"${x:,.2f}" if not pd.isna(x) else "—"),
            "תשואה ב-12 ח'": ev.get("return_12m", pd.Series([np.nan] * len(ev))).map(lambda x: pct(x)),
            "תשואה עד היום": ev.get("return_since", pd.Series([np.nan] * len(ev))).map(lambda x: pct(x)),
            "שיא מאז": ev.get("max_return_since", pd.Series([np.nan] * len(ev))).map(lambda x: pct(x)),
        })
        st.dataframe(show, hide_index=True, width="stretch")
        st.caption("התאריך הוא מועד הגשת הדוח ל-SEC (אז השוק יודע על הרווח), לא סוף הרבעון.")

with tabs[1]:
    fig = go.Figure()
    fig.add_bar(x=m.index, y=m["revenue_q"], name="הכנסות רבעוניות", marker_color="#93C5FD")
    fig.add_trace(go.Scatter(x=m.index, y=m["revenue_ttm"], name="הכנסות 12 ח'", line=dict(color="#1D4ED8", width=2.5)))
    fig.update_layout(height=420, legend=dict(orientation="h", y=-0.15), margin=dict(t=20))
    st.plotly_chart(fig, width="stretch")
    g = m["revenue_yoy"].replace([np.inf], np.nan)
    fig2 = go.Figure(go.Scatter(x=g.index, y=g.values * 100, line=dict(color="#7C3AED"), name="צמיחה שנתית %"))
    fig2.add_hline(y=cfg.growth_min * 100, line_dash="dot", annotation_text="סף צמיחה")
    fig2.add_hline(y=cfg.value_max * 100, line_dash="dot", annotation_text="סף ערך")
    fig2.update_layout(height=280, yaxis_title="% צמיחה (12 ח' מול שנה קודם)", margin=dict(t=20))
    st.plotly_chart(fig2, width="stretch")

with tabs[2]:
    fig = go.Figure()
    colors = ["#22C55E" if v >= 0 else "#EF4444" for v in m["net_income_q"].fillna(0)]
    fig.add_bar(x=m.index, y=m["net_income_q"], name="רווח נקי רבעוני", marker_color=colors)
    fig.add_trace(go.Scatter(x=m.index, y=m["net_income_ttm"], name="רווח נקי 12 ח'", line=dict(color="#111827", width=2.5)))
    if "fcf_ttm" in m:
        fig.add_trace(go.Scatter(x=m.index, y=m["fcf_ttm"], name="תזרים חופשי 12 ח'", line=dict(color="#0EA5E9", dash="dot")))
    fig.add_hline(y=0, line_color="gray")
    fig.update_layout(height=440, legend=dict(orientation="h", y=-0.15), margin=dict(t=20))
    st.plotly_chart(fig, width="stretch")

with tabs[3]:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=m.index, y=m["liquid"], name="מזומן + ני\"ע", line=dict(color="#22C55E", width=2.5)))
    fig.add_trace(go.Scatter(x=m.index, y=m["debt"], name="חוב פיננסי", line=dict(color="#EF4444", width=2.5)))
    fig.update_layout(height=420, legend=dict(orientation="h", y=-0.15), margin=dict(t=20))
    st.plotly_chart(fig, width="stretch")

with tabs[4]:
    fig = go.Figure(go.Scatter(x=m.index, y=m["shares"], line=dict(color="#7C3AED", width=2.5), name="מניות"))
    fig.update_layout(height=380, yaxis_title="מספר מניות", margin=dict(t=20))
    st.plotly_chart(fig, width="stretch")
    st.caption("עלייה חדה = הנפקות / המרות / תגמול במניות – כלומר דילול של בעלי המניות הקיימים.")

with tabs[5]:
    show = m.copy()
    show["שלב"] = dg.history.map(lambda s: STAGES[s]["he"])
    st.dataframe(show.sort_index(ascending=False), width="stretch")
    st.markdown("**מושגי XBRL שבשימוש:**")
    st.json(data.concepts_used)

st.divider()
st.caption(
    "⚠️ כלי לימודי ולא ייעוץ השקעות. הספים נקבעו על ידינו לפי ההיגיון בסרטון של דביר שלום – "
    "הנוסחאות המדויקות שלו נלמדות בקורס ואינן ידועות. נתוני XBRL עלולים לכלול חוסרים או מיפוי שגוי – "
    "תמיד לאמת מול הדוח עצמו."
)
