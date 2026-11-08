"""
אבחון שלב חברה – לפי מסגרת "האבולוציה של חברה" (סטארטאפ → צמיחה → ערך).
הרצה:  streamlit run app.py
"""
from __future__ import annotations

import html
import os
from datetime import date

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import analysis
import profile_data
import sec_data
from analysis import STAGES, Config

st.set_page_config(page_title="אבחון שלב חברה", page_icon="📈", layout="wide")

INK = "#14213D"
PAPER = "#F5F7FA"
RULE = "#DCE3EC"
GREEN = "#1A936F"
AMBER = "#D99A00"
RED = "#C8102E"
MUTED = "#5B6B82"

# ---------------------------------------------------------------------------
# עיצוב
# ---------------------------------------------------------------------------
st.markdown(
    f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Frank+Ruhl+Libre:wght@500;700;900&family=IBM+Plex+Sans+Hebrew:wght@400;500;600;700&display=swap');

.block-container, [data-testid="stSidebarContent"] {{ direction: rtl; }}
.stApp {{ background: {PAPER}; }}
[data-testid="stAppViewContainer"] :is(p, li, label, input, button, td, th, h1, h2, h3, h4, h5, div[data-testid="stMarkdownContainer"]) ,
[data-testid="stSidebar"] :is(p, label, input, button) {{
  font-family: 'IBM Plex Sans Hebrew', system-ui, sans-serif;
}}
[data-testid="stIconMaterial"], .material-symbols-rounded {{ font-family: 'Material Symbols Rounded' !important; }}
.block-container {{ padding-top: 1.6rem; max-width: 1240px; }}
[data-testid="stMarkdownContainer"] {{ text-align: right; }}
.num {{ font-variant-numeric: tabular-nums; direction: ltr; unicode-bidi: isolate; }}

/* ---------- כותרת עליונה ---------- */
.mast {{ background: {INK}; color: #fff; border-radius: 6px; padding: 22px 26px;
        display: grid; grid-template-columns: auto 1fr auto auto; gap: 26px; align-items: center; }}
.mono {{ width: 64px; height: 64px; border-radius: 6px; display: grid; place-items: center;
        font: 700 1.05rem 'IBM Plex Sans Hebrew', system-ui, sans-serif; letter-spacing: .02em; color: #fff; }}
.mast h1 {{ font-family: 'Frank Ruhl Libre', serif; font-weight: 900; font-size: 2.3rem; line-height: 1.1;
           margin: 0 0 8px 0; color: #fff; padding: 0; }}
.chips {{ display: flex; flex-wrap: wrap; gap: 6px; }}
.chip {{ border: 1px solid rgba(255,255,255,.28); border-radius: 999px; padding: 2px 10px; font-size: .82rem; color: #D7DFEA; }}
.chip.tk {{ background: #fff; color: {INK}; font-weight: 700; border-color: #fff; }}
.mast-px {{ text-align: left; border-inline-start: 1px solid rgba(255,255,255,.18); padding-inline-start: 22px; }}
.mast-px .px {{ font-size: 1.9rem; font-weight: 600; }}
.mast-px .chg.up {{ color: #6EE7B7; }} .mast-px .chg.down {{ color: #FCA5A5; }}
.mast-px .sub, .mast-next .sub {{ color: #AEB9C9; font-size: .8rem; }}
.mast-next {{ border-inline-start: 1px solid rgba(255,255,255,.18); padding-inline-start: 22px; min-width: 150px; }}
.mast-next .d {{ font-size: 1.25rem; font-weight: 600; }}
.mast-next .cd {{ display: inline-block; margin-top: 4px; background: rgba(255,255,255,.12); border-radius: 4px;
                 padding: 1px 8px; font-size: .82rem; }}
@media (max-width: 900px) {{ .mast {{ grid-template-columns: auto 1fr; padding: 18px; gap: 16px; }}
  .mast h1 {{ font-size: 1.6rem; }} .mono {{ width: 48px; height: 48px; font-size: .85rem; }}
  .mast-px, .mast-next {{ border: 0; padding: 0; text-align: right; }} }}
@media (max-width: 640px) {{ .track-wrap {{ padding: 16px 18px 14px; }} .track {{ margin: 16px 18px 4px; height: 70px; }}
  .station .nm {{ display: none; }} .station.end .nm {{ display: block; font-size: .75rem; }} }}

/* ---------- מסלול האבולוציה ---------- */
.track-wrap {{ background: #fff; border: 1px solid {RULE}; border-radius: 6px; padding: 22px 34px 18px; margin-top: 14px; }}
.track-title {{ display: flex; justify-content: space-between; align-items: baseline; gap: 16px; }}
.track-title h2 {{ font-family: 'Frank Ruhl Libre', serif; font-size: 1.75rem; font-weight: 900; margin: 0; padding: 0; }}
.track-title .why {{ color: {MUTED}; font-size: .9rem; }}
.track {{ position: relative; height: 92px; margin: 20px 10px 4px; }}
.track .line {{ position: absolute; top: 18px; right: 0; left: 0; height: 4px; background: {RULE}; border-radius: 2px; }}
.track .fill {{ position: absolute; top: 18px; right: 0; height: 4px; border-radius: 2px; }}
.station {{ position: absolute; top: 10px; transform: translateX(50%); text-align: center; width: 120px; }}
.station .dot {{ width: 20px; height: 20px; border-radius: 50%; margin: 0 auto; background: #fff; border: 3px solid {RULE}; }}
.station.past .dot {{ border-color: currentColor; background: currentColor; }}
.station .nm {{ margin-top: 10px; font-size: .86rem; color: {MUTED}; }}
.station.past .nm {{ color: {INK}; }}
.marker {{ position: absolute; top: 2px; transform: translateX(50%); text-align: center; }}
.marker .pin {{ width: 36px; height: 36px; border-radius: 50%; margin: 0 auto; border: 4px solid #fff;
               box-shadow: 0 0 0 2px currentColor; background: currentColor; }}
.offtrack {{ margin-top: 6px; color: {RED}; font-weight: 600; font-size: .9rem; }}

/* ---------- כותרות חלקים ---------- */
h3.sec {{ font-family: 'Frank Ruhl Libre', serif; font-weight: 700; font-size: 1.35rem; color: {INK};
         border-bottom: 2px solid {INK}; padding: 0 0 6px; margin: 26px 0 12px; }}
.lead {{ font-size: 1.02rem; line-height: 1.75; color: #1F2A3D; max-width: 72ch; }}
.status p {{ margin: 0 0 8px; line-height: 1.7; max-width: 72ch; }}
.facts {{ display: grid; grid-template-columns: max-content 1fr; gap: 6px 18px; margin-top: 12px; font-size: .92rem; }}
.facts dt {{ color: {MUTED}; }} .facts dd {{ margin: 0; color: {INK}; font-weight: 500; }}
.facts a {{ color: {INK}; }}

/* ---------- ציונים ---------- */
.score {{ display: grid; grid-template-columns: 110px 1fr 34px; align-items: center; gap: 12px; padding: 8px 0;
         border-bottom: 1px solid {RULE}; }}
.score .lbl {{ font-weight: 600; color: {INK}; }}
.score .bars {{ display: grid; grid-template-columns: repeat(10, 1fr); gap: 3px; direction: ltr; }}
.score .bars i {{ height: 12px; border-radius: 2px; background: #E7ECF2; }}
.score .val {{ font-weight: 700; text-align: left; }}
.score-note {{ color: {MUTED}; font-size: .8rem; margin-top: 6px; }}

/* ---------- מספרים מרכזיים ---------- */
.kgrid {{ display: grid; grid-template-columns: repeat(5, 1fr); background: #fff; border: 1px solid {RULE}; border-radius: 6px; }}
.kgrid > div {{ padding: 14px 16px; border-inline-start: 1px solid {RULE}; border-bottom: 1px solid {RULE}; }}
.kgrid > div:nth-child(5n+1) {{ border-inline-start: 0; }}
.kgrid > div:nth-last-child(-n+5) {{ border-bottom: 0; }}
.kgrid .k {{ color: {MUTED}; font-size: .82rem; }}
.kgrid .v {{ font-size: 1.3rem; font-weight: 600; color: {INK}; margin-top: 2px; }}
.kgrid .d {{ font-size: .8rem; margin-top: 2px; }}
.pos {{ color: {GREEN}; }} .neg {{ color: {RED}; }}
@media (max-width: 900px) {{ .kgrid {{ grid-template-columns: repeat(2, 1fr); }}
  .kgrid > div {{ border-inline-start: 0 !important; border-bottom: 1px solid {RULE} !important; }} }}

/* ---------- סיכון ---------- */
.rrow {{ display: grid; grid-template-columns: 1fr 48px; gap: 12px; padding: 7px 0; border-bottom: 1px solid {RULE}; }}
.rrow .p {{ font-weight: 700; text-align: left; }}
.watch {{ padding-inline-start: 1.1em; margin-inline-start: 0; }}
.watch li {{ margin-bottom: 4px; }}
.foot {{ color: {MUTED}; font-size: .8rem; margin-top: 30px; border-top: 1px solid {RULE}; padding-top: 12px; }}
.stTabs [data-baseweb="tab-list"] {{ gap: 4px; }}
</style>
""",
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# פורמט
# ---------------------------------------------------------------------------
def _bad(x):
    return x is None or (isinstance(x, (float, np.floating)) and (np.isnan(x) or np.isinf(x)))


def money(x, cur="USD"):
    if _bad(x):
        return "—"
    sym = "$" if cur == "USD" else f"{cur} "
    a, sign = abs(x), ("-" if x < 0 else "")
    for div, suf in ((1e12, "T"), (1e9, "B"), (1e6, "M"), (1e3, "K")):
        if a >= div:
            return f"<span class='num'>{sign}{sym}{a/div:.2f}{suf}</span>" if suf in "TB" else f"<span class='num'>{sign}{sym}{a/div:.1f}{suf}</span>"
    return f"<span class='num'>{sign}{sym}{a:.0f}</span>"


def pct(x, plus=True):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "—"
    if np.isinf(x):
        return "מאפס"
    fmt = ".1%" if abs(x) < 0.01 else ".0%"
    return f"<span class='num'>{x:+{fmt}}</span>" if plus else f"<span class='num'>{x:{fmt}}</span>"


def num(x, d=1):
    return "—" if _bad(x) else f"<span class='num'>{x:,.{d}f}</span>"


def months(x):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "—"
    return "10+ שנים" if x >= 120 else f"<span class='num'>{x:.0f}</span> חודשים"


def esc(s):
    return html.escape(str(s)) if s is not None else ""


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


@st.cache_data(ttl=12 * 3600, show_spinner=False)
def cached_profile(ticker, cik, ua):
    p = {}
    p.update(profile_data.fetch_sec_profile(cik, ua))
    p.update(profile_data.fetch_yahoo_profile(ticker))
    if p.get("summary_en"):
        short = profile_data.short_summary(p["summary_en"], 4)
        p["summary_short_en"] = short
        p["summary_he"] = profile_data.translate_he(short)
    return p


def load(ticker, ua):
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
        data.warnings.append("מחירים מ-Yahoo Finance לא זמינים כרגע – מכפילים, תנודתיות וגרף מחיר לא יוצגו.")
    return data


# ---------------------------------------------------------------------------
# סרגל צד
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("הגדרות")
    default_ua = os.environ.get("SEC_USER_AGENT", "")
    try:
        default_ua = default_ua or st.secrets.get("SEC_USER_AGENT", "")
    except Exception:
        pass
    ua = st.text_input(
        "זיהוי מול SEC (שם + מייל)",
        value=default_ua or sec_data.DEFAULT_UA,
        help="SEC מבקשת שכל בקשה תזדהה בשם ומייל.",
    )
    if "example.com" in ua:
        st.caption("כדאי להחליף לשם ומייל אמיתיים – SEC עלולה לחסום זיהוי גנרי.")
    with st.expander("ספי אבחון"):
        st.caption("ספים שנקבעו לפי ההיגיון בסרטון. אפשר לשנות.")
        cfg = Config(
            startup_rev=st.number_input("הכנסות שנתיות מתחתן = סטארטאפ ($M)", 1, 500, 25) * 1e6,
            early_rev=st.number_input("סף 'חברה צעירה' למעבר סטארטאפ←צמיחה ($M)", 50, 5000, 1000) * 1e6,
            growth_min=st.slider("צמיחה שנתית מינימלית לחברת צמיחה", 0.05, 0.60, 0.20, 0.01),
            value_max=st.slider("צמיחה מקסימלית לחברת ערך", 0.0, 0.20, 0.08, 0.01),
            approaching_q=st.slider("'מתקרבת לרווח' = רווח צפוי תוך X רבעונים", 1, 8, 4),
        )
    st.caption("נתונים: דוחות רשמיים מ-SEC EDGAR, מחירים ופרופיל מ-Yahoo Finance.")
    if st.button("רענון נתונים"):
        st.cache_data.clear()
        st.success("הנתונים ייטענו מחדש")

# ---------------------------------------------------------------------------
# חיפוש
# ---------------------------------------------------------------------------
examples = ["ASTS", "QS", "TE", "LMND", "PLTR", "SOFI", "HOOD", "KO"]
if "ticker_input" not in st.session_state:
    st.session_state.ticker_input = ""


def _set_ticker(t):
    st.session_state.ticker_input = t


c1, c2 = st.columns([4, 1])
with c1:
    st.text_input("טיקר", key="ticker_input", placeholder="הקלד טיקר, למשל LMND", label_visibility="collapsed")
with c2:
    st.button("אבחן", type="primary", width="stretch")


def _pick():
    v = st.session_state.get("example_pick")
    if v:
        st.session_state.ticker_input = v
    st.session_state.example_pick = None


st.pills("דוגמאות מהסרטון", examples, key="example_pick", on_change=_pick)

ticker = st.session_state.ticker_input.strip().upper()

if not ticker:
    st.markdown(
        f"""
<div class="track-wrap" style="margin-top:22px">
  <div class="track-title"><h2>באיזה שלב החברה נמצאת?</h2></div>
  <p class="lead" style="margin-top:10px">כל חברה עוברת מסלול: סטארטאפ בלי הכנסות, חברת צמיחה שמכניסה כסף ועדיין מפסידה,
  מעבר לרווח נקי, ובסוף חברת ערך בשלה. כל שלב מתמחרים אחרת, ולכל שלב סיכון אחר.
  הקלד טיקר של חברה שנסחרת בארה"ב, או בחר אחת מהדוגמאות מהסרטון.</p>
</div>""",
        unsafe_allow_html=True,
    )
    st.stop()

try:
    with st.spinner(f"מושך את הדוחות של {ticker}…"):
        data = load(ticker, ua)
        dg = analysis.diagnose(data, cfg)
        prof = cached_profile(ticker, data.cik, ua)
except sec_data.SecError as e:
    st.error(str(e))
    st.stop()
except Exception as e:
    st.error(f"לא הצלחתי לטעון את {ticker}: {e}")
    st.stop()

L = dg.latest
cur = data.currency
stage_color = STAGES[dg.stage]["color"]

# ---------------------------------------------------------------------------
# כותרת עליונה
# ---------------------------------------------------------------------------
name = prof.get("long_name") or data.name
chips = [f"<span class='chip tk'>{esc(data.ticker)}</span>"]
if prof.get("exchanges"):
    chips.append(f"<span class='chip'>{esc(prof['exchanges'][0])}</span>")
if prof.get("sector"):
    chips.append(f"<span class='chip'>{esc(profile_data.SECTOR_HE.get(prof['sector'], prof['sector']))}</span>")
if prof.get("industry"):
    chips.append(f"<span class='chip'>{esc(prof['industry'])}</span>")
elif prof.get("sic"):
    chips.append(f"<span class='chip'>{esc(prof['sic'].title())}</span>")
loc = prof.get("country") or prof.get("sec_state")
if loc:
    chips.append(f"<span class='chip'>{esc(loc)}</span>")

px_html = ""
if data.last_price:
    chg_html = ""
    if data.prices is not None and len(data.prices) > 1:
        d1 = data.prices.iloc[-1] / data.prices.iloc[-2] - 1
        chg_html = f"<div class='chg {'up' if d1 >= 0 else 'down'}'><span class='num'>{d1:+.2%}</span> ביום האחרון</div>"
    px_html = (
        f"<div class='mast-px'><div class='px num'>${data.last_price:,.2f}</div>{chg_html}"
        f"<div class='sub'>שווי שוק {money(data.market_cap)}</div></div>"
    )

next_html = ""
nxt_date, nxt_src = None, None
if prof.get("next_earnings"):
    nxt_date, nxt_src = prof["next_earnings"], "לפי Yahoo Finance"
elif prof.get("next_report_estimate"):
    est = prof["next_report_estimate"]
    nxt_date, nxt_src = est["date"], f"הערכה לפי קצב הדיווח (דוח {est['kind']})"
if nxt_date:
    days = (nxt_date - date.today()).days
    if days > 1:
        cd = f"בעוד <span class='num'>{days}</span> ימים"
    elif days in (0, 1):
        cd = "היום" if days == 0 else "מחר"
    else:
        cd = "צפוי בקרוב"
    next_html = (
        f"<div class='mast-next'><div class='sub'>הדוח הבא</div>"
        f"<div class='d num'>{nxt_date.strftime('%d.%m.%Y')}</div><div class='cd'>{cd}</div>"
        f"<div class='sub' style='margin-top:4px'>{nxt_src}</div></div>"
    )

st.markdown(
    f"""
<div class="mast">
  <div class="mono" style="background:{stage_color}">{esc(data.ticker[:4])}</div>
  <div><h1><bdi>{esc(name)}</bdi></h1><div class="chips">{''.join(chips)}</div></div>
  {px_html}
  {next_html}
</div>""",
    unsafe_allow_html=True,
)
for w in data.warnings:
    st.warning(w)

# ---------------------------------------------------------------------------
# מסלול האבולוציה
# ---------------------------------------------------------------------------
STATIONS = ["סטארטאפ", "צמיחה הפסדית", "מעבר לרווח", "צמיחה רווחית", "ערך"]
POS = {"startup": 0, "startup_to_growth": 0.5, "growth_loss": 1, "inflection": 2, "growth_profit": 3,
       "maturing": 3.5, "value": 4, "value_to_growth": 3.5, "loss_slow": 1, "declining": 4, "unknown": 0}
pos = POS.get(dg.stage, 0)
pct_pos = pos / 4 * 100
stations_html = ""
for i, nm in enumerate(STATIONS):
    cls = ("past " if i <= pos else "") + ("end" if i in (0, len(STATIONS) - 1) else "")
    stations_html += (
        f"<div class='station {cls}' style='right:{i/4*100}%; color:{stage_color}'>"
        f"<div class='dot'></div><div class='nm'>{nm}</div></div>"
    )
off = dg.stage in ("loss_slow", "declining")
track_fill = "" if off else f"<div class='fill' style='width:{pct_pos}%; background:{stage_color}'></div>"
st.markdown(
    f"""
<div class="track-wrap">
  <div class="track-title"><h2 style="color:{stage_color}">{dg.stage_he}</h2>
    <span class="why">{'⏳ מתקרבת לרווח נקי' if dg.approaching_profit else ''}</span></div>
  <div class="track">
    <div class="line"></div>{track_fill}
    {stations_html}
    <div class="marker" style="right:{pct_pos}%; color:{stage_color}"><div class="pin"></div></div>
  </div>
  {"<div class='offtrack'>מחוץ למסלול הבריא – " + ("הפסדית בלי צמיחה מספקת" if dg.stage == "loss_slow" else "ההכנסות מתכווצות") + "</div>" if off else ""}
  <p class="lead" style="margin:6px 0 0">{dg.explain}</p>
</div>""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# על החברה + ציונים
# ---------------------------------------------------------------------------
right, left = st.columns([3, 2], gap="large")
with right:
    st.markdown("<h3 class='sec'>על החברה</h3>", unsafe_allow_html=True)
    if prof.get("summary_he"):
        st.markdown(f"<p class='lead'>{esc(prof['summary_he'])}</p>", unsafe_allow_html=True)
    elif prof.get("summary_short_en"):
        st.markdown(f"<p class='lead' style='direction:ltr;text-align:left'>{esc(prof['summary_short_en'])}</p>", unsafe_allow_html=True)
    else:
        st.markdown("<p class='lead'>תיאור העסק לא זמין כרגע ממקור הנתונים.</p>", unsafe_allow_html=True)
    if prof.get("summary_en"):
        with st.expander("התיאור המלא (באנגלית)"):
            st.markdown(f"<div style='direction:ltr;text-align:left'>{esc(prof['summary_en'])}</div>", unsafe_allow_html=True)

    facts = []
    if prof.get("sector"):
        facts.append(("סקטור", profile_data.SECTOR_HE.get(prof["sector"], prof["sector"])))
    if prof.get("industry"):
        facts.append(("תעשייה", prof["industry"]))
    elif prof.get("sic"):
        facts.append(("סיווג ענפי (SEC)", prof["sic"].title()))
    city = prof.get("city") or prof.get("sec_city")
    country = prof.get("country") or prof.get("sec_state")
    if city or country:
        facts.append(("מטה", ", ".join(x.title() if x and x.isupper() else x for x in (city, country) if x)))
    if prof.get("employees"):
        facts.append(("עובדים", f"<span class='num'>{int(prof['employees']):,}</span>"))
    site = prof.get("website") or prof.get("sec_website")
    if site:
        site_url = site if site.startswith("http") else "https://" + site
        facts.append(("אתר", f"<a href='{esc(site_url)}' target='_blank'>{esc(site.replace('https://', '').replace('http://', '').strip('/'))}</a>"))
    fye = prof.get("fiscal_year_end")
    if fye and len(fye) == 4:
        facts.append(("סוף שנת כספים", f"<span class='num'>{fye[2:]}/{fye[:2]}</span>"))
    if prof.get("last_report"):
        lr = prof["last_report"]
        facts.append(("דוח אחרון", f"<span class='num'>{lr['form']}</span> לתקופה שהסתיימה ב-<span class='num'>{lr['period'].strftime('%d.%m.%Y')}</span>, "
                                    f"פורסם <span class='num'>{lr['filed'].strftime('%d.%m.%Y')}</span>"))
    if facts:
        st.markdown(
            "<dl class='facts'>" + "".join(f"<dt>{k}</dt><dd>{v if '<' in str(v) else esc(v)}</dd>" for k, v in facts) + "</dl>",
            unsafe_allow_html=True,
        )

    st.markdown("<h3 class='sec'>תמונת מצב</h3>", unsafe_allow_html=True)
    st.markdown(
        "<div class='status'>" + "".join(
            f"<p>{esc(s).replace(esc(name), f'<bdi>{esc(name)}</bdi>')}</p>" for s in analysis.status_narrative(dg, name)
        ) + "</div>",
        unsafe_allow_html=True,
    )

with left:
    st.markdown("<h3 class='sec'>רמת סיכון</h3>", unsafe_allow_html=True)
    risk_color = GREEN if dg.risk_score < 25 else AMBER if dg.risk_score < 50 else RED
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=dg.risk_score,
        number={"suffix": "", "font": {"size": 44, "color": INK, "family": "IBM Plex Sans Hebrew"}},
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 0, "tickfont": {"size": 10, "color": MUTED}},
            "bar": {"color": risk_color, "thickness": 0.32},
            "bgcolor": "#E7ECF2", "borderwidth": 0,
            "threshold": {"line": {"color": INK, "width": 2}, "thickness": 0.8, "value": dg.risk_score},
        },
    ))
    fig.update_layout(height=190, margin=dict(l=24, r=24, t=10, b=0), paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    st.markdown(f"<div style='text-align:center;margin-top:-14px;font-weight:600;color:{risk_color}'>סיכון {dg.risk_level} ביחס לשלב</div>",
                unsafe_allow_html=True)

    st.markdown("<h3 class='sec'>ציונים</h3>", unsafe_allow_html=True)
    sc = analysis.scorecards(dg)
    rows = ""
    for key, lbl in [("growth", "צמיחה"), ("profitability", "רווחיות"), ("strength", "חוסן פיננסי"), ("valuation", "תמחור")]:
        v = sc.get(key)
        if v is None:
            rows += f"<div class='score'><span class='lbl'>{lbl}</span><span style='color:{MUTED}'>אין נתון</span><span></span></div>"
            continue
        col = GREEN if v >= 7 else AMBER if v >= 4 else RED
        bars = "".join(f"<i style='background:{col if i < v else '#E7ECF2'}'></i>" for i in range(10))
        rows += f"<div class='score'><span class='lbl'>{lbl}</span><span class='bars'>{bars}</span><span class='val num' style='color:{col}'>{v}</span></div>"
    st.markdown(rows + "<div class='score-note'>1–10, גבוה = טוב יותר. בתמחור: גבוה = זול יותר. החישוב שלנו, לא מדד רשמי.</div>",
                unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# מספרים מרכזיים
# ---------------------------------------------------------------------------
st.markdown("<h3 class='sec'>מספרים מרכזיים</h3>", unsafe_allow_html=True)
g_now = L["revenue_yoy"]
dil = L["dilution_yoy"]
cells = [
    ("הכנסות, 12 חודשים", money(L["revenue_ttm"], cur),
     (f"<span class='{'pos' if (not _bad(g_now) and g_now >= 0) or (g_now is not None and np.isinf(g_now)) else 'neg'}'>{pct(g_now)} בשנה</span>" if g_now is not None and not pd.isna(g_now) else "")),
    ("רווח נקי, 12 חודשים", money(L["net_income_ttm"], cur),
     f"שולי רווח {pct(L['net_margin_ttm'], False)}" if not _bad(L["net_margin_ttm"]) else ""),
    ("תזרים חופשי, 12 חודשים", money(L["fcf_ttm"], cur), ""),
    ("מזומן וניירות ערך", money(L["liquid"], cur), ""),
    ("חוב פיננסי", money(L["debt"], cur), ""),
    ("הקופה מספיקה ל-", "לא שורפת מזומן" if dg.runway["self_funded"] else months(dg.runway["months_fcf"]), "לפי תזרים חופשי"),
    ("דילול שנתי", pct(dil), "" if _bad(dil) else ("גידול במספר המניות" if dil > 0.01 else ("רכישה עצמית" if dil < -0.01 else "ללא שינוי מהותי"))),
    ("מכפיל מכירות", num(L["ps"]), "P/S"),
    ("מכפיל רווח", num(L["pe"]) if not _bad(L["pe"]) else "אין רווח", "P/E"),
    ("תנודתיות שנתית", pct(L["volatility"], False), "שנה אחרונה"),
]
st.markdown(
    "<div class='kgrid'>" + "".join(
        f"<div><div class='k'>{k}</div><div class='v'>{v}</div><div class='d'>{d}</div></div>" for k, v, d in cells
    ) + "</div>",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# סיכון + מה לבדוק
# ---------------------------------------------------------------------------
a, b = st.columns(2, gap="large")
with a:
    st.markdown("<h3 class='sec'>ממה מורכב הסיכון</h3>", unsafe_allow_html=True)
    rows = "".join(f"<div class='rrow'><span>{esc(t)}</span><span class='p num' style='color:{RED}'>+{p}</span></div>" for p, t in dg.risk_reasons)
    rows += "".join(f"<div class='rrow'><span>{esc(t)}</span><span class='p num' style='color:{GREEN}'>{p}</span></div>" for p, t in dg.positives)
    st.markdown(rows, unsafe_allow_html=True)

with b:
    st.markdown("<h3 class='sec'>מה לבדוק בשלב הזה</h3>", unsafe_allow_html=True)
    st.markdown("<ul class='watch'>" + "".join(f"<li>{esc(w)}</li>" for w in dg.watch) + "</ul>", unsafe_allow_html=True)

    if dg.stage in ("startup", "startup_to_growth", "growth_loss", "loss_slow", "declining"):
        st.markdown("<h3 class='sec'>כמה זמן הקופה מחזיקה</h3>", unsafe_allow_html=True)
        rf, rn = dg.runway["months_fcf"], dg.runway["months_ni"]
        lines = [
            f"לפי תזרים חופשי (מדויק יותר): <b>{'לא שורפת מזומן' if dg.runway['self_funded'] else months(rf)}</b>",
            f"לפי הפסד נקי (השיטה מהסרטון): <b>{months(rn)}</b>",
        ]
        be = dg.breakeven
        if be["trend"] == "narrowing" and be["months"]:
            covers = rf is None or be["months"] <= rf
            lines.append(f"רווח נקי צפוי לפי המגמה: בעוד כ-<b><span class='num'>{be['months']}</span> חודשים</b> – "
                         + ("הקופה מספיקה עד אז" if covers else "הקופה לא מספיקה עד אז, צפוי גיוס"))
        elif be["trend"] == "widening":
            lines.append("ההפסדים מתרחבים – אין מגמה לרווח.")
        elif be["trend"] == "flat":
            lines.append("ההפסדים יציבים – אין מגמה ברורה לרווח.")
        st.markdown("<ul class='watch'>" + "".join(f"<li>{x}</li>" for x in lines) + "</ul>", unsafe_allow_html=True)
        if rf is not None and rn is not None and abs(rf - rn) / max(rf, rn, 1) > 0.3:
            st.caption("הפער בין השיטות נובע בעיקר מתגמול במניות (לא יוצא מהקופה) או מהשקעות הון.")

# ---------------------------------------------------------------------------
# גרפים
# ---------------------------------------------------------------------------
st.markdown("<h3 class='sec'>היסטוריה</h3>", unsafe_allow_html=True)
m = dg.metrics
FONT = dict(family="IBM Plex Sans Hebrew, sans-serif", color=INK, size=12)


def style(fig, h=420):
    fig.update_layout(
        height=h, font=FONT, paper_bgcolor="#fff", plot_bgcolor="#fff",
        legend=dict(orientation="h", y=-0.18), margin=dict(t=16, l=10, r=10, b=10),
        hoverlabel=dict(font_family="IBM Plex Sans Hebrew"),
    )
    fig.update_xaxes(showgrid=False, linecolor=RULE)
    fig.update_yaxes(gridcolor="#EEF2F6", zeroline=False)
    return fig


tabs = st.tabs(["מסלול המניה", "הכנסות", "רווח נקי", "מזומן מול חוב", "מניות", "אירועי מעבר לרווח", "נתונים גולמיים"])

with tabs[0]:
    fig = go.Figure()
    hist = dg.history
    idx = list(hist.index)
    for i, t in enumerate(idx):
        s = hist.iloc[i]
        if s == "unknown":
            continue
        x1 = idx[i + 1] if i + 1 < len(idx) else t + pd.Timedelta(days=91)
        fig.add_vrect(x0=t, x1=x1, fillcolor=STAGES[s]["color"], opacity=0.16, line_width=0, layer="below")
    seen = []
    for s in hist.values:
        if s != "unknown" and s not in seen:
            seen.append(s)
    for s in seen:
        fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers",
                                 marker=dict(size=11, color=STAGES[s]["color"], symbol="square"), name=STAGES[s]["he"]))
    log = st.toggle("סקאלה לוגריתמית", value=True)
    if data.prices is not None and len(data.prices):
        p = data.prices[data.prices.index >= (idx[0] - pd.Timedelta(days=90))] if idx else data.prices
        fig.add_trace(go.Scatter(x=p.index, y=p.values, name="מחיר מניה", line=dict(color=INK, width=1.8)))
        for _, ev in dg.events.iterrows():
            fig.add_vline(x=ev["event_date"], line_dash="dash", line_color=GREEN, line_width=1.5)
        fig.update_yaxes(title="מחיר ($)", type="log" if log else "linear")
    else:
        fig.add_trace(go.Scatter(x=m.index, y=m["revenue_ttm"], name="הכנסות 12 חודשים", line=dict(color=INK)))
    fig.update_xaxes(type="date")
    st.plotly_chart(style(fig, 460), width="stretch")
    st.caption("הרקע צבוע לפי השלב שאובחן בכל רבעון. קו ירוק מקווקו = פרסום הדוח שבו החברה עברה לרווח נקי.")

with tabs[1]:
    fig = go.Figure()
    fig.add_bar(x=m.index, y=m["revenue_q"], name="הכנסות רבעוניות", marker_color="#B8C7DC")
    fig.add_trace(go.Scatter(x=m.index, y=m["revenue_ttm"], name="הכנסות 12 חודשים", line=dict(color=INK, width=2.5)))
    st.plotly_chart(style(fig), width="stretch")
    g = m["revenue_yoy"].replace([np.inf], np.nan)
    fig2 = go.Figure(go.Scatter(x=g.index, y=g.values * 100, line=dict(color="#7C3AED", width=2), name="צמיחה שנתית %"))
    fig2.add_hline(y=cfg.growth_min * 100, line_dash="dot", line_color=MUTED, annotation_text="סף צמיחה")
    fig2.add_hline(y=cfg.value_max * 100, line_dash="dot", line_color=MUTED, annotation_text="סף ערך")
    fig2.update_yaxes(title="% צמיחה")
    st.plotly_chart(style(fig2, 280), width="stretch")

with tabs[2]:
    fig = go.Figure()
    colors = [GREEN if v >= 0 else RED for v in m["net_income_q"].fillna(0)]
    fig.add_bar(x=m.index, y=m["net_income_q"], name="רווח נקי רבעוני", marker_color=colors)
    fig.add_trace(go.Scatter(x=m.index, y=m["net_income_ttm"], name="רווח נקי 12 חודשים", line=dict(color=INK, width=2.5)))
    if "fcf_ttm" in m:
        fig.add_trace(go.Scatter(x=m.index, y=m["fcf_ttm"], name="תזרים חופשי 12 חודשים", line=dict(color="#0E7490", dash="dot")))
    fig.add_hline(y=0, line_color=MUTED)
    st.plotly_chart(style(fig, 440), width="stretch")

with tabs[3]:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=m.index, y=m["liquid"], name="מזומן וני\"ע", line=dict(color=GREEN, width=2.5)))
    fig.add_trace(go.Scatter(x=m.index, y=m["debt"], name="חוב פיננסי", line=dict(color=RED, width=2.5)))
    st.plotly_chart(style(fig), width="stretch")

with tabs[4]:
    fig = go.Figure(go.Scatter(x=m.index, y=m["shares"], line=dict(color="#7C3AED", width=2.5), name="מניות"))
    fig.update_yaxes(title="מספר מניות")
    st.plotly_chart(style(fig, 380), width="stretch")
    st.caption("עלייה חדה = הנפקות, המרות או תגמול במניות – דילול של בעלי המניות הקיימים.")

with tabs[5]:
    if len(dg.events):
        ev = dg.events.copy()

        def col(name):
            return ev[name] if name in ev else pd.Series([np.nan] * len(ev))

        def plain_pct(x):
            return "—" if pd.isna(x) else f"{x:+.0%}"

        show = pd.DataFrame({
            "רבעון": ev["quarter_end"].dt.date,
            "פרסום הדוח": ev["event_date"].dt.date,
            "מחיר בפרסום": col("price_at_event").map(lambda x: "—" if pd.isna(x) else f"${x:,.2f}"),
            "תשואה ב-12 חודשים": col("return_12m").map(plain_pct),
            "תשואה עד היום": col("return_since").map(plain_pct),
            "שיא מאז": col("max_return_since").map(plain_pct),
        })
        st.dataframe(show, hide_index=True, width="stretch")
        st.caption("התאריך הוא מועד הגשת הדוח ל-SEC – הרגע שבו השוק יודע על הרווח.")
    else:
        st.info("לחברה הזו לא זוהה מעבר מהפסד לרווח נקי בתקופה שיש עליה נתונים.")

with tabs[6]:
    show = m.copy()
    show["שלב"] = dg.history.map(lambda s: STAGES[s]["he"])
    st.dataframe(show.sort_index(ascending=False), width="stretch")
    st.markdown("**מאיזה שדה בדוח נלקח כל נתון:**")
    st.json(data.concepts_used)

st.markdown(
    "<div class='foot'>כלי לימודי ולא ייעוץ השקעות. הספים נקבעו לפי ההיגיון בסרטון של דביר שלום – "
    "הנוסחאות המדויקות שלו נלמדות בקורס. נתוני XBRL עלולים לכלול חוסרים או מיפוי שגוי, "
    "ותיאור החברה מתורגם אוטומטית – תמיד לאמת מול הדוח עצמו.</div>",
    unsafe_allow_html=True,
)
