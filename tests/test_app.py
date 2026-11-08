"""מריץ את ממשק Streamlit מול נתונים סינתטיים (בלי רשת) ובודק שאין חריגות."""
import sys
from pathlib import Path
import numpy as np, pandas as pd
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tests"))
import sec_data
from test_engine import make_facts
from streamlit.testing.v1 import AppTest

n = 20
rev = [100e6 * (1.07 ** i) for i in range(n)]
ni = [-60e6 + 5e6 * i for i in range(n)]
FACTS = make_facts(rev, ni, ni, [2e9] * n, [300e6 * (1.01 ** i) for i in range(n)], debt=[500e6] * n)
idx = pd.bdate_range("2019-01-01", "2024-03-01")
PRICES = pd.Series(np.exp(np.linspace(np.log(5), np.log(80), len(idx))) * (1 + 0.05*np.sin(np.arange(len(idx))/9)), index=idx)

sec_data.load_ticker_map = lambda ua=None: {"TEST": {"cik": 1, "name": "Test Co"}}
sec_data.fetch_company_facts = lambda cik, ua=None: FACTS
sec_data.fetch_prices = lambda t: (PRICES, float(PRICES.iloc[-1]), float(PRICES.iloc[-1]) * 360e6)
import profile_data
from datetime import date, timedelta
profile_data.fetch_sec_profile = lambda cik, ua: {"sic": "SERVICES-PREPACKAGED SOFTWARE", "exchanges": ["Nasdaq"], "fiscal_year_end": "1231",
    "sec_city": "NEW YORK", "sec_state": "NY", "last_report": {"form": "10-Q", "filed": date(2026, 8, 5), "period": date(2026, 6, 30)},
    "next_report_estimate": {"date": date.today() + timedelta(days=9), "period": date(2026, 9, 30), "kind": "רבעוני", "overdue": False}}
profile_data.fetch_yahoo_profile = lambda t: {"summary_en": "Test Co builds things. It sells them worldwide. It was founded in 2015. It is based in New York. Extra sentence.",
    "sector": "Technology", "industry": "Software - Application", "country": "United States", "city": "New York", "employees": 1234, "website": "https://example.com"}
profile_data.translate_he = lambda t: "החברה בונה דברים ומוכרת אותם בכל העולם. היא נוסדה ב-2015 ומטהּ בניו יורק."

at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60)
at.run()
assert not at.exception, at.exception
at.text_input(key="ticker_input").input("TEST").run()
assert not at.exception, at.exception
print([(t.label, t.value) for t in at.text_input]); print([e.value for e in at.error], [i.value for i in at.info])
md = " ".join(x.value for x in at.markdown)
assert "class=\"track\"" in md or "track-wrap" in md, "track missing"; assert "תמונת מצב" in md
print("ok render")
print("errors:", [e.value for e in at.error])
print("✓ app rendered without exceptions")

# טיקר לא קיים
at.text_input(key="ticker_input").input("ZZZZ").run()
assert any("לא נמצא" in e.value for e in at.error)
print("✓ unknown ticker handled")

