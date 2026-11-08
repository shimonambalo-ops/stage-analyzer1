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


def make_facts(rev_q, ni_q, ocf_q, cash, shares, start_year=2019, debt=None, style_ytd_cf=True, op_q=None):
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


def test_startup():
    n = 12
    f = make_facts([0] * n, [-100e6] * n, [-95e6] * n, [900e6 - 50e6 * i for i in range(n)], [400e6 + 5e6 * i for i in range(n)])
    d, dg = run(f)
    assert dg.stage == "startup", dg.stage
    assert dg.runway["months_fcf"] is not None
    print(f"✓ startup → {dg.stage_he}, runway {dg.runway['months_fcf']:.0f}m, risk {dg.risk_score} ({dg.risk_level})")


def test_startup_to_growth():
    n = 16
    rev = [0] * 8 + [5e6, 15e6, 30e6, 50e6, 80e6, 120e6, 170e6, 230e6]
    f = make_facts(rev, [-60e6] * n, [-50e6] * n, [1e9] * n, [100e6] * n)
    d, dg = run(f)
    assert dg.stage == "startup_to_growth", dg.stage
    print(f"✓ startup→growth → {dg.stage_he}, risk {dg.risk_score}")


def test_growth_loss_approaching():
    n = 20
    rev = [100e6 * (1.07 ** i) for i in range(n)]
    ni = [-120e6 + 5e6 * i for i in range(n)]  # מצטמצם, עדיין שלילי
    f = make_facts(rev, ni, [x * 0.8 for x in ni], [2e9] * n, [300e6] * n)
    d, dg = run(f)
    assert dg.stage == "growth_loss", dg.stage
    assert dg.breakeven["trend"] == "narrowing"
    print(f"✓ growth_loss → {dg.stage_he}, breakeven in {dg.breakeven['quarters']}q, approaching={dg.approaching_profit}")


def test_inflection_and_events():
    n = 20
    rev = [100e6 * (1.07 ** i) for i in range(n)]
    ni = [-60e6 + 5e6 * i for i in range(n)]  # הופך חיובי באמצע
    f = make_facts(rev, ni, ni, [2e9] * n, [300e6] * n)
    d = sec_data.build_company_data(f, "T", "T", 1)
    idx = pd.bdate_range("2019-01-01", "2024-03-01")
    d.prices = pd.Series(np.linspace(10, 100, len(idx)), index=idx)
    dg = analysis.diagnose(d)
    hist = dg.history
    assert "inflection" in set(hist.values), set(hist.values)
    assert len(dg.events) == 1, dg.events
    ev = dg.events.iloc[0]
    assert ev["return_since"] > 0
    print(f"✓ inflection detected at {ev['quarter_end'].date()} (event {ev['event_date'].date()}), "
          f"return since {ev['return_since']:.0%}; current stage {dg.stage_he}")


def test_value():
    n = 20
    rev = [1e9 * (1.01 ** i) for i in range(n)]
    f = make_facts(rev, [150e6] * n, [200e6] * n, [3e9] * n, [500e6 - 1e6 * i for i in range(n)], debt=[1e9] * n)
    d, dg = run(f)
    assert dg.stage == "value", dg.stage
    assert dg.runway["self_funded"]
    print(f"✓ value → {dg.stage_he}, risk {dg.risk_score} ({dg.risk_level})")


def test_loss_slow_and_dilution():
    n = 16
    rev = [200e6 * (1.005 ** i) for i in range(n)]
    f = make_facts(rev, [-40e6] * n, [-40e6] * n, [300e6 - 15e6 * i for i in range(n)],
                   [100e6 * (1.06 ** i) for i in range(n)], debt=[400e6] * n)
    d, dg = run(f)
    assert dg.stage == "loss_slow", dg.stage
    assert dg.latest["dilution_yoy"] > 0.2
    assert dg.risk_score >= 60, dg.risk_score
    print(f"✓ loss_slow → {dg.stage_he}, risk {dg.risk_score} ({dg.risk_level})")
    for pts, r in dg.risk_reasons:
        print(f"    +{pts}: {r}")


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
    test_startup()
    test_startup_to_growth()
    test_growth_loss_approaching()
    test_inflection_and_events()
    test_value()
    test_loss_slow_and_dilution()
    test_non_operating_profit_is_not_inflection()
    test_spac_shell_filings_are_dropped_and_securities_counted()
    print("\nכל הבדיקות עברו")


