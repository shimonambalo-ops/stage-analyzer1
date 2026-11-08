"""בדיקות לוגיקה על נתוני companyfacts סינתטיים (בלי רשת)."""
import sys
from pathlib import Path
from datetime import date, timedelta

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import sec_data
import analysis


def fiscal_quarters(start_year, n_years):
    """מחזיר [(שנה, רבעון, start, end)] לשנה קלנדרית."""
    out = []
    for y in range(start_year, start_year + n_years):
        bounds = [(date(y, 1, 1), date(y, 3, 31)), (date(y, 4, 1), date(y, 6, 30)),
                  (date(y, 7, 1), date(y, 9, 30)), (date(y, 10, 1), date(y, 12, 31))]
        for qi, (s, e) in enumerate(bounds, 1):
            out.append((y, qi, s, e))
    return out


def make_facts(rev_q, ni_q, ocf_q, cash, shares, start_year=2019, debt=None, style_ytd_cf=True, op_q=None,
               cfi_q=None, cff_q=None):
    """
    בונה JSON בפורמט companyfacts:
    הכנסות ורווח – דיווח רבעוני ל-Q1-Q3 + שנתי בלבד ל-Q4 (כמו ב-10-K).
    תזרים – YTD בלבד (כמו ב-10-Q אמיתי).
    """
    qs = fiscal_quarters(start_year, len(rev_q) // 4)

    def flow(values, ytd_only=False):
        rows = []
        for (y, qi, s, e), v in zip(qs, values):
            filed = (e + timedelta(days=40)).isoformat()
            ystart = date(y, 1, 1)
            ytd = sum(values[(qs.index((y, qi, s, e)) - (qi - 1)):qs.index((y, qi, s, e)) + 1])
            if qi < 4:
                if not ytd_only or qi == 1:
                    rows.append({"start": s.isoformat(), "end": e.isoformat(), "val": v, "filed": filed, "form": "10-Q"})
                if qi > 1:
                    rows.append({"start": ystart.isoformat(), "end": e.isoformat(), "val": ytd, "filed": filed, "form": "10-Q"})
            else:
                rows.append({"start": ystart.isoformat(), "end": e.isoformat(), "val": ytd,
                             "filed": (e + timedelta(days=60)).isoformat(), "form": "10-K"})
        return rows

    def instant(values):
        return [{"end": e.isoformat(), "val": v, "filed": (e + timedelta(days=40)).isoformat(), "form": "10-Q"}
                for (y, qi, s, e), v in zip(qs, values)]

    gaap = {
        "Revenues": {"units": {"USD": flow(rev_q)}},
        "NetIncomeLoss": {"units": {"USD": flow(ni_q)}},
        "NetCashProvidedByUsedInOperatingActivities": {"units": {"USD": flow(ocf_q, ytd_only=style_ytd_cf)}},
        "CashAndCashEquivalentsAtCarryingValue": {"units": {"USD": instant(cash)}},
    }
    if cfi_q is not None:
        gaap["NetCashProvidedByUsedInInvestingActivities"] = {"units": {"USD": flow(cfi_q, ytd_only=style_ytd_cf)}}
    if cff_q is not None:
        gaap["NetCashProvidedByUsedInFinancingActivities"] = {"units": {"USD": flow(cff_q, ytd_only=style_ytd_cf)}}
    if op_q is not None:
        gaap["OperatingIncomeLoss"] = {"units": {"USD": flow(op_q)}}
    if debt is not None:
        gaap["LongTermDebt"] = {"units": {"USD": instant(debt)}}
    return {
        "entityName": "Test Co",
        "facts": {"us-gaap": gaap, "dei": {"EntityCommonStockSharesOutstanding": {"units": {"shares": instant(shares)}}}},
    }


def run(facts):
    d = sec_data.build_company_data(facts, "TEST", "Test Co", 1)
    return d, analysis.diagnose(d)


def test_quarter_reconstruction():
    rev = [10e6 * (1.1 ** i) for i in range(16)]
    ni = [-5e6] * 16
    ocf = [-3e6 - i * 1e5 for i in range(16)]
    f = make_facts(rev, ni, ocf, [500e6] * 16, [100e6] * 16)
    d = sec_data.build_company_data(f, "T", "T", 1)
    assert len(d.quarterly) == 16, len(d.quarterly)
    assert np.allclose(d.quarterly["revenue"].values, rev), "Q4 must be derived from annual minus 9M"
    assert np.allclose(d.quarterly["ocf"].values, ocf), "cash flow quarters must be derived from YTD"
    print("✓ quarter reconstruction (Q4 from 10-K, cash flow from YTD)")


def _stage(ocf, cfi, cff, n=12, rev=None, ni=None):
    rev = rev or [200e6] * n
    ni = ni or [10e6] * n
    f = make_facts(rev, ni, [ocf] * n, [1e9] * n, [100e6] * n, cfi_q=[cfi] * n, cff_q=[cff] * n)
    d = sec_data.build_company_data(f, "T", "T", 1)
    return analysis.diagnose(d)


def test_dickinson_patterns():
    """8 הצירופים של Dickinson (2011) → 5 שלבים."""
    cases = {
        (-1, -1, +1): "introduction", (+1, -1, +1): "growth", (+1, -1, -1): "mature",
        (-1, -1, -1): "shakeout", (+1, +1, +1): "shakeout", (+1, +1, -1): "shakeout",
        (-1, +1, +1): "decline", (-1, +1, -1): "decline",
    }
    for (o, i, f), want in cases.items():
        dg = _stage(o * 30e6, i * 20e6, f * 10e6)
        assert dg.stage == want, ((o, i, f), dg.stage)
        assert dg.latest["pattern"] == "".join("+" if x > 0 else "-" for x in (o, i, f))
    print("✓ all 8 Dickinson cash-flow patterns map to the right stage")


def test_materiality():
    """תזרים השקעות ומימון זניחים (כמו Palantir) לא הופכים חברה ל'התנערות'."""
    dg = _stage(4000e6, 20e6, 9e6)  # + + + גולמי, אבל השניים האחרונים זניחים
    assert dg.stage == "mature", dg.stage
    assert set(dg.latest["near_zero"]) == {"cfi_ttm", "cff_ttm"}
    dg = _stage(4000e6, 900e6, -500e6)  # מכירת נכסים מהותית – נשאר התנערות
    assert dg.stage == "shakeout", dg.stage
    print("✓ materiality: near-zero investing/financing flows treated as no activity")


def test_damodaran_lens():
    n = 12
    # הכנסות זניחות → סטארטאפ
    dg = _stage(-30e6, -20e6, 60e6, rev=[1e6] * n, ni=[-40e6] * n)
    assert dg.damodaran == "startup", dg.damodaran
    # צמיחה מהירה + רווח → צמיחה גבוהה
    dg = _stage(50e6, -30e6, 10e6, rev=[100e6 * 1.08 ** i for i in range(n)], ni=[20e6] * n)
    assert dg.damodaran == "high_growth", dg.damodaran
    # צמיחה איטית + רווח → בשלות יציבה
    dg = _stage(50e6, -30e6, -10e6, rev=[100e6 * 1.005 ** i for i in range(n)], ni=[20e6] * n)
    assert dg.damodaran == "mature_stable", dg.damodaran
    # הכנסות יורדות → דעיכה
    dg = _stage(50e6, -30e6, -10e6, rev=[100e6 * 0.97 ** i for i in range(n)], ni=[20e6] * n)
    assert dg.damodaran == "decline", dg.damodaran
    print("✓ Damodaran lens: startup / high growth / mature stable / decline")


def test_securities_trading_neutralized():
    """מכירת ניירות ערך (ניהול קופה) לא הופכת חברה בשלה ל'התנערות'."""
    n = 12
    f = make_facts([200e6] * n, [10e6] * n, [30e6] * n, [1e9] * n, [100e6] * n,
                   cfi_q=[40e6] * n, cff_q=[-10e6] * n)  # תזרים השקעות חיובי בגלל מכירת ני"ע
    gaap = f["facts"]["us-gaap"]
    gaap["MarketableSecuritiesCurrent"] = {"units": {"USD": [
        {"end": e, "val": 2e9 - 0.06e9 * k, "filed": e, "form": "10-Q", "accn": f"a{k}"}
        for k, e in enumerate(r["end"] for r in gaap["CashAndCashEquivalentsAtCarryingValue"]["units"]["USD"])]}}
    d = sec_data.build_company_data(f, "T", "T", 1)
    dg = analysis.diagnose(d)
    assert dg.latest["cfi_raw_ttm"] > 0 and dg.latest["cfi_ttm"] < 0, (dg.latest["cfi_raw_ttm"], dg.latest["cfi_ttm"])
    assert dg.stage == "mature", dg.stage
    print("✓ securities sales neutralized in investing cash flow (stays 'mature')")


def test_edge_signal():
    """תזרים מפעילות שלילי שמתקרב לאפס → על הסף למעבר מהיכרות לצמיחה."""
    n = 12
    ocf = [-60e6 + 5e6 * i for i in range(n)]
    f = make_facts([200e6] * n, [-10e6] * n, ocf, [1e9] * n, [100e6] * n, cfi_q=[-20e6] * n, cff_q=[30e6] * n)
    d = sec_data.build_company_data(f, "T", "T", 1)
    dg = analysis.diagnose(d)
    assert dg.stage == "introduction", dg.stage
    edges = analysis.edge_signals(dg)
    assert any(e["to"] == "growth" for e in edges), edges
    print("✓ edge signal: operating cash flow approaching zero → growth")


def test_inflection_and_events():
    n = 20
    rev = [100e6 * (1.07 ** i) for i in range(n)]
    ni = [-60e6 + 5e6 * i for i in range(n)]
    f = make_facts(rev, ni, ni, [2e9] * n, [300e6] * n, cfi_q=[-20e6] * n, cff_q=[10e6] * n)
    d = sec_data.build_company_data(f, "T", "T", 1)
    idx = pd.bdate_range("2019-01-01", "2024-03-01")
    d.prices = pd.Series(np.linspace(10, 100, len(idx)), index=idx)
    dg = analysis.diagnose(d)
    assert len(dg.events) == 1, dg.events
    assert dg.events.iloc[0]["return_since"] > 0
    print(f"✓ profit-transition event detected at {dg.events.iloc[0]['quarter_end'].date()}")


def test_runway_and_dilution():
    n = 16
    f = make_facts([200e6] * n, [-40e6] * n, [-40e6] * n, [300e6 - 15e6 * i for i in range(n)],
                   [100e6 * (1.06 ** i) for i in range(n)], debt=[400e6] * n, cfi_q=[-5e6] * n, cff_q=[20e6] * n)
    d = sec_data.build_company_data(f, "T", "T", 1)
    dg = analysis.diagnose(d)
    assert dg.stage == "introduction"
    assert dg.latest["dilution_yoy"] > 0.2
    assert dg.risk_score >= 60, dg.risk_score
    print(f"✓ runway + dilution → risk {dg.risk_score} ({dg.risk_level})")


def test_non_operating_profit_is_not_inflection():
    """סטארטאפ שהרווח הנקי שלו חיובי רק משערוך כתבי אופציה – לא 'מעבר לרווח'."""
    n = 16
    ni = [-50e6] * 6 + [80e6] * 4 + [-60e6] * 6      # רווח חשבונאי זמני
    op = [-55e6] * n                                  # הפעילות מפסידה כל הזמן
    f = make_facts([0] * n, ni, [-50e6] * n, [1e9] * n, [100e6] * n, op_q=op)
    d = sec_data.build_company_data(f, "T", "T", 1)
    idx = pd.bdate_range("2019-01-01", "2023-03-01")
    d.prices = pd.Series(np.linspace(10, 20, len(idx)), index=idx)
    dg = analysis.diagnose(d)
    assert len(dg.events) == 0, dg.events
    assert set(dg.history.values) <= {"startup", "unknown"}, set(dg.history.values)
    print("✓ non-operating profit ignored (no false 'profit' event)")


def test_spac_shell_filings_are_dropped_and_securities_counted():
    """חברה שנכנסה דרך SPAC: דוחות המעטפת (עם נכסים בנאמנות) לא נכנסים, וניירות ערך לא שוטפים נספרים בקופה."""
    n = 16
    f = make_facts([0] * n, [-30e6] * n, [-25e6] * n, [100e6] * n, [100e6] * n, start_year=2021)
    gaap = f["facts"]["us-gaap"]
    # המעטפת: נכסים בנאמנות, רווח מריבית על הנאמנות, בדוחות שהוגשו עד 05/2022
    gaap["AssetsHeldInTrustNoncurrent"] = {"units": {"USD": [
        {"end": "2021-12-31", "val": 500e6, "filed": "2022-03-01", "form": "10-K", "accn": "s1"},
        {"end": "2022-03-31", "val": 501e6, "filed": "2022-05-12", "form": "10-Q", "accn": "s2"}]}}
    for row in gaap["NetIncomeLoss"]["units"]["USD"]:
        if row["filed"] <= "2022-05-12":
            row["val"] = abs(row["val"])  # "רווח" מריבית על הנאמנות
    gaap["DebtSecuritiesAvailableForSaleExcludingAccruedInterest"] = {"units": {"USD": [
        {"end": "2024-12-31", "val": 700e6, "filed": "2025-02-10", "form": "10-K", "accn": "x"}]}}
    d = sec_data.build_company_data(f, "T", "T", 1)
    assert d.spac_cutoff == pd.Timestamp("2022-05-12")
    assert d.quarterly.index.min() > pd.Timestamp("2022-03-31"), d.quarterly.index.min()
    dg = analysis.diagnose(d)
    assert len(dg.events) == 0
    assert dg.latest["liquid"] >= 800e6, dg.latest["liquid"]  # 100M מזומן + 700M ניירות ערך
    print(f"✓ SPAC shell filings dropped (cutoff {d.spac_cutoff.date()}), securities counted in cash")


if __name__ == "__main__":
    test_quarter_reconstruction()
    test_dickinson_patterns()
    test_materiality()
    test_damodaran_lens()
    test_securities_trading_neutralized()
    test_edge_signal()
    test_inflection_and_events()
    test_runway_and_dilution()
    test_non_operating_profit_is_not_inflection()
    test_spac_shell_filings_are_dropped_and_securities_counted()
    print("\nכל הבדיקות עברו")
