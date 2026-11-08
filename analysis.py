"""
מנוע האבחון: שלב החברה לפי מסגרת "האבולוציה של חברה" (סטארטאפ → צמיחה → ערך),
מדדי בריאות (קופה, חוב, דילול, צמצום הפסדים), אירועי מעבר לרווח נקי, ורמת סיכון.

כל הספים נמצאים ב-Config וניתנים לכיוונון מהממשק.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, replace

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# הגדרות
# ---------------------------------------------------------------------------
@dataclass
class Config:
    startup_rev: float = 25e6        # הכנסות TTM מתחת לזה = סטארטאפ
    early_rev: float = 1e9           # עד כאן חברה "צעירה": הכפלת הכנסות מתחת לסף = מעבר סטארטאפ→צמיחה
    growth_min: float = 0.20         # צמיחת הכנסות שנתית מעליה = חברת צמיחה
    value_max: float = 0.08          # צמיחה מתחת לזה = חברת ערך (אם רווחית)
    lookback_cross_q: int = 8        # כמה רבעונים אחורה בודקים "חצתה את סף הסטארטאפ לאחרונה"
    inflection_window_q: int = 4     # כמה רבעונים אחרי המעבר לרווח עדיין מסומנים כ"מעבר לרווח"
    breakeven_fit_q: int = 6         # כמה רבעונים להתאמת מגמת צמצום ההפסד
    approaching_q: int = 4           # הערכת רווח תוך X רבעונים = "מתקרבת לרווח נקי"


STAGES = {
    "startup":           {"he": "סטארטאפ",                       "order": 0, "color": "#7C3AED"},
    "startup_to_growth": {"he": "מעבר: סטארטאפ ← צמיחה",         "order": 1, "color": "#A855F7"},
    "growth_loss":       {"he": "צמיחה הפסדית",                   "order": 2, "color": "#F59E0B"},
    "inflection":        {"he": "מעבר לרווח נקי (Money Time)",    "order": 3, "color": "#10B981"},
    "growth_profit":     {"he": "צמיחה רווחית",                   "order": 4, "color": "#22C55E"},
    "maturing":          {"he": "מעבר: צמיחה ← ערך",             "order": 5, "color": "#0EA5E9"},
    "value":             {"he": "ערך",                            "order": 6, "color": "#2563EB"},
    "value_to_growth":   {"he": "מעבר: ערך ← צמיחה (האצה מחדש)", "order": 7, "color": "#14B8A6"},
    "loss_slow":         {"he": "הפסדית בצמיחה איטית",            "order": 8, "color": "#EF4444"},
    "declining":         {"he": "התכווצות",                       "order": 9, "color": "#B91C1C"},
    "unknown":           {"he": "אין מספיק נתונים",               "order": 10, "color": "#9CA3AF"},
}

STAGE_EXPLAIN = {
    "startup": (
        "חברה עם רעיון ומוצר בפיתוח, בלי הכנסות משמעותיות. אין מכפילים, ולכן מעריכים אותה "
        "לפי המאזן: כמה מזומן יש, כמה היא שורפת בשנה, וכמה זמן נשאר לה עד שתצטרך לגייס (ולדלל)."
    ),
    "startup_to_growth": (
        "החברה התחילה להכניס כסף לראשונה מהמוצר. ההכנסות עדיין קטנות ביחס לשווי, אבל הקצב חד. "
        "השאלה המרכזית: האם ההכנסות הן מהמוצר עצמו או מתמלוגים/שיתופי פעולה, והאם הקופה מחזיקה עד שהמנוע יתפוס."
    ),
    "growth_loss": (
        "חברת צמיחה שכבר מכניסה כסף ממשי וצומחת מהר, אבל עדיין הפסדית. לפי השיטה מחפשים צמצום הפסדים "
        "עקבי, מאזן עם יותר מזומן מחוב, והערכה מתי תגיע לרווח נקי – והאם הקופה מספיקה עד אז."
    ),
    "inflection": (
        "החברה עברה לאחרונה לרווח נקי ב-12 החודשים האחרונים (Money Time). זה האירוע שבדוגמאות מהסרטון "
        "(Palantir, SoFi, Robinhood) הגיע יחד עם תחילת המהלך הגדול. בודקים שהרווח נובע מהפעילות ולא מאירוע חד-פעמי."
    ),
    "growth_profit": (
        "צמיחה גבוהה יחד עם רווחיות. כאן כבר יש מכפיל רווח, ומשווים את קצב הצמיחה למכפיל. "
        "הסיכון העיקרי: האטה בצמיחה שתוביל לכיווץ מכפיל."
    ),
    "maturing": (
        "חברה רווחית שהצמיחה שלה מתמתנת – בדרך להפוך לחברת ערך. מתמחרים לפי רווח ותזרים, "
        "ובודקים אם השוק עדיין מתמחר אותה כחברת צמיחה."
    ),
    "value": (
        "חברה בשלה: רווחית, צמיחה נמוכה. מתמחרים לפי מכפילי רווח ותזרים, דיבידנד ורכישות עצמיות. "
        "לפי הסרטון – חברות מצוינות, אבל לא מכאן מגיעות תשואות שמנצחות את המדד בפער גדול."
    ),
    "value_to_growth": (
        "חברה בשלה שחזרה להאיץ צמיחה (מנוע חדש, מוצר חדש, שוק חדש). שלב ביניים מעניין: "
        "השוק לפעמים עדיין מתמחר אותה כחברת ערך."
    ),
    "loss_slow": (
        "חברה הפסדית שהצמיחה שלה איטית – מחוץ למסלול האבולוציה הבריא. אין לה את הצמיחה שתצדיק הפסדים, "
        "וגם לא את הרווחיות של חברת ערך. כאן הקופה והחוב הם הכל."
    ),
    "declining": (
        "ההכנסות מתכווצות. לא שלב באבולוציה אלא סימן אזהרה – צריך להבין אם זה זמני (מחזוריות) או מבני."
    ),
    "unknown": "אין מספיק רבעונים מדווחים כדי לאבחן.",
}

STAGE_WATCH = {
    "startup": ["קצב שריפת מזומנים מול הקופה (כמה זמן נשאר)", "גיוסי הון ודילול", "אבני דרך: מתי ההכנסה הראשונה מהמוצר"],
    "startup_to_growth": ["מקור ההכנסות (מוצר מול תמלוגים)", "קצב צמיחת ההכנסות רבעון מול רבעון", "הקופה מול השריפה"],
    "growth_loss": ["צמצום ההפסד מרבעון לרבעון", "מתי הרווח הנקי צפוי", "האם הקופה מספיקה עד הרווח", "חוב שהולך וגדל מול המאזן"],
    "inflection": ["האם הרווח חוזר על עצמו ברבעונים הבאים", "רווח מפעילות מול רווח חד-פעמי", "מכפיל הרווח הראשון מול קצב הצמיחה"],
    "growth_profit": ["שימור קצב הצמיחה", "שיפור שולי רווח", "מכפיל מול צמיחה"],
    "maturing": ["האם הצמיחה ממשיכה להאט", "תזרים חופשי, דיבידנד ורכישות עצמיות", "מכפיל מול חברות ערך דומות"],
    "value": ["מכפיל רווח ותזרים", "יציבות הרווח", "תשואת דיבידנד ורכישות עצמיות"],
    "value_to_growth": ["מה מניע את ההאצה", "האם היא בת-קיימא", "האם המכפיל עוד לא משקף אותה"],
    "loss_slow": ["הקופה מול השריפה", "חוב ומועדי פירעון", "סימנים לשינוי כיוון (התייעלות, מוצר חדש)"],
    "declining": ["סיבת הירידה", "שולי רווח", "מאזן וחוב"],
    "unknown": [],
}

# ---------------------------------------------------------------------------
# עזר
# ---------------------------------------------------------------------------
def _contiguous_ttm(s: pd.Series) -> pd.Series:
    """סכום 4 רבעונים רק כשהרבעונים רצופים (פער 80–100 ימים) וכולם קיימים."""
    s = s.sort_index()
    idx = s.index
    vals = s.values.astype(float)
    out = np.full(len(s), np.nan)
    for i in range(3, len(s)):
        window = vals[i - 3:i + 1]
        if np.isnan(window).any():
            continue
        gaps = [(idx[j] - idx[j - 1]).days for j in range(i - 2, i + 1)]
        if all(80 <= g <= 100 for g in gaps):
            out[i] = window.sum()
    return pd.Series(out, index=idx)


def _value_year_ago(s: pd.Series, when: pd.Timestamp, tol_days: int = 25):
    target = when - pd.Timedelta(days=365)
    s = s.dropna()
    if s.empty:
        return np.nan
    diffs = np.abs((s.index - target).days)
    k = int(np.argmin(diffs))
    return s.iloc[k] if diffs[k] <= tol_days else np.nan


def _split_adjusted(s: pd.Series) -> pd.Series:
    """
    מתאים את מספר המניות לפיצולים: קפיצה בין שתי תקופות סמוכות ביחס כמעט שלם (פי 2, 3, 4, 10, 20...)
    היא פיצול ולא הנפקה. כל הערכים שלפני הפיצול מוכפלים ביחס, כדי שהגרף והדילול יהיו בני השוואה.
    """
    s = pd.Series(s, dtype=float).copy()
    v = s.dropna()
    for i in range(len(v) - 1, 0, -1):
        prev, cur = v.iloc[i - 1], v.iloc[i]
        if prev <= 0 or pd.isna(prev):
            continue
        r = cur / prev
        k = round(r)
        if 2 <= k <= 50 and abs(r - k) / k < 0.03:
            s.loc[s.index < v.index[i]] *= k
            v = s.dropna()
    return s


def _asof(s: pd.Series | None, when: pd.Timestamp, slack_days: int = 15, max_age_days: int = 200):
    """הערך המאזני האחרון עד התאריך – רק אם הוא לא ישן מדי."""
    if s is None:
        return np.nan
    s = s.dropna().sort_index()
    s = s[s.index <= when + pd.Timedelta(days=slack_days)]
    if not len(s) or (when - s.index[-1]).days > max_age_days:
        return np.nan
    return float(s.iloc[-1])


# ---------------------------------------------------------------------------
# מדדים רבעוניים
# ---------------------------------------------------------------------------
def compute_metrics(quarterly: pd.DataFrame, balance: pd.DataFrame, period_months: int = 3) -> pd.DataFrame:
    q = quarterly.copy().sort_index()
    m = pd.DataFrame(index=q.index)
    m["revenue_q"] = q.get("revenue")
    m["net_income_q"] = q.get("net_income")
    m["ocf_q"] = q.get("ocf")
    capex = q.get("capex")
    if capex is not None and m["ocf_q"] is not None:
        capex = capex.reindex(q.index)
        # אם אין דיווח capex ברבעון – מניחים 0 רק כשיש תזרים תפעולי
        capex = capex.where(capex.notna() | m["ocf_q"].isna(), 0.0)
        m["fcf_q"] = m["ocf_q"] - capex.abs()
    elif "ocf_q" in m:
        m["fcf_q"] = m["ocf_q"]
    m["sbc_q"] = q.get("sbc")
    m["op_income_q"] = q.get("op_income")
    m["shares_avg"] = q.get("shares_avg")
    m["cfi_q"] = q.get("cfi")
    m["cff_q"] = q.get("cff")

    for col in ["revenue", "net_income", "op_income", "ocf", "cfi", "cff", "fcf", "sbc"]:
        src = m.get(f"{col}_q")
        if src is None or not src.notna().any():
            m[f"{col}_ttm"] = np.nan
        elif period_months == 12:
            m[f"{col}_ttm"] = src  # בדוח שנתי – התקופה עצמה היא 12 חודשים
        else:
            m[f"{col}_ttm"] = _contiguous_ttm(src)

    rev_yoy = []
    for t in m.index:
        cur = m.at[t, "revenue_ttm"]
        prev = _value_year_ago(m["revenue_ttm"], t)
        if pd.isna(cur) or pd.isna(prev):
            rev_yoy.append(np.nan)
        elif prev <= 1e6:  # מאפס/כמעט אפס – צמיחה "אינסופית"
            rev_yoy.append(np.inf if cur > 5e6 else np.nan)
        else:
            rev_yoy.append(cur / prev - 1)
    m["revenue_yoy"] = rev_yoy
    rq = m["revenue_q"]
    m["revenue_q_yoy"] = [ (rq.at[t] / p - 1) if (not pd.isna(rq.at[t]) and not pd.isna(p := _value_year_ago(rq, t)) and p > 0) else np.nan for t in m.index ]

    m["net_margin_ttm"] = m["net_income_ttm"] / m["revenue_ttm"].where(m["revenue_ttm"] > 0)
    # רווח נקי חיובי שנובע מרווח לא תפעולי (למשל שערוך כתבי אופציה או ריבית על הקופה) כשהפעילות עצמה מפסידה
    # לא נחשב "מעבר לרווח". לסיווג משתמשים ברווח "ליבה": אם הרווח התפעולי שלילי – הוא קובע.
    op = m["op_income_ttm"]
    m["non_operating_profit"] = (m["net_income_ttm"] > 0) & (op < 0)
    m["ni_core_ttm"] = m["net_income_ttm"].where(~m["non_operating_profit"], op)

    b = balance.copy().sort_index() if balance is not None else pd.DataFrame()
    # נתון מאזני נלקח רק מהמאזן של אותה תקופה – לא ממשיכים להציג ערך ישן שלא דווח שוב
    # (מספר מניות מגיע מעמוד השער, שמתוארך כמה שבועות אחרי סוף התקופה – לכן חלון רחב יותר)
    for col in ["cash", "st_investments", "securities_total", "lt_securities", "debt", "shares"]:
        series = b[col] if col in b else None
        age = 20 if col != "shares" else (200 if period_months == 3 else 420)
        # מספר המניות מעמוד השער מתוארך 3–6 שבועות אחרי סוף התקופה, ולכן נספר לתקופה שעליה הדוח מדווח
        m[col] = [_asof(series, t, slack_days=15 if col != "shares" else 60, max_age_days=age) for t in m.index]
    for col in ["shares", "shares_avg"]:
        if col in m:
            m[col] = _split_adjusted(m[col])
    # קופה = מזומן + ניירות ערך סחירים. אם יש סה"כ ניירות ערך (שוטף + לא שוטף) – לוקחים את הגדול מבין החישובים
    by_parts = m["cash"].fillna(0) + m["st_investments"].fillna(0) + m["lt_securities"].fillna(0)
    by_total = m["cash"].fillna(0) + m["securities_total"].fillna(0)
    # יש חברות (למשל טסלה) שבהן "סך ניירות הערך" כבר כולל את שווי המזומנים – ואז הוספת המזומן סופרת אותו פעמיים
    st_parts = m["cash"].fillna(0) + m["st_investments"].fillna(0)
    incl_cash = (m["securities_total"] - st_parts).abs() <= 0.02 * m["securities_total"].abs()
    by_total = by_total.where(~incl_cash.fillna(False), m["securities_total"])
    m["liquid"] = np.maximum(by_parts, by_total)
    m.loc[m[["cash", "st_investments", "securities_total", "lt_securities"]].isna().all(axis=1), "liquid"] = np.nan
    return m


# ---------------------------------------------------------------------------
# סיווג שלב
# ---------------------------------------------------------------------------
def classify_at(m: pd.DataFrame, i: int, cfg: Config) -> str:
    row = m.iloc[i]
    rev, ni, g = row["revenue_ttm"], row["ni_core_ttm"], row["revenue_yoy"]

    if pd.isna(ni):
        return "unknown"
    if pd.isna(rev) or rev < cfg.startup_rev:
        return "startup"

    past = m.iloc[max(0, i - cfg.lookback_cross_q):i]
    past_rev = past["revenue_ttm"]
    crossed_recently = len(past_rev.dropna()) > 0 and (past_rev.dropna() < cfg.startup_rev).any()
    doubling_young = (not pd.isna(g) and g >= 1.0 and rev < cfg.early_rev)
    if crossed_recently or doubling_young:
        return "startup_to_growth"

    # מעבר לרווח נקי: TTM חיובי לראשונה אחרי לפחות 2 רבעוני TTM שליליים
    if ni > 0:
        hist = m["ni_core_ttm"].iloc[:i + 1].dropna()
        if len(hist) >= 3:
            pos = (hist > 0).values
            # הרבעון הראשון ברצף החיובי הנוכחי
            k = len(pos) - 1
            while k > 0 and pos[k - 1]:
                k -= 1
            run_len = len(pos) - k
            negatives_before = (~pos[:k]).sum()
            if run_len <= cfg.inflection_window_q and negatives_before >= 2:
                if pd.isna(g) or g >= cfg.value_max:
                    return "inflection"

    if pd.isna(g):
        return "unknown"

    if g >= cfg.growth_min:
        if ni < 0:
            return "growth_loss"
        # האצה מחדש: 4–12 רבעונים אחורה רוב הזמן צמיחה נמוכה
        older = m["revenue_yoy"].iloc[max(0, i - 12):max(0, i - 4)].replace([np.inf], np.nan).dropna()
        if len(older) >= 4 and (older < cfg.value_max).mean() >= 0.5:
            return "value_to_growth"
        return "growth_profit"

    if g < -0.10:
        return "declining" if ni < 0 else "value"

    if g >= cfg.value_max:
        return "maturing" if ni > 0 else "loss_slow"

    return "value" if ni > 0 else "loss_slow"


def stage_history(m: pd.DataFrame, cfg: Config) -> pd.Series:
    return pd.Series([classify_at(m, i, cfg) for i in range(len(m))], index=m.index)


# ---------------------------------------------------------------------------
# הערכת זמן לרווח נקי
# ---------------------------------------------------------------------------
def breakeven_estimate(m: pd.DataFrame, cfg: Config, period_months: int = 3) -> dict:
    ni_q = m["net_income_q"].dropna()
    res = {"quarters": None, "months": None, "slope": None, "r2": None, "trend": None}
    if len(ni_q) < (4 if period_months == 3 else 3):
        return res
    recent = ni_q.iloc[-cfg.breakeven_fit_q:]
    x = np.arange(len(recent), dtype=float)
    y = recent.values.astype(float)
    slope, intercept = np.polyfit(x, y, 1)
    pred = slope * x + intercept
    ss_res = ((y - pred) ** 2).sum()
    ss_tot = ((y - y.mean()) ** 2).sum()
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0
    res.update(slope=float(slope), r2=float(r2))

    ttm = m["ni_core_ttm"].dropna()
    if ttm.empty:
        return res
    if ttm.iloc[-1] > 0:
        res["trend"] = "profitable"
        res["quarters"] = 0
        res["months"] = 0
        return res

    scale = max(1.0, float(np.abs(y).mean()))
    if abs(slope) < 0.01 * scale:
        res["trend"] = "flat"
    else:
        res["trend"] = "narrowing" if slope > 0 else "widening"
    if slope <= 0 or res["trend"] == "flat":
        return res
    # הקרנה קדימה: רבעונים עתידיים לפי המגמה, עד ש-TTM המוקרן חיובי
    k = 4 if period_months == 3 else 1  # כמה תקופות מרכיבות 12 חודשים
    window = list(ni_q.iloc[-k:].values.astype(float))
    n = len(recent)
    for h in range(1, (21 if period_months == 3 else 6)):
        nxt = slope * (n - 1 + h) + intercept
        window = window[1:] + [nxt]
        if sum(window) > 0:
            res["quarters"] = h if period_months == 3 else None
            res["months"] = h * period_months
            break
    return res


# ---------------------------------------------------------------------------
# אירועי מעבר לרווח נקי + ביצועי המניה מאז
# ---------------------------------------------------------------------------
def inflection_events(m: pd.DataFrame, quarterly: pd.DataFrame, prices: pd.Series | None,
                      min_revenue: float = 0.0) -> pd.DataFrame:
    """מעבר לרווח נקי – רק כשהרווח נובע מהפעילות, ורק כשיש לחברה הכנסות משמעותיות (לא סטארטאפ)."""
    ttm = m["ni_core_ttm"]
    rows = []
    vals = ttm.values
    for i in range(1, len(vals)):
        if pd.isna(vals[i]) or pd.isna(vals[i - 1]):
            continue
        if vals[i] > 0 and vals[i - 1] <= 0:
            prior_neg = (ttm.iloc[:i].dropna() <= 0).sum()
            if prior_neg < 2:
                continue
            rev_i = m["revenue_ttm"].iloc[i]
            if pd.isna(rev_i) or rev_i < min_revenue:
                continue
            qend = ttm.index[i]
            filed = quarterly["filed"].get(qend) if "filed" in quarterly else None
            event_date = pd.Timestamp(filed) if filed is not None and not pd.isna(filed) else qend + pd.Timedelta(days=45)
            row = {"quarter_end": qend, "event_date": event_date, "ni_ttm": vals[i]}
            if prices is not None and len(prices):
                after = prices[prices.index >= event_date]
                if len(after):
                    p0 = float(after.iloc[0])
                    row["price_at_event"] = p0
                    row["price_now"] = float(prices.iloc[-1])
                    row["return_since"] = float(prices.iloc[-1]) / p0 - 1
                    row["max_return_since"] = float(after.max()) / p0 - 1
                    yr = after[after.index <= event_date + pd.Timedelta(days=365)]
                    if len(yr) and (after.index[-1] - event_date).days >= 360:
                        row["return_12m"] = float(yr.iloc[-1]) / p0 - 1
            rows.append(row)
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# אבחון מלא + סיכון
# ---------------------------------------------------------------------------
@dataclass
class Diagnosis:
    stage: str
    stage_he: str
    approaching_profit: bool
    metrics: pd.DataFrame
    history: pd.Series
    latest: dict
    breakeven: dict
    runway: dict
    risk_score: int
    risk_level: str
    risk_reasons: list = field(default_factory=list)
    positives: list = field(default_factory=list)
    events: pd.DataFrame = field(default_factory=pd.DataFrame)
    explain: str = ""
    watch: list = field(default_factory=list)


BASE_RISK = {
    "startup": 35, "startup_to_growth": 28, "growth_loss": 20, "loss_slow": 30, "declining": 35,
    "inflection": 15, "growth_profit": 10, "maturing": 8, "value": 5, "value_to_growth": 10, "unknown": 25,
}


def _risk_level(score: int) -> str:
    if score < 25:
        return "נמוך"
    if score < 50:
        return "בינוני"
    if score < 75:
        return "גבוה"
    return "גבוה מאוד"


def diagnose(data, cfg: Config | None = None) -> Diagnosis:
    cfg = cfg or Config()
    pm = getattr(data, "period_months", 3)
    if pm == 12:  # התאמת חלונות הזמן לנתונים שנתיים
        cfg = replace(cfg, lookback_cross_q=2, inflection_window_q=1, breakeven_fit_q=4)
    m = compute_metrics(data.quarterly, data.balance, pm)
    m = m[m["net_income_q"].notna() | m["revenue_q"].notna()]
    hist = stage_history(m, cfg)

    # השלב הנוכחי = הרבעון האחרון שאפשר לסווג
    valid = hist[hist != "unknown"]
    stage = valid.iloc[-1] if len(valid) else "unknown"
    li = m.index.get_loc(valid.index[-1]) if len(valid) else len(m) - 1
    last = m.iloc[li] if len(m) else pd.Series(dtype=float)

    be = breakeven_estimate(m.iloc[:li + 1], cfg, pm)

    # ---- קופה ----
    liquid = last.get("liquid", np.nan)
    n_recent = 4 if pm == 3 else 1
    fcf_recent = m["fcf_q"].iloc[max(0, li - n_recent + 1):li + 1].dropna() if "fcf_q" in m else pd.Series(dtype=float)
    burn_q = -fcf_recent.mean() if len(fcf_recent) else np.nan  # שריפה לתקופה (רבעון או שנה)
    runway = {"liquid": liquid, "burn_q_fcf": burn_q, "months_fcf": None, "months_ni": None, "self_funded": False}
    if not pd.isna(burn_q) and not pd.isna(liquid):
        if burn_q > 0:
            runway["months_fcf"] = max(0.0, liquid) / burn_q * pm
        else:
            runway["self_funded"] = True
    ni_ttm = last.get("net_income_ttm", np.nan)
    if not pd.isna(ni_ttm) and ni_ttm < 0 and not pd.isna(liquid):
        runway["months_ni"] = max(0.0, liquid) / (-ni_ttm) * 12  # השיטה מהסרטון: קופה / הפסד שנתי

    # ---- דילול ----
    shares_now = last.get("shares", np.nan)
    shares_prev = _value_year_ago(m["shares"].iloc[:li + 1], m.index[li]) if len(m) else np.nan
    dilution = shares_now / shares_prev - 1 if shares_prev and not pd.isna(shares_prev) and not pd.isna(shares_now) else np.nan
    # דילול = שינוי במספר המניות הממוצע המדולל (זה שבחישוב הרווח למניה), רבעון מול אותו רבעון אשתקד.
    # מספר המניות בעמוד השער כולל גם מניות חסומות שטרם הבשילו, ולכן יכול להגזים (למשל טסלה אחרי מענק המנכ"ל).
    dilution_basis = "cover"
    avg = m["shares_avg"].iloc[:li + 1].dropna() if "shares_avg" in m and len(m) else pd.Series(dtype=float)
    if len(avg) and (m.index[li] - avg.index[-1]).days <= 100:
        avg_prev = _value_year_ago(avg, avg.index[-1])
        if not pd.isna(avg_prev) and avg_prev > 0:
            dilution, dilution_basis = avg.iloc[-1] / avg_prev - 1, "avg"

    # ---- שווי ----
    mcap = data.market_cap if data.currency == "USD" else None
    rev_ttm = last.get("revenue_ttm", np.nan)
    ps = mcap / rev_ttm if mcap and rev_ttm and rev_ttm > 0 else np.nan
    pe = mcap / ni_ttm if mcap and not pd.isna(ni_ttm) and ni_ttm > 0 else np.nan
    fcf_ttm = last.get("fcf_ttm", np.nan)
    pfcf = mcap / fcf_ttm if mcap and not pd.isna(fcf_ttm) and fcf_ttm > 0 else np.nan

    # ---- תנודתיות ----
    vol = np.nan
    if data.prices is not None and len(data.prices) > 60:
        r = data.prices.iloc[-252:].pct_change().dropna()
        vol = float(r.std() * math.sqrt(252))

    # ---- האטה בצמיחה ----
    g = last.get("revenue_yoy", np.nan)
    g_prev = _value_year_ago(m["revenue_yoy"].replace([np.inf], np.nan).iloc[:li + 1], m.index[li]) if len(m) else np.nan

    sbc_ratio = last.get("sbc_ttm", np.nan) / rev_ttm if rev_ttm and rev_ttm > 0 else np.nan
    debt = last.get("debt", np.nan)

    latest = {
        "quarter_end": m.index[li] if len(m) else None,
        "revenue_ttm": rev_ttm, "revenue_yoy": g, "revenue_yoy_prev": g_prev,
        "revenue_q_yoy": last.get("revenue_q_yoy", np.nan),
        "net_income_ttm": ni_ttm, "net_margin_ttm": last.get("net_margin_ttm", np.nan),
        "fcf_ttm": fcf_ttm, "sbc_ttm": last.get("sbc_ttm", np.nan), "sbc_ratio": sbc_ratio,
        "cash": last.get("cash", np.nan), "st_investments": last.get("st_investments", np.nan),
        "liquid": liquid, "debt": debt,
        "shares": shares_now, "dilution_yoy": dilution, "dilution_basis": dilution_basis,
        "cover_shares_yoy": (shares_now / shares_prev - 1) if shares_prev and not pd.isna(shares_prev) and not pd.isna(shares_now) else np.nan,
        "market_cap": mcap, "ps": ps, "pe": pe, "pfcf": pfcf, "volatility": vol,
        "last_price": data.last_price,
        "non_operating_profit": bool(last.get("non_operating_profit", False)) if len(m) else False,
        "op_income_ttm": last.get("op_income_ttm", np.nan),
    }

    # ---- ניקוד סיכון ----
    score = BASE_RISK.get(stage, 25)
    reasons, positives = [], []
    reasons.append((BASE_RISK.get(stage, 25), f"בסיס לשלב \"{STAGES[stage]['he']}\""))

    def add(pts, text):
        nonlocal score
        score += pts
        (reasons if pts > 0 else positives).append((pts, text))

    rm = runway["months_fcf"]
    if runway["self_funded"]:
        add(-5, "תזרים חופשי חיובי – החברה מממנת את עצמה")
    elif rm is not None:
        if rm < 12:
            add(30, f"הקופה מספיקה לכ-{rm:.0f} חודשים בלבד – סכנת גיוס/דילול גבוהה")
        elif rm < 24:
            add(15, f"הקופה מספיקה לכ-{rm:.0f} חודשים")
        elif rm < 36:
            add(6, f"הקופה מספיקה לכ-{rm:.0f} חודשים")
        else:
            add(-3, f"קופה ארוכה – כ-{rm:.0f} חודשים בקצב השריפה הנוכחי")

    if be.get("months") and be["months"] > 0 and rm is not None:
        be_months = be["months"]
        if be_months > rm:
            add(10, f"לפי המגמה, הרווח צפוי בעוד ~{be_months} חודשים – אחרי שהקופה נגמרת. צפוי גיוס")
        else:
            add(-3, "לפי המגמה, הקופה מספיקה עד הרווח הנקי הצפוי")

    if not pd.isna(debt) and not pd.isna(liquid) and debt > liquid:
        if not pd.isna(ni_ttm) and ni_ttm < 0:
            add(12, "חוב גבוה מהמזומן בחברה הפסדית")
        else:
            add(5, "חוב גבוה מהמזומן")
    elif not pd.isna(liquid) and (pd.isna(debt) or debt < liquid):
        add(-2, "יותר מזומן מחוב")

    if not pd.isna(dilution):
        if dilution > 0.20:
            add(15, f"דילול כבד: מספר המניות גדל ב-{dilution:.0%} בשנה")
        elif dilution > 0.08:
            add(8, f"דילול משמעותי: {dilution:.0%} בשנה")
        elif dilution > 0.03:
            add(3, f"דילול מתון: {dilution:.0%} בשנה")
        elif dilution < -0.02:
            add(-3, f"רכישה עצמית: מספר המניות ירד ב-{-dilution:.0%}")

    if be.get("trend") == "widening":
        add(10, "ההפסדים מתרחבים מתקופה לתקופה")
    elif be.get("trend") == "narrowing":
        add(-2, "ההפסדים מצטמצמים מתקופה לתקופה")

    if not pd.isna(g) and np.isfinite(g):
        if g < -0.10:
            add(10, f"ההכנסות ירדו ב-{-g:.0%} בשנה")
        elif stage in ("growth_loss", "growth_profit", "inflection") and not pd.isna(g_prev) and g_prev > 0.3 and g < g_prev * 0.5:
            add(5, f"האטה חדה בצמיחה: מ-{g_prev:.0%} ל-{g:.0%}")

    if not pd.isna(ps):
        if ps > 40:
            add(12, f"תמחור קיצוני: מכפיל מכירות {ps:.0f}")
        elif ps > 20:
            add(7, f"תמחור גבוה: מכפיל מכירות {ps:.0f}")
        elif ps > 10:
            add(3, f"מכפיל מכירות {ps:.0f}")

    if latest["non_operating_profit"]:
        add(8, "הרווח הנקי חיובי רק בזכות רווח לא תפעולי – הפעילות עצמה מפסידה")

    if not pd.isna(sbc_ratio) and sbc_ratio > 0.30:
        add(5, f"תגמול במניות = {sbc_ratio:.0%} מההכנסות (דילול סמוי)")

    if not pd.isna(vol):
        if vol > 0.80:
            add(8, f"תנודתיות שנתית קיצונית: {vol:.0%}")
        elif vol > 0.50:
            add(4, f"תנודתיות שנתית גבוהה: {vol:.0%}")

    score = int(max(3, min(100, round(score))))  # אין מניה בלי סיכון
    approaching = (
        stage in ("growth_loss", "startup_to_growth", "loss_slow")
        and be.get("months") is not None and 0 < be["months"] <= cfg.approaching_q * 3
    )

    events = inflection_events(m, data.quarterly, data.prices, cfg.startup_rev)
    if pm == 12 and len(events) and "filed" not in data.quarterly:
        events["event_date"] = events["quarter_end"] + pd.Timedelta(days=100)

    return Diagnosis(
        stage=stage, stage_he=STAGES[stage]["he"], approaching_profit=approaching,
        metrics=m, history=hist, latest=latest, breakeven=be, runway=runway,
        risk_score=score, risk_level=_risk_level(score),
        risk_reasons=reasons, positives=positives, events=events,
        explain=STAGE_EXPLAIN[stage], watch=STAGE_WATCH[stage],
    )


# ---------------------------------------------------------------------------
# ציונים 1–10 (בסגנון כרטיסי דירוג) + תמונת מצב במילים
# ---------------------------------------------------------------------------
def _bucket(x, edges, scores):
    """edges עולים; מחזיר את הציון של הטווח שבו x נמצא."""
    for e, s in zip(edges, scores):
        if x < e:
            return s
    return scores[-1]


def scorecards(dg: "Diagnosis") -> dict:
    L = dg.latest
    out = {}

    g = L.get("revenue_yoy")
    if g is not None and not pd.isna(g):
        out["growth"] = 10 if np.isinf(g) else _bucket(g, [-0.10, 0, 0.05, 0.10, 0.20, 0.30, 0.50], [1, 2, 3, 5, 6, 7, 8, 10])

    nm = L.get("net_margin_ttm")
    if nm is not None and not pd.isna(nm):
        s = _bucket(nm, [-0.5, -0.2, -0.05, 0, 0.05, 0.10, 0.20], [1, 2, 3, 4, 5, 6, 8, 10])
        fcf = L.get("fcf_ttm")
        if fcf is not None and not pd.isna(fcf) and fcf > 0 and s < 10:
            s += 1
        out["profitability"] = s
    elif L.get("net_income_ttm") is not None and not pd.isna(L.get("net_income_ttm")):
        out["profitability"] = 1 if L["net_income_ttm"] < 0 else 6

    # חוסן פיננסי: קופה, חוב, דילול
    rw = dg.runway
    if rw["self_funded"]:
        s = 8
    elif rw["months_fcf"] is not None:
        s = _bucket(rw["months_fcf"], [12, 24, 36, 60], [2, 4, 5, 6, 7])
    else:
        s = 5
    liquid, debt = L.get("liquid"), L.get("debt")
    if liquid is not None and not pd.isna(liquid):
        if debt is None or pd.isna(debt) or debt <= liquid:
            s += 1
        elif debt > 2 * liquid:
            s -= 2
        else:
            s -= 1
    dil = L.get("dilution_yoy")
    if dil is not None and not pd.isna(dil):
        if dil > 0.15:
            s -= 2
        elif dil > 0.05:
            s -= 1
        elif dil < -0.02:
            s += 1
    out["strength"] = int(max(1, min(10, s)))

    # תמחור: ציון גבוה = זול יותר
    pe, ps = L.get("pe"), L.get("ps")
    if pe is not None and not pd.isna(pe):
        out["valuation"] = _bucket(pe, [12, 18, 25, 35, 50, 80], [10, 8, 7, 5, 4, 3, 2])
    elif ps is not None and not pd.isna(ps):
        out["valuation"] = _bucket(ps, [1, 2, 4, 8, 15, 30], [8, 7, 6, 4, 3, 2, 1])
    return out


def _m(x):
    if x is None or pd.isna(x):
        return None
    a, sign = abs(x), ("-" if x < 0 else "")
    if a >= 1e9:
        return f"{sign}${a/1e9:.1f} מיליארד"
    if a >= 1e6:
        return f"{sign}${a/1e6:.0f} מיליון"
    return f"{sign}${a:,.0f}"


def status_narrative(dg: "Diagnosis", name: str) -> list[str]:
    """תמונת מצב כללית בעברית, משפט לכל נושא."""
    L = dg.latest
    out = []
    out.append(f"{name} נמצאת בשלב \"{dg.stage_he}\" במסלול האבולוציה של חברה.")

    rev, g, ni = L.get("revenue_ttm"), L.get("revenue_yoy"), L.get("net_income_ttm")
    if rev is not None and not pd.isna(rev) and rev > 0:
        s = f"ב-12 החודשים האחרונים הכניסה {_m(rev)}"
        if g is not None and not pd.isna(g):
            s += " – לראשונה הכנסות משמעותיות" if np.isinf(g) else (f", צמיחה של {g:.0%} לעומת שנה קודם" if g >= 0 else f", ירידה של {-g:.0%} לעומת שנה קודם")
        if ni is not None and not pd.isna(ni):
            s += f", ו{'הרוויחה' if ni > 0 else 'הפסידה'} {_m(abs(ni))}."
        out.append(s if s.endswith(".") else s + ".")
    elif ni is not None and not pd.isna(ni):
        out.append(f"אין לה עדיין הכנסות משמעותיות, וב-12 החודשים האחרונים הפסידה {_m(abs(ni))}.")

    rw = dg.runway
    if rw["self_funded"]:
        out.append("התזרים החופשי חיובי – החברה מממנת את הפעילות בעצמה ולא תלויה בגיוסים.")
    elif rw["months_fcf"] is not None:
        mth = rw["months_fcf"]
        out.append(
            f"בקצב השריפה הנוכחי הקופה ({_m(L.get('liquid'))}) מספיקה לכ-{mth:.0f} חודשים"
            + (" – צפוי גיוס הון בטווח הקרוב." if mth < 18 else ".")
        )

    be = dg.breakeven
    if dg.stage in ("growth_loss", "startup_to_growth", "loss_slow"):
        if be.get("trend") == "narrowing" and be.get("months"):
            out.append(f"ההפסדים מצטמצמים; לפי המגמה, רווח נקי שנתי צפוי בעוד כ-{be['months']} חודשים.")
        elif be.get("trend") == "widening":
            out.append("ההפסדים מתרחבים – עדיין אין מגמה ברורה לכיוון רווח.")

    dil = L.get("dilution_yoy")
    if dil is not None and not pd.isna(dil):
        if dil > 0.08:
            out.append(f"מספר המניות גדל ב-{dil:.0%} בשנה האחרונה – דילול משמעותי לבעלי המניות.")
        elif dil < -0.02:
            out.append(f"החברה רוכשת מניות בחזרה: מספר המניות ירד ב-{-dil:.0%} בשנה.")

    if len(dg.events):
        ev = dg.events.iloc[-1]
        when = pd.Timestamp(ev["event_date"]).strftime("%m/%Y")
        s = f"החברה עברה לרווח נקי בדוח שפורסם ב-{when}"
        if "return_since" in ev and not pd.isna(ev.get("return_since")):
            s += f"; מאז המניה {'עלתה' if ev['return_since'] >= 0 else 'ירדה'} {abs(ev['return_since']):.0%}"
        out.append(s + ".")

    out.append(f"רמת הסיכון ביחס לשלב: {dg.risk_level} ({dg.risk_score}/100).")
    return out


# ---------------------------------------------------------------------------
# "על הסף" – קרבה לגבול בין שלבים + כיוון התנועה
# ---------------------------------------------------------------------------
def _trend_eta(values: list, threshold: float, max_periods: int = 8):
    """
    מתאים קו מגמה לערכים האחרונים ומחזיר (שיפוע, תקופות עד חציית הסף) – או None אם לא נחצה בטווח.
    """
    v = [x for x in values if x is not None and not pd.isna(x) and np.isfinite(x)]
    if len(v) < 3:
        return None, None
    x = np.arange(len(v), dtype=float)
    slope, intercept = np.polyfit(x, np.array(v, dtype=float), 1)
    last = slope * (len(v) - 1) + intercept
    if slope == 0:
        return slope, None
    k = (threshold - last) / slope
    if 0 < k <= max_periods:
        return slope, int(math.ceil(k))
    return slope, None


def edge_signals(dg: "Diagnosis", cfg: Config | None = None) -> list[dict]:
    """
    מחזיר רשימת התראות "על הסף": חברה שקרובה לגבול של שלב אחר ונעה לכיוונו.
    כל התראה: to (קוד שלב), title, text, eta (רבעונים, אם ניתן להעריך), direction (up/down).
    """
    cfg = cfg or Config()
    m = dg.metrics
    if m is None or m.empty:
        return []
    L = dg.latest
    stage = dg.stage
    out = []
    g = L.get("revenue_yoy")
    g_hist = list(m["revenue_yoy"].replace([np.inf, -np.inf], np.nan).dropna().iloc[-4:].values)
    rev = L.get("revenue_ttm")
    rev_hist = list(m["revenue_ttm"].dropna().iloc[-4:].values)

    def add(to, title, text, eta=None, direction="up"):
        out.append({"to": to, "to_he": STAGES[to]["he"], "title": title, "text": text, "eta": eta, "direction": direction})

    # סטארטאפ שמתקרב לסף ההכנסות
    if stage == "startup" and rev is not None and not pd.isna(rev) and rev > 0.3 * cfg.startup_rev:
        _, eta = _trend_eta(rev_hist, cfg.startup_rev)
        if eta or rev > 0.6 * cfg.startup_rev:
            add("startup_to_growth", "ההכנסות מתקרבות לסף",
                f"הכנסות של ${rev/1e6:.0f}M ב-12 חודשים, מול סף של ${cfg.startup_rev/1e6:.0f}M.", eta)

    finite_g = g is not None and not pd.isna(g) and np.isfinite(g)

    # הפסדית שמתקרבת לרווח
    if dg.approaching_profit and dg.breakeven.get("months"):
        q = max(1, round(dg.breakeven["months"] / 3))
        add("inflection", "מתקרבת לרווח נקי",
            "ההפסדים מצטמצמים בעקביות, ולפי המגמה הרווח הנקי השנתי יהפוך לחיובי.", q)

    # רווחית עם שולי רווח דקים ורווח יורד – סכנת חזרה להפסד
    if stage in ("inflection", "growth_profit", "maturing", "value", "value_to_growth"):
        nm = L.get("net_margin_ttm")
        ni_q = list(m["net_income_q"].dropna().iloc[-4:].values)
        if nm is not None and not pd.isna(nm) and 0 < nm < 0.04 and len(ni_q) >= 3:
            slope, _ = _trend_eta(ni_q, 0)
            if slope is not None and slope < 0:
                add("growth_loss" if finite_g and g >= cfg.growth_min else "loss_slow", "סכנת חזרה להפסד",
                    f"שולי הרווח דקים ({nm:.1%}) והרווח הרבעוני יורד.", None, "down")

    if finite_g and len(g_hist) >= 3:
        slope, _ = _trend_eta(g_hist, 0)
        # צמיחה שמאטה לכיוון סף הצמיחה
        if stage in ("growth_profit", "growth_loss", "inflection", "value_to_growth") and g < cfg.growth_min + 0.10 and slope < 0:
            _, eta = _trend_eta(g_hist, cfg.growth_min)
            to = "maturing" if (L.get("net_income_ttm") or 0) > 0 else "loss_slow"
            add(to, "הצמיחה מאטה לכיוון הסף",
                f"צמיחה של {g:.0%} בשנה (סף חברת צמיחה: {cfg.growth_min:.0%}) – יורדת ברבעונים האחרונים.", eta, "down")
        # בשלה שהצמיחה שלה מאטה לכיוון ערך
        if stage == "maturing" and g < cfg.value_max + 0.05 and slope < 0:
            _, eta = _trend_eta(g_hist, cfg.value_max)
            add("value", "מתקרבת לשלב הערך",
                f"צמיחה של {g:.0%} בשנה (סף חברת ערך: {cfg.value_max:.0%}) – ממשיכה לרדת.", eta, "down")
        # האצה מחדש לכיוון צמיחה
        if stage in ("maturing", "value", "loss_slow") and g > cfg.growth_min - 0.08 and slope > 0:
            _, eta = _trend_eta(g_hist, cfg.growth_min)
            to = "value_to_growth" if stage != "loss_slow" else "growth_loss"
            add(to, "הצמיחה מאיצה",
                f"צמיחה של {g:.0%} בשנה ועולה – מתקרבת לסף חברת צמיחה ({cfg.growth_min:.0%}).", eta, "up")
    return out