def test_proxy_statement_does_not_override_annual_report():
    """DEF 14A (טבלת שכר מול ביצועים) מתייג רווח נקי מאוחד – לא אמור לדרוס את הרווח מה-10-K (טסלה, Q4 2025)."""
    n = 16
    rev = [1e9] * n
    ni = [100e6] * n
    f = make_facts(rev, ni, ni, [1e9] * n, [100e6] * n)
    rows = f["facts"]["us-gaap"]["NetIncomeLoss"]["units"]["USD"]
    fy = [r for r in rows if r["form"] == "10-K"][-1]
    rows.append({**fy, "val": fy["val"] + 61e6, "filed": "2030-01-01", "form": "DEF 14A"})
    d = sec_data.build_company_data(f, "T", "T", 1)
    assert abs(d.quarterly["net_income"].iloc[-1] - 100e6) < 1, d.quarterly["net_income"].tail(2)


def test_dilution_uses_average_diluted_shares():
    """מניות חסומות שהונפקו למנכ"ל מנפחות את עמוד השער; הדילול נמדד לפי הממוצע המדולל."""
    n = 16
    f = make_facts([1e9] * n, [100e6] * n, [100e6] * n, [1e9] * n,
                   [3.2e9] * (n - 4) + [3.95e9] * 4)  # קפיצה של 23% בעמוד השער
    qs = fiscal_quarters(2019, n // 4)
    avg = [3.50e9 + 5e6 * i for i in range(n)]
    f["facts"]["us-gaap"]["WeightedAverageNumberOfDilutedSharesOutstanding"] = {"units": {"shares": [
        {"start": s.isoformat(), "end": e.isoformat(), "val": v, "filed": (e + timedelta(days=40)).isoformat(), "form": "10-Q"}
        for (y, qi, s, e), v in zip(qs, avg) if qi < 4]}}
    d, dg = run(f)
    L = dg.latest
    assert L["dilution_basis"] == "avg", L
    assert abs(L["dilution_yoy"]) < 0.02, L["dilution_yoy"]
    assert L["cover_shares_yoy"] > 0.2


def test_split_adjusts_share_history():
    s = pd.Series([1.0e9, 1.01e9, 1.02e9, 3.07e9, 3.08e9],
                  index=pd.to_datetime(["2022-03-31", "2022-06-30", "2022-09-30", "2022-12-31", "2023-03-31"]))
    a = analysis._split_adjusted(s)
    assert abs(a.iloc[0] - 3.0e9) < 1e6 and abs(a.iloc[-1] - 3.08e9) < 1
    # הנפקה של 50% אינה פיצול
    s2 = pd.Series([1.0e9, 1.5e9], index=pd.to_datetime(["2022-03-31", "2022-06-30"]))
    assert analysis._split_adjusted(s2).iloc[0] == 1.0e9


def test_securities_total_that_includes_cash_is_not_double_counted():
    """טסלה: AvailableForSaleSecuritiesDebtSecurities = מזומן + השקעות קצרות – לא להוסיף שוב את המזומן."""
    n = 8
    f = make_facts([1e9] * n, [1e8] * n, [1e8] * n, [18e9] * n, [3e9] * n)
    qs = fiscal_quarters(2019, n // 4)
    inst = lambda vals: [{"end": e.isoformat(), "val": v, "filed": (e + timedelta(days=40)).isoformat(), "form": "10-Q"}
                         for (y, qi, a, e), v in zip(qs, vals)]
    f["facts"]["us-gaap"]["ShortTermInvestments"] = {"units": {"USD": inst([23e9] * n)}}
    f["facts"]["us-gaap"]["AvailableForSaleSecuritiesDebtSecurities"] = {"units": {"USD": inst([41e9] * n)}}
    d, dg = run(f)
    assert abs(dg.latest["liquid"] - 41e9) < 1e6, dg.latest["liquid"]
