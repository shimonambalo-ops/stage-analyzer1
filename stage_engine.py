"""
מנוע השלבים: באיזה שלב במחזור החיים החברה נמצאת, כמה בטוחים בזה, ומה הסיכון ביחס לשלב.

שכבה 1 – Dickinson, V. (2011), The Accounting Review 86(6):
    הסימנים (+/−) של תזרים מפעילות, מהשקעות וממימון בכל אחת מ-4 שנות הכספים האחרונות.
    השלב של Dickinson = הנפוץ ב-3 השנים האחרונות (בתיקו – השנה האחרונה).
שכבה 2 – מדדים תומכים בסגנון Damodaran (2024): צמיחה, השקעות מול פחת, ROIC, תזרים חופשי, החזר לבעלים.
ניקוד: כל מדד נותן נקודות לשלבים שהפרופיל שלהם מתאים לו (stage_config.PROFILES), לפי משקלות.
השלב הסופי = הניקוד הגבוה ביותר; הביטחון = הפער בין המקום הראשון לשני.

כל הספים ב-stage_config.py. הנתונים – מהדוחות השנתיים ב-SEC (sec_data.CompanyData.fiscal).
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

import stage_config as C

DICKINSON = {
    ("-", "-", "+"): "introduction",
    ("+", "-", "+"): "growth",
    ("+", "-", "-"): "mature",
    ("-", "-", "-"): "shakeout",
    ("+", "+", "+"): "shakeout",
    ("+", "+", "-"): "shakeout",
    ("-", "+", "+"): "decline",
    ("-", "+", "-"): "decline",
}

JUDGE_BY = {
    "startup": "הקופה מול קצב השריפה (כמה זמן נשאר עד גיוס), היקף הדילול ואבני הדרך של המוצר. מכפילים עדיין לא רלוונטיים.",
    "growth": "קצב צמיחת ההכנסות והאם הוא נשמר, שיפור בשולי הרווח ותשואה על ההון שמשתפרת. מכפיל מכירות מול קצב הצמיחה.",
    "profitable": "האם הצמיחה נשמרת בזמן שהשוליים והתשואה על ההון גבוהים, ולאן הולך התזרים החופשי. מכפיל רווח מול צמיחה (PEG).",
    "value": "תזרים חופשי יציב, שוליים שלא נשחקים, תשואה על ההון, וכמה מהתזרים חוזר לבעלי המניות. מכפיל תזרים ותשואת דיבידנד.",
    "shakeout": "מה גורם לטלטלה – מכירת נכסים, ארגון מחדש או ירידה בתזרים מהפעילות – ולאן החברה מכוונת אחריה.",
    "decline": "ערך הנכסים, היכולת להחזיר את החוב, והאם החלוקה לבעלי המניות בת-קיימא כשההכנסות יורדות.",
}

DICKINSON_WHY = {
    "introduction": "הפעילות שורפת מזומן, והחברה משקיעה ומממנת את עצמה מגיוסים",
    "growth": "הפעילות מייצרת מזומן, אבל החברה משקיעה יותר מזה וממשיכה לגייס",
    "mature": "הפעילות מממנת את ההשקעות, והעודף חוזר לבעלים או להחזר חוב",
    "shakeout": "צירוף תזרימים מעורב – לרוב מכירת נכסים, ארגון מחדש או מעבר בין שלבים",
    "decline": "הפעילות שורפת מזומן והחברה מוכרת נכסים כדי לממן אותה",
}


# ---------------------------------------------------------------------------
# עזרים
# ---------------------------------------------------------------------------
def _num(x):
    if x is None:
        return None
    try:
        f = float(x)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) or math.isinf(f) else f


def _asof(s, when, max_age_days=20, slack_days=15):
    if s is None:
        return None
    s = s.dropna().sort_index()
    s = s[s.index <= when + pd.Timedelta(days=slack_days)]
    if not len(s) or (when - s.index[-1]).days > max_age_days:
        return None
    return float(s.iloc[-1])


def band(x, lo, hi, soft):
    """1 בתוך הטווח, ויורד ליניארית עד 0 במרחק soft מחוצה לו."""
    if x is None:
        return None
    if (lo is None or x >= lo) and (hi is None or x <= hi):
        return 1.0
    d = (lo - x) if (lo is not None and x < lo) else (x - hi)
    return max(0.0, 1.0 - d / soft) if soft else 0.0


def _sign(x):
    return "+" if x > 0 else "-"   # 0 נחשב שלילי


def _ratio(a, b):
    a, b = _num(a), _num(b)
    if a is None or b is None or b == 0:
        return None
    return a / b


def _slope(vals):
    """שיפוע ליניארי לשנה (נק' אחוז לשנה כשהערכים הם שוליים)."""
    v = [x for x in vals if x is not None]
    if len(v) < 2:
        return None
    x = np.arange(len(v), dtype=float)
    return float(np.polyfit(x, np.array(v, dtype=float), 1)[0])


def is_financial(sic) -> bool:
    try:
        n = int(str(sic).strip())
    except (TypeError, ValueError):
        return False
    return any(lo <= n <= hi for lo, hi in C.FINANCIAL_SIC)


# ---------------------------------------------------------------------------
# טבלת השנים
# ---------------------------------------------------------------------------
def fiscal_rows(data) -> list[dict]:
    fy = getattr(data, "fiscal", None)
    if fy is None or fy.empty:
        return []
    b = data.balance if data.balance is not None else pd.DataFrame()
    col = lambda c: b[c] if c in b else None

    def sec_level(t):
        st, lt, tot = _asof(col("st_investments"), t), _asof(col("lt_securities"), t), _asof(col("securities_total"), t)
        if st is None and lt is None and tot is None:
            return None
        return max((st or 0) + (lt or 0), tot or 0)

    rows, prev_t = [], None
    for t, r in fy.sort_index().iterrows():
        g = lambda k: _num(r.get(k))
        rev, ocf, cfi, cff = g("revenue"), g("ocf"), g("cfi"), g("cff")
        cash, st = _asof(col("cash"), t), _asof(col("st_investments"), t)
        lt, tot = _asof(col("lt_securities"), t), _asof(col("securities_total"), t)
        liquid = None
        if any(v is not None for v in (cash, st, lt, tot)):
            liquid = max((cash or 0) + (st or 0) + (lt or 0), (cash or 0) + (tot or 0))
        # תזרים מהשקעות מנוטרל מניהול ניירות ערך
        sec_now = sec_level(t)
        sec_prev = sec_level(prev_t) if prev_t is not None else None
        sec_change = (sec_now - sec_prev) if (sec_now is not None and sec_prev is not None) else 0.0
        cfi_adj = (cfi + sec_change) if (cfi is not None and C.NEUTRALIZE_SECURITIES) else cfi
        # הנטרול לא "ממציא" מכירת נכסים: עלייה ביתרת ניירות הערך יכולה לנבוע גם מרכישת חברה או משערוך,
        # ולכן אם התזרים המקורי שלילי – אחרי הנטרול הוא לכל היותר 0 (ולא מכירת נכסים)
        if cfi is not None and cfi_adj is not None and cfi <= 0 < cfi_adj:
            cfi_adj = 0.0

        capex = abs(g("capex")) if g("capex") is not None else (0.0 if ocf is not None else None)
        fcf = (ocf - capex) if (ocf is not None and capex is not None) else None
        gp = g("gross_profit")
        if gp is None and rev is not None and g("cost_of_revenue") is not None:
            gp = rev - g("cost_of_revenue")
        op = g("op_income")
        tax_rate = _ratio(g("tax"), g("pretax"))
        if tax_rate is None or not (0 <= tax_rate <= 0.5) or (g("pretax") or 0) <= 0:
            tax_rate = None
        debt, equity = _asof(col("debt"), t), _asof(col("equity"), t)
        da = g("da")
        div = abs(g("dividends")) if g("dividends") is not None else (0.0 if ocf is not None else None)
        bb = abs(g("buybacks")) if g("buybacks") is not None else (0.0 if ocf is not None else None)

        # ROIC = EBIT × (1 − מס) / (חוב + הון עצמי − מזומן)
        roic, ic_negative = None, False
        if op is not None and equity is not None:
            nopat = op * (1 - (tax_rate if tax_rate is not None else C.DEFAULT_TAX))
            ic = (debt or 0) + equity - ((cash or 0) + (st or 0))
            if ic > 0:
                roic = nopat / ic
            elif op > 0:
                roic, ic_negative = 1.0, True   # הון מושקע שלילי ורווח תפעולי חיובי = תשואה "אינסופית"
            elif (debt or 0) + equity > 0:
                roic = nopat / ((debt or 0) + equity)   # הפסד תפעולי וקופה גדולה מההון – בלי ניכוי המזומן

        pattern, near_zero = None, []
        if None not in (ocf, cfi_adj, cff):
            pat = [_sign(ocf), _sign(cfi_adj), _sign(cff)]
            if C.MATERIALITY:
                scale = max(abs(ocf), abs(cfi_adj), abs(cff))
                for i, (k, v) in enumerate((("cfi", cfi_adj), ("cff", cff)), start=1):
                    if scale > 0 and abs(v) < C.MATERIALITY * scale and pat[i] == "+":
                        pat[i] = "-"
                        near_zero.append(k)
            pattern = "".join(pat)

        rows.append({
            "end": t, "revenue": rev, "op_income": op, "net_income": g("net_income"),
            "ocf": ocf, "cfi": cfi, "cfi_adj": cfi_adj, "cff": cff, "sec_change": sec_change,
            "pattern": pattern, "near_zero": near_zero,
            "dickinson": DICKINSON.get(tuple(pattern)) if pattern else None,
            "capex": capex, "da": da, "capex_da": _ratio(capex, da) if (da or 0) > 0 else None,
            "fcf": fcf, "fcf_margin": _ratio(fcf, rev) if (rev or 0) > 0 else None,
            "gross_margin": _ratio(gp, rev) if (rev or 0) > 0 else None,
            "op_margin": _ratio(op, rev) if (rev or 0) > 0 else None,
            "tax_rate": tax_rate, "roic": roic, "ic_negative": ic_negative,
            "dividends": div, "buybacks": bb,
            "payout": _ratio((div or 0) + (bb or 0), fcf) if (fcf or 0) > 0 else None,
            "shares": g("shares_diluted_avg"), "liquid": liquid, "cash": cash, "debt": debt, "equity": equity,
            "ebitda": (op + da) if (op is not None and da is not None) else None,
        })
        prev_t = t
    # רק שנים מלאות עם נתונים, והאחרונות קודם לחישוב צמיחה
    rows = [r for r in rows if r["revenue"] is not None or r["ocf"] is not None]
    for i, r in enumerate(rows):
        p = rows[i - 1] if i else None
        r["growth"] = _ratio(r["revenue"], p["revenue"]) - 1 if (p and (p["revenue"] or 0) > 1e6 and r["revenue"] is not None) else None
        r["dilution"] = _ratio(r["shares"], p["shares"]) - 1 if (p and (p["shares"] or 0) > 0 and r["shares"]) else None
        if r["dilution"] is not None:
            q = r["dilution"] + 1
            # פיצול / איחוד מניות שלא הותאם לאחור (למשל 10:1) – לא דילול
            if (q >= 1.8 and abs(q - round(q)) < 0.08 * q) or (q <= 0.55 and abs(1 / q - round(1 / q)) < 0.08 / q):
                r["dilution"] = None
    return rows


# ---------------------------------------------------------------------------
# ניקוד
# ---------------------------------------------------------------------------
def _cagr(rows, n=3):
    revs = [r["revenue"] for r in rows if r["revenue"] is not None]
    if len(revs) < 2:
        return None, 0
    n = min(n, len(revs) - 1)
    a, b = revs[-1 - n], revs[-1]
    if b is None or b <= 0 or a is None:
        return None, n
    if a <= 1e6:   # מהכנסות אפסיות – צמיחה "אינסופית"; מוגבל ל-100% בשנה
        return (1.0 if b >= C.STARTUP_REVENUE else None), n
    return (b / a) ** (1 / n) - 1, n


def _metric_scores(m: dict) -> dict:
    """לכל מדד – ניקוד 0–1 לכל שלב (None = אין נתון)."""
    out = {}
    # צמיחה
    if m.get("revenue") is not None and m["revenue"] < C.STARTUP_REVENUE:
        out["growth"] = {k: {"startup": 1.0, "growth": 0.3}.get(k, 0.0) for k in C.STAGE_KEYS}
    elif m.get("cagr") is not None:
        out["growth"] = {k: band(m["cagr"], *C.PROFILES["growth"][k]) for k in C.STAGE_KEYS}
    # Capex / פחת
    if m.get("capex_da") is not None:
        out["capex"] = {k: band(m["capex_da"], *C.PROFILES["capex"][k]) for k in C.STAGE_KEYS}
    # ROIC + מגמה
    if m.get("roic") is not None:
        s = {k: band(m["roic"], *C.PROFILES["roic"][k]) for k in C.STAGE_KEYS}
        tr = m.get("roic_trend")
        if tr is not None:
            if tr >= C.ROIC_IMPROVING and m["roic"] < 0.15:
                s["growth"] = max(s["growth"], 0.8)
            if abs(tr) > C.ROIC_STABLE:
                s["value"] *= 0.6
            s["decline"] *= 1.0 if tr < 0 else 0.5
        out["roic"] = s
    # שולי FCF + מגמה
    if m.get("fcf_margin") is not None:
        s = {k: band(m["fcf_margin"], *C.PROFILES["fcf"][k]) for k in C.STAGE_KEYS}
        if m.get("fcf_trend") is not None and m["fcf_trend"] >= 0:
            s["decline"] *= 0.5
        out["fcf"] = s
    # החזר לבעלים ודילול
    dil, pay = m.get("dilution"), m.get("payout")
    if dil is not None or pay is not None or m.get("fcf") is not None:
        P = C.PAYOUT
        payv = pay if pay is not None else (0.0 if (m.get("returned") or 0) == 0 else 1.5)
        dilv = dil if dil is not None else 0.0
        out["payout"] = {
            "startup": band(dilv, *P["startup_dilution"]),
            "growth": band(dilv, *P["growth_dilution"]) * (1.0 if payv < P["growth_max_payout"] else 0.3),
            "profitable": band(payv, *P["profitable_payout"]) * (1.0 if dilv <= P["profitable_max_dilution"] else 0.5),
            "value": band(payv, *P["value_payout"]) * (1.0 if dilv <= P["value_max_dilution"] else 0.5),
            "shakeout": 0.3,
            "decline": 1.0 if m.get("dividend_cut") else 0.2,
        }
    return out


def _combine(parts: dict, weights: dict):
    tot = {k: 0.0 for k in C.STAGE_KEYS}
    wsum = 0.0
    for name, sc in parts.items():
        w = weights.get(name, 0)
        if not w or sc is None:
            continue
        wsum += w
        for k in C.STAGE_KEYS:
            tot[k] += w * (sc.get(k) or 0.0)
    if wsum == 0:
        return None, 0.0
    return {k: v / wsum for k, v in tot.items()}, wsum


# ---------------------------------------------------------------------------
# הערכה
# ---------------------------------------------------------------------------
def _fmt_pct(x, digits=0):
    return None if x is None else f"{x * 100:.{digits}f}%"


def evaluate(data, latest: dict | None = None, sic=None, market_cap=None) -> dict:
    latest = latest or {}
    if is_financial(sic):
        return {
            "suitable": False,
            "reason": "המודל לא מתאים לחברות פיננסיות (בנקים, ביטוח, ברוקרים וקרנות נדל\"ן): "
                      "אצלן הלוואות, פיקדונות והשקעות הם חלק מהפעילות עצמה, ולכן הסימנים של דוח תזרים המזומנים "
                      "לא מעידים על שלב במחזור החיים.",
            "sic": sic,
        }

    rows = fiscal_rows(data)
    path = [r for r in rows if r["pattern"]][-C.YEARS_PATH:]
    if not path:
        return {"suitable": True, "stage": None,
                "reason": "אין מספיק דוחות שנתיים עם דוח תזרים מזומנים מלא כדי לקבוע שלב."}

    # ---- שכבה 1: Dickinson ----
    vote_rows = path[-C.YEARS_VOTE:]
    counts: dict = {}
    for r in vote_rows:
        counts[r["dickinson"]] = counts.get(r["dickinson"], 0) + 1
    top = max(counts.values())
    leaders = [s for s, c in counts.items() if c == top]
    dk_stage = leaders[0] if len(leaders) == 1 else vote_rows[-1]["dickinson"]
    dk_aff = {k: sum(C.DICKINSON_AFFINITY[r["dickinson"]][k] for r in vote_rows) / len(vote_rows) for k in C.STAGE_KEYS}

    # ---- שכבה 2: מדדים ----
    last = rows[-1]
    last3 = rows[-3:]
    cagr, cagr_n = _cagr(rows, 3)
    gs = [r["growth"] for r in rows if r.get("growth") is not None]
    accel = (gs[-1] - gs[-2]) if len(gs) >= 2 else None
    roics = [r["roic"] for r in last3]
    roic_trend = (roics[-1] - roics[0]) if (len(roics) >= 2 and roics[-1] is not None and roics[0] is not None) else None
    fcfm = [r["fcf_margin"] for r in last3]
    divs = [r["dividends"] for r in rows[-2:]]
    dividend_cut = len(divs) == 2 and (divs[0] or 0) > 0 and (divs[1] or 0) < C.DIVIDEND_CUT * divs[0]

    # נתונים עדכניים (12 חודשים אחרונים) לקופה ולתמחור
    fcf_ttm = _num(latest.get("fcf_ttm"))
    fcf_now = fcf_ttm if fcf_ttm is not None else last["fcf"]
    liquid = _num(latest.get("liquid"))
    liquid = liquid if liquid is not None else last["liquid"]
    debt = _num(latest.get("debt"))
    debt = debt if debt is not None else last["debt"]
    runway = None
    if fcf_now is not None and fcf_now < 0 and liquid is not None:
        runway = max(0.0, liquid) / (-fcf_now) * 12
    implied = None
    mcap = _num(market_cap)
    if mcap and fcf_now and fcf_now > 0:
        ev = mcap + (debt or 0) - (liquid or 0)
        if ev + fcf_now > 0:
            implied = (C.DISCOUNT_RATE * ev - fcf_now) / (ev + fcf_now)
    net_debt_ebitda = None
    if last["ebitda"] and last["ebitda"] > 0 and debt is not None:
        net_debt_ebitda = (debt - (liquid or 0)) / last["ebitda"]

    returned = (last["dividends"] or 0) + (last["buybacks"] or 0)
    m = {
        "revenue": last["revenue"], "cagr": cagr, "cagr_years": cagr_n, "growth_last": gs[-1] if gs else None,
        "accel": accel, "capex_da": last["capex_da"], "roic": last["roic"], "roic_trend": roic_trend,
        "ic_negative": last["ic_negative"], "fcf": last["fcf"], "fcf_margin": last["fcf_margin"],
        "fcf_trend": _slope(fcfm), "gross_slope": _slope([r["gross_margin"] for r in last3]),
        "op_slope": _slope([r["op_margin"] for r in last3]), "payout": last["payout"], "returned": returned,
        "dilution": last["dilution"], "dividend_cut": dividend_cut, "runway_months": runway,
        "implied_growth": implied, "net_debt_ebitda": net_debt_ebitda, "tax_rate": last["tax_rate"],
    }

    parts = _metric_scores(m)
    metrics_only, _ = _combine(parts, C.WEIGHTS)
    parts["dickinson"] = dk_aff
    scores, coverage = _combine(parts, C.WEIGHTS)
    ranked = sorted(scores, key=lambda k: scores[k], reverse=True)
    stage, second = ranked[0], ranked[1]
    gap = scores[stage] - scores[second]
    conf = min(1.0, gap / C.CONFIDENCE_FULL_GAP) * coverage
    few_years = len(path) < 3 or cagr_n < 2
    if few_years:
        conf *= C.FEW_YEARS_FACTOR
    conf = round(max(0.05, conf) * 100)

    # ---- סתירה ----
    contradiction = None
    if metrics_only:
        m_top = max(metrics_only, key=lambda k: metrics_only[k])
        if C.DICKINSON_AFFINITY[dk_stage][m_top] < C.CONTRADICTION_AFFINITY:
            contradiction = {
                "dickinson": dk_stage, "metrics": m_top,
                "text": (f"לפי התזרימים (Dickinson) החברה ב\"{C.DICKINSON_HE[dk_stage]}\", "
                         f"אבל המדדים התומכים מתאימים יותר ל\"{C.STAGES[m_top]['he']}\". "
                         "זה מידע ולא שגיאה: לרוב זו חברה בזמן מעבר, או שנה עם אירוע חד-פעמי (מכירת נכס, גיוס גדול)."),
            }

    table = _metric_table(m, parts, stage)
    risk = _risk(stage, m)
    why = _why(stage, dk_stage, vote_rows, table)

    return {
        "suitable": True,
        "stage": stage, "stage_he": C.STAGES[stage]["he"], "color": C.STAGES[stage]["color"],
        "warning": C.STAGES[stage]["warning"],
        "second": second, "second_he": C.STAGES[second]["he"],
        "confidence": conf, "low_confidence": few_years,
        "scores": {k: round(v, 3) for k, v in scores.items()},
        "metrics_only": {k: round(v, 3) for k, v in metrics_only.items()} if metrics_only else None,
        "coverage": round(coverage, 2),
        "dickinson": {
            "stage": dk_stage, "he": C.DICKINSON_HE[dk_stage],
            "votes": counts, "tie": len(leaders) > 1,
            "path": [{"end": r["end"], "year": r["end"].year, "pattern": r["pattern"], "stage": r["dickinson"],
                      "he": C.DICKINSON_HE[r["dickinson"]], "ocf": r["ocf"], "cfi": r["cfi_adj"],
                      "cfi_raw": r["cfi"], "cff": r["cff"], "near_zero": r["near_zero"]} for r in path],
        },
        "metrics": m, "table": table, "risk": risk,
        "inputs": {"fcf_now": fcf_now, "fcf_now_ttm": fcf_ttm is not None, "liquid": liquid, "debt": debt,
                   "market_cap": mcap, "fiscal_year_end": last["end"]},
        "contradiction": contradiction, "why": why,
        "judge_by": "בשלב הזה כדאי לשפוט את החברה לפי " + JUDGE_BY[stage],
        "years": [{k: r[k] for k in ("end", "revenue", "growth", "op_margin", "gross_margin", "fcf", "fcf_margin",
                                      "capex_da", "roic", "payout", "dilution", "pattern")} for r in rows[-C.YEARS_PATH:]],
        "stages": [{"code": k, **v} for k, v in C.STAGES.items()],
    }


EXPECT_TEXT = {
    "growth": {"startup": "גבוהה / לא יציבה", "growth": "מעל 15%", "profitable": "מעל 10%",
               "value": "0%–10%", "shakeout": "סביב 0%", "decline": "שלילית"},
    "capex": {"startup": "גבוה מאוד (מעל 2)", "growth": "מעל 1.5", "profitable": "מעל 1.1",
              "value": "0.8–1.5", "shakeout": "0.6–1.3", "decline": "מתחת ל-0.8"},
    "roic": {"startup": "שלילי", "growth": "נמוך או עולה", "profitable": "מעל 15%",
             "value": "מעל 10% ויציב", "shakeout": "נמוך", "decline": "נמוך ויורד"},
    "fcf": {"startup": "שלילי", "growth": "סביב 0 או חיובי", "profitable": "מעל 10%",
            "value": "חיובי וחזק (מעל 8%)", "shakeout": "חלש", "decline": "חלש ויורד"},
    "payout": {"startup": "דילול (5%+)", "growth": "דילול קל, בלי חלוקה", "profitable": "חלוקה חלקית",
               "value": "דיבידנד / קנייה עצמית (60%+ מה-FCF)", "shakeout": "—", "decline": "קיצוץ בחלוקה"},
}
LABELS = {"growth": "צמיחת הכנסות (CAGR)", "capex": "השקעות הוניות / פחת", "roic": "תשואה על ההון (ROIC)",
          "fcf": "שולי תזרים חופשי", "payout": "החזר לבעלים / דילול"}


def _metric_table(m, parts, stage):
    vals = {
        "growth": (f"{_fmt_pct(m['cagr'])} בשנה ({m['cagr_years']} שנים)" if m["cagr"] is not None
                   else ("הכנסות זניחות" if (m["revenue"] or 0) < C.STARTUP_REVENUE and m["revenue"] is not None else None)),
        "capex": f"{m['capex_da']:.2f}" if m["capex_da"] is not None else None,
        "roic": ("מעל 100% (הון מושקע שלילי)" if m["ic_negative"] else _fmt_pct(m["roic"])) if m["roic"] is not None else None,
        "fcf": _fmt_pct(m["fcf_margin"], 1),
        "payout": None,
    }
    pv = []
    if (m["returned"] or 0) == 0:
        pv.append("אין חלוקה")
    elif m["payout"] is not None:
        pv.append(f"{_fmt_pct(m['payout'])} מה-FCF")
    else:
        pv.append("מחלקת למרות תזרים חופשי שלילי")
    if m["dilution"] is not None:
        pv.append(f"מניות {'+' if m['dilution'] >= 0 else ''}{m['dilution'] * 100:.1f}%")
    vals["payout"] = ", ".join(pv) or None
    out = []
    for k in ("growth", "capex", "roic", "fcf", "payout"):
        sc = parts.get(k)
        s = None if sc is None else sc.get(stage)
        out.append({"key": k, "label": LABELS[k], "weight": C.WEIGHTS[k], "value": vals[k],
                    "expected": EXPECT_TEXT[k][stage], "score": None if s is None else round(s, 2),
                    "ok": None if s is None else s >= 0.5})
    return out


def _risk(stage, m):
    R = C.RISK
    score = C.RISK_BASE[stage]
    flags = []

    def add(pts, text, level="warn"):
        nonlocal score
        score += pts
        flags.append({"pts": pts, "text": text, "level": level})

    rw = m["runway_months"]
    if rw is not None:
        if rw < R["runway_high_months"]:
            add(35 if stage in ("startup", "growth") else 25, f"הקופה מספיקה לכ-{rw:.0f} חודשים בקצב השריפה הנוכחי – צפוי גיוס", "high")
        else:
            add(0, f"הקופה מספיקה לכ-{rw:.0f} חודשים", "info")
    if stage == "startup" and m["dilution"] is not None and m["dilution"] > R["dilution_warn"]:
        add(10, f"דילול של {m['dilution']:.0%} בשנה")
    if stage in ("growth", "profitable"):
        if m["accel"] is not None and m["accel"] < -R["slowdown_pp"]:
            add(15, f"האטה חדה בצמיחה: {m['accel'] * 100:+.0f} נק' אחוז בשנה האחרונה")
        if stage == "growth" and m["roic"] is not None and m["roic"] < 0 and not (m["roic_trend"] or 0) > 0:
            add(15, "ROIC שלילי שלא משתפר")
    if stage in ("profitable", "value", "shakeout", "decline"):
        if m["net_debt_ebitda"] is not None and m["net_debt_ebitda"] > R["net_debt_ebitda"]:
            add(20, f"חוב נטו גבוה: פי {m['net_debt_ebitda']:.1f} מה-EBITDA")
        if m["payout"] is not None and m["payout"] > R["payout_over_fcf"]:
            add(15, f"מחלקת לבעלים {m['payout']:.0%} מהתזרים החופשי – יותר ממה שהיא מייצרת")
        if m["op_slope"] is not None and m["op_slope"] < -R["margin_erosion_pp"]:
            add(10, f"שחיקה בשולי התפעול: {m['op_slope'] * 100:.1f} נק' אחוז בשנה")
    if m["implied_growth"] is not None and m["cagr"] is not None and m["implied_growth"] - m["cagr"] > R["implied_gap"]:
        add(10, f"המחיר מגלם צמיחה של כ-{m['implied_growth']:.0%} לנצח, יותר מהצמיחה בפועל ({m['cagr']:.0%}) – אזהרת תמחור")
    score = max(score, C.RISK_MIN.get(stage, 0))
    score = int(max(3, min(100, score)))
    level = next(name for lim, name in C.RISK_LEVELS if score < lim)
    if any(f["level"] == "high" for f in flags):
        level = "גבוה"
    return {"score": score, "level": level, "base": C.RISK_BASE[stage], "flags": flags}


def _why(stage, dk_stage, vote_rows, table):
    pats = " → ".join(r["pattern"] for r in vote_rows)
    s1 = (f"לפי Dickinson, ב-{len(vote_rows)} השנים האחרונות ({pats}) החברה ב\"{C.DICKINSON_HE[dk_stage]}\": "
          f"{DICKINSON_WHY[dk_stage]}.")
    good = [t["label"] for t in table if t["ok"]]
    bad = [t["label"] for t in table if t["ok"] is False]
    s2 = ""
    if good:
        s2 = f"מה שתומך ב\"{C.STAGES[stage]['he']}\": {', '.join(good)}."
    if bad:
        s2 += f" לא מתאים לפרופיל: {', '.join(bad)}."
    return [s1, s2.strip()] if s2 else [s1]
