"""
אימות הנתונים: בדיקות עקביות על נתוני ה-SEC, ומקור (דוח + שדה) לכל מספר מרכזי.
בדיקה מול מקור חיצוני (Yahoo Finance) נעשית בדפדפן, כשנתוני Yahoo מגיעים.
"""
from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

FORM_HE = {"10-Q": "דוח רבעוני", "10-K": "דוח שנתי", "20-F": "דוח שנתי (חברה זרה)", "40-F": "דוח שנתי (חברה זרה)",
           "10-Q/A": "דוח רבעוני מתוקן", "10-K/A": "דוח שנתי מתוקן", "8-K": "דיווח מיידי", "6-K": "דיווח שוטף"}


def filing_url(cik: int, accn: str | None) -> str | None:
    if not accn:
        return None
    return f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accn.replace('-', '')}/{accn}-index.htm"


def _rows_upto(prov: pd.DataFrame | None, end: pd.Timestamp, n: int):
    if prov is None or prov.empty:
        return []
    p = prov[prov.index <= end + pd.Timedelta(days=15)].tail(n)
    return [{"period_end": i, "form": r["form"], "accn": r["accn"], "filed": r["src_filed"]} for i, r in p.iterrows()]


def sources(data, dg) -> list[dict]:
    """לכל נתון מרכזי: הערך, השדה בדוח (XBRL), והדוחות שמהם נלקח – עם קישור לדוח ב-SEC."""
    L = dg.latest
    qe = L.get("quarter_end")
    if qe is None:
        return []
    pm = data.period_months
    n_flow = 4 if pm == 3 else 1
    used = data.concepts_used
    prov = data.provenance

    def entry(key, label, value, items, how):
        files, concepts = {}, []
        for it in items:
            if it not in prov or it not in used:
                continue
            rows = _rows_upto(prov[it], qe, n_flow if it in ("revenue", "net_income", "ocf", "capex", "op_income") else 1)
            # נתון מאזני ישן (שלא דווח שוב) לא נכנס לחישוב – ולכן גם לא מוצג כמקור
            rows = [r for r in rows if (pd.Timestamp(qe) - pd.Timestamp(r["period_end"])).days <= 200]
            if not rows:
                continue
            concepts.append(used[it])
            for r in rows:
                if r["accn"]:
                    files[r["accn"]] = r
        fl = sorted(files.values(), key=lambda r: r["period_end"], reverse=True)
        return {
            "key": key, "label": label, "value": value, "how": how, "concepts": concepts,
            "filings": [{"form": r["form"], "form_he": FORM_HE.get(r["form"], r["form"]), "period_end": r["period_end"],
                         "filed": r["filed"], "url": filing_url(data.cik, r["accn"])} for r in fl],
        }

    ttm_how = "סכום 4 הרבעונים האחרונים" if pm == 3 else "הדוח השנתי האחרון"
    sec_items = [i for i in ("securities_total", "st_investments", "lt_securities") if i in used]
    debt_items = [i for i in ("debt_total", "debt_noncurrent", "debt_current") if i in used]
    return [
        entry("revenue_ttm", "הכנסות, 12 חודשים", L.get("revenue_ttm"), ["revenue"], ttm_how),
        entry("net_income_ttm", "רווח נקי, 12 חודשים", L.get("net_income_ttm"), ["net_income"], ttm_how),
        entry("op_income_ttm", "רווח תפעולי, 12 חודשים", L.get("op_income_ttm"), ["op_income"], ttm_how),
        entry("fcf_ttm", "תזרים חופשי, 12 חודשים", L.get("fcf_ttm"), ["ocf", "capex"], "תזרים מפעילות שוטפת פחות השקעות ברכוש קבוע, " + ttm_how),
        entry("liquid", "מזומן וניירות ערך", L.get("liquid"), ["cash"] + sec_items, "מזומן ושווי מזומן + ניירות ערך סחירים (שוטפים ולא שוטפים), לסוף הרבעון"),
        entry("debt", "חוב פיננסי", L.get("debt"), debt_items, "חוב לטווח ארוך + חלויות שוטפות, לסוף הרבעון. לא כולל התחייבויות חכירה"),
        entry("shares", "מספר מניות", L.get("shares"), ["shares"], "כפי שדווח בעמוד הראשון של הדוח האחרון"),
    ]


def _check(cid, title, status, detail):
    return {"id": cid, "title": title, "status": status, "detail": detail}


