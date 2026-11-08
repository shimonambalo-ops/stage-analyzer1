"""בדיקות למנוע השלבים (stage_engine) על נתונים שנתיים סינתטיים."""
import sys
from pathlib import Path
from types import SimpleNamespace

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import stage_engine as E


def company(years, rev0, growth, op_m, ocf_m, capex_m, da_m, cfi_extra=0.0, cff=None, div_m=0.0, bb_m=0.0,
            equity_m=1.0, debt_m=0.3, cash_m=0.2, shares0=1e9, dil=0.0, patterns=None):
    """years שנים; כל הסכומים כשיעור מההכנסות של אותה שנה."""
    idx = pd.DatetimeIndex([pd.Timestamp(2021 + i, 12, 31) for i in range(years)])
    rows, bal = [], []
    rev, sh = rev0, shares0
    for i, t in enumerate(idx):
        g = growth[i] if isinstance(growth, list) else growth
        if i:
            rev *= 1 + g
            sh *= 1 + dil
        ocf = ocf_m * rev
        capex = capex_m * rev
        cfi = -capex + cfi_extra * rev
        div, bb = div_m * rev, bb_m * rev
        f = cff[i] * rev if isinstance(cff, list) else (cff * rev if cff is not None else -(div + bb))
        if patterns:  # כפיית צירוף סימנים לשנה
            p = patterns[i]
            ocf = abs(ocf) * (1 if p[0] == "+" else -1)
            cfi = abs(cfi) * (1 if p[1] == "+" else -1)
            f = abs(f or 0.1 * rev) * (1 if p[2] == "+" else -1)
        rows.append({"revenue": rev, "op_income": op_m * rev, "net_income": op_m * 0.8 * rev, "ocf": ocf,
                     "cfi": cfi, "cff": f, "capex": -capex, "da": da_m * rev, "gross_profit": 0.5 * rev,
                     "tax": 0.2 * op_m * rev, "pretax": op_m * rev, "dividends": -div, "buybacks": -bb,
                     "shares_diluted_avg": sh})
        bal.append({"cash": cash_m * rev, "debt": debt_m * rev, "equity": equity_m * rev, "shares": sh})
    fiscal = pd.DataFrame(rows, index=idx)
    balance = pd.DataFrame(bal, index=idx)
    return SimpleNamespace(fiscal=fiscal, balance=balance)


def test_value_company():
    d = company(4, 40e9, 0.04, op_m=0.28, ocf_m=0.27, capex_m=0.05, da_m=0.05, div_m=0.18, bb_m=0.04)
    r = E.evaluate(d, sic="2080")
    assert r["dickinson"]["stage"] == "mature"
    assert r["stage"] == "value", r["scores"]
    assert [p["pattern"] for p in r["dickinson"]["path"]] == ["+--"] * 4


def test_profitable_growth():
    d = company(4, 30e9, 0.60, op_m=0.55, ocf_m=0.50, capex_m=0.04, da_m=0.02, bb_m=0.12)
    r = E.evaluate(d)
    assert r["stage"] == "profitable", r["scores"]


def test_growth_crwd_like():
    d = company(4, 2e9, 0.30, op_m=-0.01, ocf_m=0.32, capex_m=0.06, da_m=0.035, cff=0.03, dil=0.02, equity_m=0.6)
    r = E.evaluate(d)
    assert r["dickinson"]["stage"] == "growth"
    assert r["stage"] == "growth", r["scores"]


def test_startup():
    d = company(4, 10e6, 0.9, op_m=-4.0, ocf_m=-3.0, capex_m=0.3, da_m=0.05, cff=3.0, dil=0.20, equity_m=8, cash_m=6)
    r = E.evaluate(d, latest={"fcf_ttm": -3.3 * 10e6 * 1.9 ** 3, "liquid": 6 * 10e6 * 1.9 ** 3})
    assert r["stage"] == "startup", r["scores"]
    assert r["risk"]["level"] == "בינוני" or r["risk"]["score"] >= 40
    assert r["metrics"]["runway_months"] is not None


def test_short_runway_is_high_risk():
    d = company(3, 50e6, 0.5, op_m=-2.0, ocf_m=-1.5, capex_m=0.2, da_m=0.05, cff=1.0, dil=0.1, cash_m=1.0)
    r = E.evaluate(d, latest={"fcf_ttm": -1.7 * 50e6 * 2.25, "liquid": 1.0 * 50e6 * 2.25})
    assert r["metrics"]["runway_months"] < 18
    assert r["risk"]["level"] == "גבוה"


def test_financial_not_suitable():
    d = company(4, 40e9, 0.04, op_m=0.3, ocf_m=0.3, capex_m=0.02, da_m=0.02)
    r = E.evaluate(d, sic="6021")
    assert r["suitable"] is False and "פיננסיות" in r["reason"]


def test_majority_and_tie():
    d = company(4, 5e9, 0.15, op_m=0.15, ocf_m=0.2, capex_m=0.15, da_m=0.08,
                patterns=["+-+", "+--", "+--", "+-+"])
    r = E.evaluate(d)
    assert r["dickinson"]["stage"] == "mature" and not r["dickinson"]["tie"]
    d = company(4, 5e9, 0.15, op_m=0.15, ocf_m=0.2, capex_m=0.15, da_m=0.08,
                patterns=["+--", "--+", "+--", "+-+"])
    r = E.evaluate(d)
    # 3 השנים האחרונות: היכרות, בשלות, צמיחה → תיקו → השנה האחרונה
    assert r["dickinson"]["tie"] and r["dickinson"]["stage"] == "growth"


def test_missing_metrics_renormalize():
    d = company(4, 40e9, 0.04, op_m=0.28, ocf_m=0.27, capex_m=0.05, da_m=0.05, div_m=0.18, bb_m=0.04)
    d.fiscal = d.fiscal.drop(columns=["da"])
    d.balance = d.balance.drop(columns=["equity"])
    r = E.evaluate(d)
    assert r["stage"] == "value"
    assert r["coverage"] < 1
    assert next(t for t in r["table"] if t["key"] == "capex")["value"] is None


def test_few_years_low_confidence():
    d = company(2, 40e9, 0.04, op_m=0.28, ocf_m=0.27, capex_m=0.05, da_m=0.05, div_m=0.18, bb_m=0.04)
    r = E.evaluate(d)
    assert r["low_confidence"]


def test_materiality_zero_is_negative():
    # מימון של 1% מתזרים הפעילות → "−" (אין גיוס) → בשלות ולא צמיחה
    d = company(4, 10e9, 0.10, op_m=0.3, ocf_m=0.3, capex_m=0.05, da_m=0.04, cff=0.003)
    r = E.evaluate(d)
    assert r["dickinson"]["path"][-1]["pattern"] == "+--"


def test_contradiction_flag():
    # תזרימים של "טלטלה" (מכירת נכס גדולה בכל שנה) אבל מדדים של חברת ערך
    d = company(4, 40e9, 0.04, op_m=0.28, ocf_m=0.27, capex_m=0.05, da_m=0.05, div_m=0.18, bb_m=0.04,
                cfi_extra=0.2)
    r = E.evaluate(d)
    assert r["dickinson"]["stage"] == "shakeout"
    assert r["contradiction"] is not None
