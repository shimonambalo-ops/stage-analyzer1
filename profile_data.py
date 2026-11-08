"""
פרופיל חברה: מה היא עושה, ענף, מדינה, עובדים, ומתי הדוח הבא.

מקורות (כולם בלי מפתח API):
- Yahoo Finance (yfinance): תיאור העסק, ענף, עובדים, אתר, מועד דוח צפוי.
- SEC submissions: סיווג ענפי (SIC), סוף שנת כספים, היסטוריית הגשות – משמשת להערכת
  מועד הדוח הבא כשאין תאריך מ-Yahoo.
- תרגום לעברית: deep-translator (Google Translate). אם נכשל – מוצג המקור באנגלית.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

import pandas as pd

from sec_data import _get_json

SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik:010d}.json"

SECTOR_HE = {
    "Technology": "טכנולוגיה",
    "Healthcare": "בריאות",
    "Financial Services": "שירותים פיננסיים",
    "Consumer Cyclical": "צריכה מחזורית",
    "Consumer Defensive": "צריכה בסיסית",
    "Communication Services": "תקשורת",
    "Industrials": "תעשייה",
    "Energy": "אנרגיה",
    "Utilities": "תשתיות",
    "Real Estate": "נדל\"ן",
    "Basic Materials": "חומרי גלם",
}

PERIODIC_FORMS = {"10-Q", "10-K", "20-F", "40-F", "10-KT"}

STAT_KEYS = [
    "fiftyTwoWeekHigh", "fiftyTwoWeekLow", "beta", "dividendYield", "forwardPE", "trailingPE", "trailingEps",
    "forwardEps", "priceToBook", "shortPercentOfFloat", "heldPercentInstitutions", "heldPercentInsiders",
    "averageVolume", "sharesOutstanding", "grossMargins", "operatingMargins", "profitMargins", "returnOnEquity",
    "recommendationMean", "targetMeanPrice", "targetHighPrice", "targetLowPrice", "numberOfAnalystOpinions",
    "regularMarketPreviousClose", "currentPrice", "enterpriseToEbitda", "pegRatio",
    # להשוואה מול נתוני ה-SEC (בדיקת אמינות)
    "totalRevenue", "netIncomeToCommon", "totalCash", "totalDebt", "marketCap", "mostRecentQuarter",
]


# ---------------------------------------------------------------------------
# Yahoo
# ---------------------------------------------------------------------------
def fetch_yahoo_profile(ticker: str) -> dict:
    out: dict = {}
    try:
        import yfinance as yf
        t = yf.Ticker(ticker)
    except Exception:
        return out
    try:
        info = t.info or {}
        for src, dst in [
            ("longBusinessSummary", "summary_en"), ("sector", "sector"), ("industry", "industry"),
            ("country", "country"), ("city", "city"), ("fullTimeEmployees", "employees"),
            ("website", "website"), ("exchange", "exchange"), ("longName", "long_name"),
            ("currency", "price_currency"),
        ]:
            if info.get(src) not in (None, ""):
                out[dst] = info[src]
        if info.get("financialCurrency"):
            out["financial_currency"] = info["financialCurrency"]
        stats = {}
        for k in STAT_KEYS:
            v = info.get(k)
            if isinstance(v, (int, float)) and v == v:
                stats[k] = float(v)
        # yfinance החליף בעבר את dividendYield מעשרוני לאחוזים – מנרמלים לעשרוני
        if "dividendYield" in stats and stats["dividendYield"] > 1:
            stats["dividendYield"] /= 100
        out["stats"] = stats
        if info.get("recommendationKey"):
            out["recommendation"] = info["recommendationKey"]
    except Exception:
        pass
    try:
        cal = t.calendar
        dates = None
        if isinstance(cal, dict):
            dates = cal.get("Earnings Date")
        elif isinstance(cal, pd.DataFrame) and "Earnings Date" in cal.index:
            dates = list(cal.loc["Earnings Date"].values)
        if dates:
            dates = [pd.Timestamp(d).date() for d in (dates if isinstance(dates, (list, tuple)) else [dates])]
            future = [d for d in dates if d >= date.today() - timedelta(days=1)]
            if future:
                out["next_earnings"] = min(future)
                out["next_earnings_range"] = (min(future), max(future)) if len(future) > 1 else None
    except Exception:
        pass
    return out


# ---------------------------------------------------------------------------
# SEC
# ---------------------------------------------------------------------------
def fetch_submissions(cik: int, user_agent: str) -> dict | None:
    try:
        return _get_json(SUBMISSIONS_URL.format(cik=cik), user_agent)
    except Exception:
        return None


def fetch_sec_profile(cik: int, user_agent: str, sub: dict | None = None) -> dict:
    out: dict = {}
    sub = sub if sub is not None else fetch_submissions(cik, user_agent)
    if not sub:
        return out
    out["sic"] = sub.get("sicDescription")
    out["exchanges"] = [e for e in (sub.get("exchanges") or []) if e]
    out["fiscal_year_end"] = sub.get("fiscalYearEnd")  # "1231"
    out["filer_category"] = sub.get("category")
    addr = (sub.get("addresses") or {}).get("business") or {}
    out["sec_city"] = addr.get("city")
    out["sec_state"] = addr.get("stateOrCountryDescription") or addr.get("stateOrCountry")
    if sub.get("website"):
        out["sec_website"] = sub["website"]

    recent = (sub.get("filings") or {}).get("recent") or {}
    forms = recent.get("form") or []
    fdates = recent.get("filingDate") or []
    rdates = recent.get("reportDate") or []
    rows = []
    for f, fd, rd in zip(forms, fdates, rdates):
        if f in PERIODIC_FORMS and fd and rd:
            rows.append({"form": f, "filed": pd.Timestamp(fd), "period": pd.Timestamp(rd)})
    if rows:
        df = pd.DataFrame(rows).sort_values("filed")
        last = df.iloc[-1]
        out["last_report"] = {"form": last["form"], "filed": last["filed"].date(), "period": last["period"].date()}
        out["next_report_estimate"] = _estimate_next(df, out.get("fiscal_year_end"))
    return out


def _estimate_next(df: pd.DataFrame, fye: str | None) -> dict | None:
    """הערכת מועד הדוח הבא לפי קצב ההגשות בעבר."""
    last = df.iloc[-1]
    annual_only = not (df["form"] == "10-Q").any()
    step = 365 if annual_only else 91
    next_period = last["period"] + pd.Timedelta(days=step)

    is_year_end = annual_only
    if fye and len(fye) == 4 and not annual_only:
        fy_md = (int(fye[:2]), int(fye[2:]))
        cand = pd.Timestamp(year=next_period.year, month=fy_md[0], day=min(fy_md[1], 28))
        is_year_end = abs((next_period - cand).days) <= 20

    forms = {"10-K", "20-F", "40-F", "10-KT"} if is_year_end else {"10-Q"}
    hist = df[df["form"].isin(forms)].tail(4)
    lag = int((hist["filed"] - hist["period"]).dt.days.median()) if len(hist) else (60 if is_year_end else 40)
    est = (next_period + pd.Timedelta(days=lag)).date()
    # אם ההערכה כבר עברה (דוח באיחור) – מציגים "בקרוב"
    return {"date": est, "period": next_period.date(), "kind": "שנתי" if is_year_end else "רבעוני", "overdue": est < date.today()}


# ---------------------------------------------------------------------------
# תרגום
# ---------------------------------------------------------------------------
def translate_he(text: str) -> str | None:
    if not text:
        return None
    try:
        from deep_translator import GoogleTranslator
        text = text[:4500]
        return GoogleTranslator(source="auto", target="iw").translate(text)
    except Exception:
        return None


def translate_many_he(texts: list[str]) -> list[str | None]:
    """מתרגם כמה שורות בבקשה אחת (מופרדות בשורה חדשה). אם המבנה נשבר – מחזיר None לכולן."""
    if not texts:
        return []
    joined = "\n".join(t.replace("\n", " ") for t in texts)
    res = translate_he(joined)
    if not res:
        return [None] * len(texts)
    parts = [p.strip() for p in res.split("\n")]
    return parts if len(parts) == len(texts) else [None] * len(texts)


def short_summary(text: str, max_sentences: int = 4) -> str:
    """מקצר תיאור ארוך לכמה משפטים ראשונים."""
    if not text:
        return text
    parts = [p.strip() for p in text.replace("\n", " ").split(". ") if p.strip()]
    out = ". ".join(parts[:max_sentences])
    return out if out.endswith(".") else out + "."