def checks(data, dg) -> list[dict]:
    out = []
    L, m = dg.latest, dg.metrics
    qe = L.get("quarter_end")
    pm = data.period_months
    used = data.concepts_used

    # 1. עדכניות
    if qe is not None:
        age = (pd.Timestamp(date.today()) - pd.Timestamp(qe)).days
        last_filed = max((p["src_filed"].max() for p in data.provenance.values() if len(p)), default=None)
        lf = f", הדוח האחרון הוגש ב-{pd.Timestamp(last_filed).strftime('%d.%m.%Y')}" if last_filed is not None else ""
        limit_ok, limit_warn = (150, 240) if pm == 3 else (480, 600)
        st = "ok" if age <= limit_ok else "warn" if age <= limit_warn else "fail"
        out.append(_check("fresh", "הנתונים עדכניים", st,
                          f"התקופה האחרונה הסתיימה ב-{pd.Timestamp(qe).strftime('%d.%m.%Y')} (לפני {age} ימים){lf}."
                          + ("" if st == "ok" else " ייתכן שהחברה מאחרת בדיווח, או שהדוח החדש עוד לא עובד ב-SEC.")))

    # 2. רבעונים מחושבים סבירים: רבעון 4 (ותזרים מצטבר) מחושבים כהפרש בין דוחות.
    #    אם החברה הציגה מחדש מספרים או החליפה שדה – ההפרש יוצא שלילי או חריג.
    if pm == 3 and "revenue_q" in m:
        rq = m["revenue_q"].dropna().iloc[-12:]
        rq = rq[rq.index.isin(m.index)]
        neg = int((rq < 0).sum())
        med = rq.rolling(5, center=True, min_periods=3).median()
        odd = int(((rq > 3 * med) | ((rq < med / 3) & (med > 0))).sum()) if len(rq) >= 5 else 0
        st = "fail" if neg else "warn" if odd else "ok"
        out.append(_check("quarters", "ההכנסות הרבעוניות סבירות", st,
                          "אין רבעונים שליליים או חריגים בשלוש השנים האחרונות. רבעון רביעי מחושב כדוח השנתי פחות 9 חודשים."
                          if st == "ok" else
                          f"נמצאו {neg} רבעונים שליליים ו-{odd} רבעונים חריגים – כנראה הצגה מחדש של דוחות או שינוי בשדה הדיווח."))

    # 3. נכסים והתחייבויות
    b = data.balance
    assets = _last(b, "assets")
    liab = _last(b, "liabilities")
    liquid, debt = L.get("liquid"), L.get("debt")
    if assets and liquid is not None and not pd.isna(liquid):
        st = "ok" if liquid <= assets * 1.02 else "fail"
        out.append(_check("liquid_assets", "הקופה לא גדולה מסך הנכסים", st,
                          f"קופה {_fmt(liquid)} מתוך נכסים של {_fmt(assets)} ({liquid / assets:.0%})."))
    if liab and debt is not None and not pd.isna(debt):
        st = "ok" if debt <= liab * 1.02 else "fail"
        out.append(_check("debt_liab", "החוב לא גדול מסך ההתחייבויות", st,
                          f"חוב {_fmt(debt)} מתוך התחייבויות של {_fmt(liab)} ({debt / liab:.0%})."))

    # 4. רציפות
    idx = m.index[-12:] if pm == 3 else m.index[-4:]
    gaps = [(idx[i] - idx[i - 1]).days for i in range(1, len(idx))]
    max_gap = 100 if pm == 3 else 380
    bad = [g for g in gaps if g > max_gap]
    out.append(_check("continuity", "אין רבעונים חסרים" if pm == 3 else "אין שנים חסרות",
                      "ok" if not bad else "warn",
                      "כל התקופות בשלוש השנים האחרונות קיימות." if not bad else f"נמצאו {len(bad)} פערים בסדרה – חלק מהגרפים יהיו מקוטעים."))

    # 5. כיסוי
    need = {"revenue": "הכנסות", "net_income": "רווח נקי", "ocf": "תזרים מפעילות", "cash": "מזומן", "shares": "מספר מניות"}
    missing = [v for k, v in need.items() if k not in used]
    out.append(_check("coverage", "כל הנתונים הבסיסיים נמצאו בדוחות", "ok" if not missing else "warn",
                      "הכנסות, רווח, תזרים, מזומן ומניות – כולם נמצאו." if not missing else "חסרים: " + ", ".join(missing) + "."))
    if not any(k in used for k in ("debt_total", "debt_noncurrent", "debt_current")):
        out.append(_check("debt_found", "חוב פיננסי", "info", "לא נמצא חוב בדוחות. ייתכן שאין לחברה חוב, או שהוא מדווח תחת שם לא סטנדרטי."))

    # 6. הערות מבניות
    if data.spac_cutoff is not None:
        out.append(_check("spac", "סינון דוחות של חברת SPAC", "info",
                          f"דוחות שהוגשו עד {pd.Timestamp(data.spac_cutoff).strftime('%m/%Y')} שייכים לחברת המעטפת ולא נכללו."))
    if pm == 12:
        out.append(_check("annual_only", "דוחות שנתיים בלבד", "info", "החברה לא מגישה דוחות רבעוניים, ולכן האבחון מבוסס על נתונים שנתיים."))
    if L.get("non_operating_profit"):
        out.append(_check("nonop", "רווח לא תפעולי", "warn",
                          "הרווח הנקי חיובי, אבל הרווח התפעולי שלילי. לצורך האבחון הכלי מתייחס לחברה כהפסדית."))
    return out


def _last(b: pd.DataFrame, col: str):
    if b is None or col not in b or b[col].dropna().empty:
        return None
    return float(b[col].dropna().iloc[-1])


def _fmt(x):
    a = abs(x)
    for d, u in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
        if a >= d:
            return f"${x / d:.2f}{u}"
    return f"${x:,.0f}"
