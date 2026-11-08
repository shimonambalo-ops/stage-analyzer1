"""
הלוגיקה של ה-API (משותפת לפונקציות של Vercel בתיקיית api/ ולשרת הפיתוח המקומי).
כל פונקציה מחזירה dict שמוכן ל-JSON.
"""
from __future__ import annotations

import math
import os
import time
from datetime import date, datetime

import numpy as np
import pandas as pd

import analysis
import news_data
import profile_data
import sec_data
import verify

UA = os.environ.get("SEC_USER_AGENT") or sec_data.DEFAULT_UA

# cache בזיכרון – נשמר כל עוד המופע של הפונקציה "חם"
_CACHE: dict = {}


def _cached(key, ttl, fn):
    hit = _CACHE.get(key)
    if hit and time.time() - hit[0] < ttl:
        return hit[1]
    val = fn()
    _CACHE[key] = (time.time(), val)
    return val


def clean(o):
    """ממיר ערכים ל-JSON: NaN/inf → None, תאריכים → מחרוזת."""
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, (np.floating, float)):
        f = float(o)
        return None if math.isnan(f) or math.isinf(f) else f
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, (pd.Timestamp, datetime, date)):
        return o.strftime("%Y-%m-%d")
    if o is pd.NaT:
        return None
    return o


def ticker_map():
    return _cached("tmap", 86400, lambda: sec_data.load_ticker_map(UA))


def tickers_list():
    tm = ticker_map()
    return [[t, v["name"]] for t, v in tm.items()]


def _price_series(prices: pd.Series | None):
    """מחירים לגרף: יומי לשנתיים האחרונות, שבועי לפני כן (שומר על גודל תגובה סביר)."""
    if prices is None or not len(prices):
        return []
    cut = prices.index[-1] - pd.Timedelta(days=730)
    old = prices[prices.index < cut].resample("W-FRI").last().dropna()
    new = prices[prices.index >= cut]
    s = pd.concat([old, new])
    return [[d.strftime("%Y-%m-%d"), round(float(v), 4)] for d, v in s.items()]


def _yearly_snapshots(m: pd.DataFrame, n: int = 5):
    """שורות "12 חודשים שהסתיימו ב-…" – שנה אחורה בכל צעד, מהרבעון האחרון."""
    if m.empty:
        return []
    rows = []
    idx = m.index
    last = idx[-1]
    for k in range(n):
        target = last - pd.Timedelta(days=365 * k)
        diffs = np.abs((idx - target).days)
        j = int(np.argmin(diffs))
        if diffs[j] > 25:
            break
        r = m.iloc[j]
        rows.append({
            "end": idx[j], "revenue": r.get("revenue_ttm"), "growth": r.get("revenue_yoy"),
            "net_income": r.get("net_income_ttm"), "margin": r.get("net_margin_ttm"),
            "fcf": r.get("fcf_ttm"), "liquid": r.get("liquid"), "debt": r.get("debt"), "shares": r.get("shares"),
        })
    return rows


def _asof_info(data, dg):
    """על איזה דוח מבוססים הנתונים – להצגה בראש העמוד."""
    qe = dg.latest.get("quarter_end")
    p = data.provenance.get("revenue") if "revenue" in data.provenance else data.provenance.get("net_income")
    if qe is None or p is None or p.empty:
        return None
    row = p[p.index <= qe + pd.Timedelta(days=15)].tail(1)
    if row.empty:
        return None
    r = row.iloc[0]
    return {"period_end": qe, "form": r["form"], "form_he": verify.FORM_HE.get(r["form"], r["form"]),
            "filed": r["src_filed"], "url": verify.filing_url(data.cik, r["accn"]), "period_months": data.period_months}


