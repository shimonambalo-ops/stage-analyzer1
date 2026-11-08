"""
שכבת נתונים: משיכת דוחות כספיים מ-SEC EDGAR (חינמי, ללא מפתח) ומחירים מ-yfinance.

SEC מחייבת User-Agent מזהה (שם + מייל). מגדירים אותו בסרגל הצד של האפליקציה
או במשתנה הסביבה SEC_USER_AGENT.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from datetime import date, timedelta

import pandas as pd
import requests

DEFAULT_UA = os.environ.get("SEC_USER_AGENT", "CompanyStageAnalyzer research-tool contact@example.com")

TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"

# ---------------------------------------------------------------------------
# מיפוי מושגי XBRL. לכל מדד כמה חלופות, כי חברות שונות מדווחות תחת שמות שונים.
# ---------------------------------------------------------------------------
CONCEPTS: dict[str, list[tuple[str, str]]] = {
    "revenue": [
        ("us-gaap", "RevenueFromContractWithCustomerExcludingAssessedTax"),
        ("us-gaap", "Revenues"),
        ("us-gaap", "RevenueFromContractWithCustomerIncludingAssessedTax"),
        ("us-gaap", "RevenuesNetOfInterestExpense"),
        ("us-gaap", "SalesRevenueNet"),
        ("us-gaap", "SalesRevenueGoodsNet"),
        ("us-gaap", "SalesRevenueServicesNet"),
        ("us-gaap", "RevenueNet"),
        ("ifrs-full", "Revenue"),
        ("ifrs-full", "RevenueFromContractsWithCustomers"),
    ],
    "net_income": [
        ("us-gaap", "NetIncomeLoss"),
        ("us-gaap", "NetIncomeLossAvailableToCommonStockholdersBasic"),
        ("us-gaap", "ProfitLoss"),
        ("ifrs-full", "ProfitLossAttributableToOwnersOfParent"),
        ("ifrs-full", "ProfitLoss"),
    ],
    "ocf": [
        ("us-gaap", "NetCashProvidedByUsedInOperatingActivities"),
        ("us-gaap", "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations"),
        ("ifrs-full", "CashFlowsFromUsedInOperatingActivities"),
        ("ifrs-full", "CashFlowsFromUsedInOperations"),
    ],
    "capex": [
        ("us-gaap", "PaymentsToAcquirePropertyPlantAndEquipment"),
        ("us-gaap", "PaymentsToAcquireProductiveAssets"),
        ("us-gaap", "PaymentsForCapitalImprovements"),
        ("ifrs-full", "PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities"),
    ],
    "sbc": [
        ("us-gaap", "ShareBasedCompensation"),
        ("us-gaap", "AllocatedShareBasedCompensationExpense"),
    ],
    "cash": [
        ("us-gaap", "CashAndCashEquivalentsAtCarryingValue"),
        ("us-gaap", "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents"),
        ("us-gaap", "Cash"),
        ("ifrs-full", "CashAndCashEquivalents"),
    ],
    "st_investments": [
        ("us-gaap", "ShortTermInvestments"),
        ("us-gaap", "MarketableSecuritiesCurrent"),
        ("us-gaap", "AvailableForSaleSecuritiesDebtSecuritiesCurrent"),
        ("us-gaap", "AvailableForSaleSecuritiesCurrent"),
        ("ifrs-full", "CurrentInvestments"),
    ],
    # חוב: מנסים קודם סך חוב, אחרת מחברים לטווח ארוך + שוטף
    "debt_total": [
        ("us-gaap", "LongTermDebt"),
        ("us-gaap", "DebtInstrumentCarryingAmount"),
        ("us-gaap", "LongTermDebtAndCapitalLeaseObligationsIncludingCurrentMaturities"),
        ("us-gaap", "DebtLongtermAndShorttermCombinedAmount"),
        ("ifrs-full", "Borrowings"),
    ],
    "debt_noncurrent": [
        ("us-gaap", "LongTermDebtNoncurrent"),
        ("us-gaap", "ConvertibleNotesPayableNoncurrent"),
        ("us-gaap", "ConvertibleDebtNoncurrent"),
        ("us-gaap", "LongTermDebtAndCapitalLeaseObligations"),
        ("us-gaap", "SeniorNotesNoncurrent"),
        ("ifrs-full", "NoncurrentPortionOfNoncurrentBorrowings"),
        ("ifrs-full", "LongtermBorrowings"),
    ],
    "debt_current": [
        ("us-gaap", "LongTermDebtCurrent"),
        ("us-gaap", "DebtCurrent"),
        ("us-gaap", "ConvertibleNotesPayableCurrent"),
        ("ifrs-full", "CurrentPortionOfNoncurrentBorrowings"),
        ("ifrs-full", "CurrentPortionOfLongtermBorrowings"),
        ("ifrs-full", "ShorttermBorrowings"),
    ],
    "shares": [
        ("dei", "EntityCommonStockSharesOutstanding"),
        ("us-gaap", "CommonStockSharesOutstanding"),
    ],
    "shares_diluted_avg": [
        ("us-gaap", "WeightedAverageNumberOfDilutedSharesOutstanding"),
        ("us-gaap", "WeightedAverageNumberOfSharesOutstandingBasic"),
        ("ifrs-full", "AdjustedWeightedAverageShares"),
    ],
}

FLOW_ITEMS = ["revenue", "net_income", "ocf", "capex", "sbc"]
INSTANT_ITEMS = ["cash", "st_investments", "debt_total", "debt_noncurrent", "debt_current", "shares"]


class SecError(Exception):
    pass


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------
def _get_json(url: str, user_agent: str, retries: int = 3) -> dict:
    headers = {"User-Agent": user_agent, "Accept-Encoding": "gzip, deflate"}
    last = None
    for i in range(retries):
        try:
            r = requests.get(url, headers=headers, timeout=30)
            if r.status_code == 404:
                raise SecError("לא נמצאו נתונים ב-SEC עבור החברה (404).")
            if r.status_code == 403:
                raise SecError(
                    "SEC חסמה את הבקשה (403). הגדר User-Agent עם שם ומייל אמיתיים בסרגל הצד."
                )
            r.raise_for_status()
            return r.json()
        except SecError:
            raise
        except Exception as e:  # רשת / קצב בקשות
            last = e
            time.sleep(1.5 * (i + 1))
    raise SecError(f"שגיאה בגישה ל-SEC: {last}")


def load_ticker_map(user_agent: str = DEFAULT_UA) -> dict[str, dict]:
    raw = _get_json(TICKERS_URL, user_agent)
    out = {}
    for row in raw.values():
        out[str(row["ticker"]).upper()] = {"cik": int(row["cik_str"]), "name": row["title"]}
    return out


def fetch_company_facts(cik: int, user_agent: str = DEFAULT_UA) -> dict:
    return _get_json(FACTS_URL.format(cik=cik), user_agent)


# ---------------------------------------------------------------------------
# פירוק companyfacts לסדרות
# ---------------------------------------------------------------------------
def _facts_df(facts: dict, ns: str, concept: str) -> tuple[pd.DataFrame, str | None]:
    """מחזיר DataFrame של כל הדיווחים למושג + יחידת המידה."""
    node = facts.get("facts", {}).get(ns, {}).get(concept)
    if not node:
        return pd.DataFrame(), None
    units = node.get("units", {})
    if not units:
        return pd.DataFrame(), None
    # עדיפות ל-USD / shares, אחרת היחידה עם הכי הרבה תצפיות
    unit = None
    for pref in ("USD", "shares"):
        if pref in units:
            unit = pref
            break
    if unit is None:
        unit = max(units, key=lambda u: len(units[u]))
    df = pd.DataFrame(units[unit])
    if df.empty or "end" not in df:
        return pd.DataFrame(), unit
    df["end"] = pd.to_datetime(df["end"], errors="coerce")
    if "start" in df:
        df["start"] = pd.to_datetime(df["start"], errors="coerce")
    df["filed"] = pd.to_datetime(df.get("filed"), errors="coerce")
    df = df.dropna(subset=["end", "val"])
    return df, unit


def _quarterly_from_duration(df: pd.DataFrame) -> pd.DataFrame:
    """
    בונה סדרה רבעונית ממדד "זרימה" (הכנסות, רווח, תזרים).
    משתמש בדיווחים רבעוניים ישירים, ומשלים רבעונים חסרים מהפרשי YTD
    (למשל רבעון 4 = שנתי פחות 9 חודשים; תזרים מזומנים מדווח לרוב רק מצטבר).
    מחזיר DataFrame עם index=תאריך סוף רבעון ועמודות val, filed.
    """
    if df.empty or "start" not in df:
        return pd.DataFrame(columns=["val", "filed"])
    d = df.dropna(subset=["start"]).copy()
    d["days"] = (d["end"] - d["start"]).dt.days
    d = d[(d["days"] >= 80) & (d["days"] <= 380)]
    # ערך: הדיווח האחרון לכל תקופה (תיקונים / הצגה מחדש). תאריך: הפרסום הראשון (מתי השוק ידע)
    first_filed = d.groupby(["start", "end"])["filed"].min()
    d = d.sort_values("filed").drop_duplicates(subset=["start", "end"], keep="last").copy()
    d["filed"] = [first_filed.loc[(a, b)] for a, b in zip(d["start"], d["end"])]

    quarters: dict[pd.Timestamp, tuple[float, pd.Timestamp]] = {}
    direct = d[(d["days"] >= 80) & (d["days"] <= 100)]
    for _, r in direct.iterrows():
        quarters[r["end"]] = (float(r["val"]), r["filed"])

    # הפרשים בין דיווחים מצטברים עם אותה תחילת שנה
    for start, g in d.groupby("start"):
        g = g.sort_values("end")
        prev = None
        for _, r in g.iterrows():
            if prev is not None:
                gap = (r["end"] - prev["end"]).days
                if 80 <= gap <= 100 and r["end"] not in quarters:
                    quarters[r["end"]] = (float(r["val"]) - float(prev["val"]), r["filed"])
            prev = r

    if not quarters:
        return pd.DataFrame(columns=["val", "filed"])
    out = pd.DataFrame.from_dict(quarters, orient="index", columns=["val", "filed"]).sort_index()
    # איחוד תאריכי סוף קרובים (הפרש של ימים בודדים בין דוחות)
    out = out[~out.index.duplicated(keep="last")]
    return out


def _annual_from_duration(df: pd.DataFrame) -> pd.DataFrame:
    """סדרה שנתית (לחברות זרות שמגישות 20-F/40-F בלבד, בלי דוחות רבעוניים)."""
    if df.empty or "start" not in df:
        return pd.DataFrame(columns=["val", "filed"])
    d = df.dropna(subset=["start"]).copy()
    d["days"] = (d["end"] - d["start"]).dt.days
    d = d[(d["days"] >= 350) & (d["days"] <= 380)]
    if d.empty:
        return pd.DataFrame(columns=["val", "filed"])
    first_filed = d.groupby("end")["filed"].min()
    d = d.sort_values("filed").drop_duplicates(subset=["end"], keep="last").set_index("end").sort_index()
    d["filed"] = first_filed.reindex(d.index)
    return d[["val", "filed"]]


def _series(df: pd.DataFrame, kind: str, sum_classes: bool = False) -> pd.DataFrame:
    if kind == "flow":
        return _quarterly_from_duration(df)
    if kind == "annual":
        return _annual_from_duration(df)
    return _instant_series(df, sum_classes)


def _instant_series(df: pd.DataFrame, sum_classes: bool = False) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["val", "filed"])
    if sum_classes and "accn" in df:
        # מספר מניות בעמוד השער מדווח לכל סוג מניה בנפרד (למשל Class A + Class B) – מחברים
        df = df.groupby(["end", "accn"], as_index=False).agg(val=("val", "sum"), filed=("filed", "max"))
    d = df.sort_values("filed").drop_duplicates(subset=["end"], keep="last")
    d = d.set_index("end")[["val", "filed"]].sort_index()
    return d


def _best_concept(facts: dict, item: str, kind: str):
    """בוחר את המושג עם הנתון העדכני ביותר (ובשוויון – עם הכי הרבה היסטוריה)."""
    best = None
    best_key = None
    for ns, concept in CONCEPTS[item]:
        df, unit = _facts_df(facts, ns, concept)
        if df.empty:
            continue
        s = _series(df, kind, sum_classes=(ns == "dei"))
        if s.empty:
            continue
        key = (s.index.max(), len(s))
        if best_key is None or key > best_key:
            best, best_key = (s, unit, f"{ns}:{concept}"), key
    return best


def _merge_concepts(facts: dict, item: str, kind: str):
    """
    משלב כמה מושגים: המושג העדכני ביותר הוא הבסיס, ומושגים אחרים משלימים
    רבעונים היסטוריים שחסרים בו (חברות מחליפות מושג XBRL לאורך השנים).
    """
    base = _best_concept(facts, item, kind)
    if base is None:
        return None
    series, unit, used = base
    for ns, concept in CONCEPTS[item]:
        name = f"{ns}:{concept}"
        if name == used:
            continue
        df, u = _facts_df(facts, ns, concept)
        if df.empty or u != unit:
            continue
        s = _series(df, kind, sum_classes=(ns == "dei"))
        if s.empty:
            continue
        missing = s.index.difference(series.index)
        missing = missing[missing < series.index.min()]  # רק היסטוריה מוקדמת יותר
        if len(missing):
            series = pd.concat([series, s.loc[missing]]).sort_index()
    return series, unit, used


@dataclass
class CompanyData:
    ticker: str
    name: str
    cik: int
    quarterly: pd.DataFrame          # index=סוף רבעון; עמודות: revenue, net_income, ocf, capex, sbc, filed
    balance: pd.DataFrame            # index=תאריך; עמודות: cash, st_investments, debt, shares
    currency: str = "USD"
    period_months: int = 3           # 3 = רבעוני, 12 = שנתי בלבד (חברות זרות)
    concepts_used: dict = field(default_factory=dict)
    prices: pd.Series | None = None  # מחיר סגירה יומי
    market_cap: float | None = None
    last_price: float | None = None
    warnings: list = field(default_factory=list)


def build_company_data(facts: dict, ticker: str, name: str, cik: int) -> CompanyData:
    warnings: list[str] = []
    used: dict[str, str] = {}
    currency = "USD"

    # רבעוני כברירת מחדל; שנתי אם החברה לא מגישה דוחות רבעוניים (20-F / 40-F)
    flow_kind, period_months = "flow", 3
    q_ni = _merge_concepts(facts, "net_income", "flow")
    a_ni = _merge_concepts(facts, "net_income", "annual")
    if a_ni is not None and (
        q_ni is None or len(q_ni[0]) < 6
        or (a_ni[0].index.max() - q_ni[0].index.max()).days > 200
    ):
        flow_kind, period_months = "annual", 12
        warnings.append(
            "החברה מגישה דוחות שנתיים בלבד (כנראה דוח \u206620-F\u2069 של חברה זרה) – האבחון מבוסס על נתונים שנתיים ופחות מדויק."
        )

    flows = {}
    filed_any = None
    for item in FLOW_ITEMS:
        res = _merge_concepts(facts, item, flow_kind)
        if res is None:
            continue
        s, unit, concept = res
        flows[item] = s["val"]
        used[item] = concept
        if item in ("revenue", "net_income"):
            currency = unit if unit and unit != "shares" else currency
            filed_any = s["filed"] if filed_any is None else filed_any.combine_first(s["filed"])

    if "net_income" not in flows:
        raise SecError("לא נמצא רווח נקי בדוחות ה-SEC של החברה – ייתכן שהיא לא מגישה דוחות XBRL סטנדרטיים.")

    q = pd.DataFrame(flows).sort_index()
    if "revenue" not in q:
        q["revenue"] = 0.0
        warnings.append("לא נמצאו הכנסות מדווחות – החברה מטופלת כחברה ללא הכנסות.")
    if filed_any is not None:
        q["filed"] = filed_any.reindex(q.index)

    inst = {}
    for item in INSTANT_ITEMS:
        res = _merge_concepts(facts, item, "instant")
        if res is None:
            continue
        s, unit, concept = res
        inst[item] = s["val"]
        used[item] = concept
    b = pd.DataFrame(inst).sort_index()

    # חוב: סך חוב אם קיים ועדכני, אחרת לטווח ארוך + שוטף
    if not b.empty:
        parts = [b[c] for c in ("debt_noncurrent", "debt_current") if c in b]
        combined = None
        if parts:
            mask = parts[0].notna()
            total = parts[0].fillna(0)
            for p in parts[1:]:
                mask = mask | p.notna()
                total = total + p.fillna(0)
            combined = total.where(mask)
        if "debt_total" in b and combined is not None:
            b["debt"] = b["debt_total"].combine_first(combined)
            # אם סך החוב "נתקע" בתאריך ישן – העדף את הסכום העדכני
            if b["debt_total"].last_valid_index() is not None and combined.last_valid_index() is not None:
                if combined.last_valid_index() > b["debt_total"].last_valid_index():
                    b["debt"] = combined.combine_first(b["debt_total"])
        elif "debt_total" in b:
            b["debt"] = b["debt_total"]
        elif combined is not None:
            b["debt"] = combined
        else:
            b["debt"] = float("nan")
        if b["debt"].notna().sum() == 0:
            warnings.append("לא אותר חוב פיננסי בדוחות – ייתכן שאין לחברה חוב, או שהוא מדווח תחת שם לא סטנדרטי.")

    # מניות: אם אין מספר מניות עדכני, משתמשים בממוצע המדולל המשוקלל מהדוחות
    last_q = q.index.max()
    shares_ok = (
        not b.empty and "shares" in b and b["shares"].notna().sum() >= 2
        and (last_q - b["shares"].last_valid_index()).days < 200
    )
    if not shares_ok:
        res = _merge_concepts(facts, "shares_diluted_avg", flow_kind)
        if res is not None and (last_q - res[0].index.max()).days < 200:
            b = b.drop(columns=["shares"], errors="ignore").combine_first(pd.DataFrame({"shares": res[0]["val"]}))
            used["shares"] = res[2] + " (ממוצע משוקלל)"

    if currency != "USD":
        warnings.append(f"הדוחות מדווחים ב-{currency}. השוואות לשווי שוק בדולרים עלולות להיות לא מדויקות.")

    return CompanyData(
        ticker=ticker, name=name, cik=cik, quarterly=q, balance=b,
        currency=currency, period_months=period_months, concepts_used=used, warnings=warnings,
    )


# ---------------------------------------------------------------------------
# מחירים
# ---------------------------------------------------------------------------
def fetch_prices(ticker: str) -> tuple[pd.Series | None, float | None, float | None]:
    """מחזיר (מחירי סגירה יומיים, מחיר אחרון, שווי שוק). כל כישלון → None."""
    try:
        import yfinance as yf
    except ImportError:
        return None, None, None
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="max", auto_adjust=True)
        prices = hist["Close"] if not hist.empty else None
        if prices is not None:
            prices.index = pd.to_datetime(prices.index).tz_localize(None)
        last = float(prices.iloc[-1]) if prices is not None and len(prices) else None
        mcap = None
        try:
            fi = t.fast_info
            mcap = float(fi.get("market_cap") or fi.get("marketCap") or 0) or None
        except Exception:
            mcap = None
        return prices, last, mcap
    except Exception:
        return None, None, None


def load_company(ticker: str, user_agent: str = DEFAULT_UA, ticker_map: dict | None = None) -> CompanyData:
    ticker = ticker.strip().upper()
    tmap = ticker_map or load_ticker_map(user_agent)
    # yfinance משתמש ב-BRK-B, SEC ב-BRK-B / BRK.B
    key = ticker if ticker in tmap else ticker.replace(".", "-")
    if key not in tmap:
        raise SecError(
            f"הטיקר {ticker} לא נמצא ברשימת ה-SEC. הכלי תומך בחברות שמגישות דוחות ל-SEC "
            "(נסחרות בארה\"ב). מניות שנסחרות רק בתל אביב אינן נתמכות."
        )
    info = tmap[key]
    facts = fetch_company_facts(info["cik"], user_agent)
    data = build_company_data(facts, ticker, facts.get("entityName") or info["name"], info["cik"])
    prices, last, mcap = fetch_prices(ticker)
    data.prices, data.last_price = prices, last
    if mcap is None and last is not None and "shares" in data.balance and data.balance["shares"].notna().any():
        mcap = last * float(data.balance["shares"].dropna().iloc[-1])
    data.market_cap = mcap
    if prices is None:
        data.warnings.append("לא הצלחתי למשוך מחירים מ-yfinance – מדדי שווי ותשואה לא יוצגו.")
    return data