def analyze(ticker: str) -> dict:
    ticker = ticker.strip().upper()
    tm = ticker_map()
    key = ticker if ticker in tm else ticker.replace(".", "-")
    if key not in tm:
        return {"error": f"הטיקר {ticker} לא נמצא ברשימת ה-SEC. הכלי תומך בחברות שמגישות דוחות ל-SEC (נסחרות בארה\"ב)."}
    info = tm[key]
    facts = _cached(("facts", info["cik"]), 6 * 3600, lambda: sec_data.fetch_company_facts(info["cik"], UA))
    raw_name = facts.get("entityName") or info["name"]
    nice = " ".join(w if any(ch.islower() for ch in w) else w.capitalize() for w in raw_name.split()) if raw_name.isupper() else raw_name
    data = sec_data.build_company_data(facts, ticker, nice, info["cik"])
    prices, last, mcap = _cached(("px", ticker), 3 * 3600, lambda: sec_data.fetch_prices(ticker))
    if prices is not None and data.spac_cutoff is not None:
        prices = prices[prices.index > data.spac_cutoff]  # מחירי חברת המעטפת (~10$) לא רלוונטיים
    data.prices, data.last_price = prices, last
    if mcap is None and last is not None and "shares" in data.balance and data.balance["shares"].notna().any():
        mcap = last * float(data.balance["shares"].dropna().iloc[-1])
    data.market_cap = mcap
    if prices is None:
        data.warnings.append("מחירים מ-Yahoo Finance לא זמינים כרגע – מכפילים, תנודתיות וגרף מחיר לא יוצגו.")

    cfg = analysis.Config()
    dg = analysis.diagnose(data, cfg)
    m = dg.metrics

    change_1d = None
    if prices is not None and len(prices) > 1:
        change_1d = float(prices.iloc[-1] / prices.iloc[-2] - 1)
    perf = {}
    if prices is not None and len(prices) > 5:
        for label, days in (("1M", 30), ("6M", 182), ("1Y", 365), ("5Y", 1826)):
            past = prices[prices.index <= prices.index[-1] - pd.Timedelta(days=days)]
            if len(past):
                perf[label] = float(prices.iloc[-1] / past.iloc[-1] - 1)
        ytd = prices[prices.index < pd.Timestamp(year=prices.index[-1].year, month=1, day=1)]
        if len(ytd):
            perf["YTD"] = float(prices.iloc[-1] / ytd.iloc[-1] - 1)

    series = {
        "dates": [d.strftime("%Y-%m-%d") for d in m.index],
        "revenue_q": list(m["revenue_q"]), "revenue_ttm": list(m["revenue_ttm"]),
        "revenue_yoy": list(m["revenue_yoy"].replace([np.inf], np.nan)),
        "net_income_q": list(m["net_income_q"]), "net_income_ttm": list(m["net_income_ttm"]),
        "fcf_ttm": list(m["fcf_ttm"]) if "fcf_ttm" in m else [],
        "liquid": list(m["liquid"]), "debt": list(m["debt"]), "shares": list(m["shares"]),
        "stage": [s for s in dg.history.reindex(m.index).fillna("unknown")],
    }

    return clean({
        "ticker": ticker, "cik": info["cik"], "name": data.name, "currency": data.currency,
        "period_months": data.period_months, "warnings": data.warnings,
        "price": last, "change_1d": change_1d, "market_cap": mcap, "perf": perf,
        "stage": dg.stage, "stage_he": dg.stage_he, "stage_color": analysis.STAGES[dg.stage]["color"],
        "explain": dg.explain, "watch": dg.watch, "approaching_profit": dg.approaching_profit,
        "risk": {"score": dg.risk_score, "level": dg.risk_level,
                 "reasons": [{"pts": p, "text": t} for p, t in dg.risk_reasons],
                 "positives": [{"pts": p, "text": t} for p, t in dg.positives]},
        "runway": dg.runway, "breakeven": dg.breakeven, "latest": dg.latest,
        "scores": analysis.scorecards(dg),
        "narrative": analysis.status_narrative(dg, data.name),
        "edges": analysis.edge_signals(dg, cfg),
        "events": dg.events.to_dict("records") if len(dg.events) else [],
        "series": series, "prices": _price_series(prices),
        "yearly": _yearly_snapshots(m),
        "stages": {k: {"he": v["he"], "color": v["color"]} for k, v in analysis.STAGES.items()},
        "concepts": data.concepts_used,
        "checks": verify.checks(data, dg),
        "sources": verify.sources(data, dg),
        "asof": _asof_info(data, dg),
        "updated": datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ"),
    })


def extras(ticker: str, cik: int = 0, name: str = "") -> dict:
    ticker = ticker.strip().upper()
    if not cik:
        tm = ticker_map()
        key = ticker if ticker in tm else ticker.replace(".", "-")
        if key not in tm:
            return {"error": f"הטיקר {ticker} לא נמצא"}
        cik, name = tm[key]["cik"], name or tm[key]["name"]
    sub = _cached(("sub", cik), 6 * 3600, lambda: profile_data.fetch_submissions(cik, UA)) or {}
    prof = {}
    prof.update(profile_data.fetch_sec_profile(cik, UA, sub))
    prof.update(_cached(("yprof", ticker), 6 * 3600, lambda: profile_data.fetch_yahoo_profile(ticker)))

    fil = news_data.sec_filings(sub, cik) if sub else {"filings": [], "insider_trades_90d": None, "shelf_filings_365d": []}
    news = _cached(("news", ticker), 1800, lambda: news_data.collect_news(ticker, prof.get("long_name") or name))

    # תרגום: תיאור החברה + כותרות באנגלית, בבקשה אחת לכל אחד
    summary_short = profile_data.short_summary(prof.get("summary_en"), 4) if prof.get("summary_en") else None
    summary_he = _cached(("tr", summary_short), 86400, lambda: profile_data.translate_he(summary_short)) if summary_short else None
    titles = [n["title"] for n in news["en"]]
    titles_he = _cached(("trt", tuple(titles)), 3600, lambda: profile_data.translate_many_he(titles)) if titles else []
    for n, t in zip(news["en"], titles_he):
        n["title_he"] = t

    nxt = None
    if prof.get("next_earnings"):
        nxt = {"date": prof["next_earnings"], "source": "לפי Yahoo Finance", "estimated": False}
    elif prof.get("next_report_estimate"):
        e = prof["next_report_estimate"]
        nxt = {"date": e["date"], "source": f"הערכה לפי קצב הדיווח (דוח {e['kind']})", "estimated": True}

    return clean({
        "profile": {
            "name": prof.get("long_name") or name,
            "summary_en": prof.get("summary_en"), "summary_short_en": summary_short, "summary_he": summary_he,
            "sector": prof.get("sector"), "sector_he": profile_data.SECTOR_HE.get(prof.get("sector"), prof.get("sector")),
            "industry": prof.get("industry"), "sic": prof.get("sic"),
            "city": prof.get("city") or prof.get("sec_city"), "country": prof.get("country") or prof.get("sec_state"),
            "employees": prof.get("employees"), "website": prof.get("website") or prof.get("sec_website"),
            "exchange": (prof.get("exchanges") or [None])[0], "fiscal_year_end": prof.get("fiscal_year_end"),
            "last_report": prof.get("last_report"),
        },
        "next_report": nxt,
        "stats": prof.get("stats") or {},
        "financial_currency": prof.get("financial_currency"),
        "recommendation": prof.get("recommendation"),
        "news": news,
        "filings": fil,
    })
