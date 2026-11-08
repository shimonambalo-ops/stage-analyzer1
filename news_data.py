"""
עדכונים אחרונים: כותרות חדשות (Yahoo Finance + Google News, כולל בעברית) ודיווחים רשמיים ל-SEC.
מציגים כותרת, מקור, זמן וקישור בלבד – הכתבה עצמה נפתחת באתר המקור.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus

import requests

FORM_HE = {
    "10-K": "דוח שנתי",
    "10-Q": "דוח רבעוני",
    "20-F": "דוח שנתי (חברה זרה)",
    "40-F": "דוח שנתי (חברה זרה)",
    "6-K": "דיווח שוטף (חברה זרה)",
    "8-K": "דיווח מיידי",
    "4": "עסקת בעל עניין",
    "S-1": "תשקיף הנפקה",
    "S-3": "תשקיף מדף (אפשרות לגיוס)",
    "S-3ASR": "תשקיף מדף (אפשרות לגיוס)",
    "424B5": "הנפקה בפועל לפי תשקיף",
    "424B3": "תשקיף משלים",
    "424B4": "הנפקה בפועל לפי תשקיף",
    "SC 13G": "החזקה מהותית של משקיע",
    "SC 13G/A": "עדכון החזקה מהותית",
    "SC 13D": "החזקה מהותית (משקיע אקטיביסטי)",
    "SC 13D/A": "עדכון החזקה (אקטיביסט)",
    "DEF 14A": "זימון אסיפת בעלי מניות",
    "144": "הודעה על מכירת מניות של בעל עניין",
}

ITEM_HE = {
    "1.01": "הסכם מהותי",
    "1.02": "סיום הסכם מהותי",
    "1.05": "אירוע סייבר",
    "2.01": "רכישה או מכירה של נכסים",
    "2.02": "תוצאות כספיות",
    "2.03": "התחייבות פיננסית חדשה",
    "2.05": "עלויות ארגון מחדש",
    "2.06": "ירידת ערך",
    "3.01": "אזהרת מחיקה מהמסחר",
    "3.02": "הנפקת מניות",
    "4.01": "החלפת רואה חשבון",
    "4.02": "תיקון דוחות קודמים",
    "5.02": "שינוי בהנהלה או בדירקטוריון",
    "5.03": "שינוי בתקנון",
    "5.07": "תוצאות הצבעה באסיפה",
    "7.01": "מצגת / הודעה למשקיעים",
    "8.01": "אירוע אחר",
}

INTERESTING = set(FORM_HE) | {"10-K/A", "10-Q/A", "8-K/A"}


def sec_filings(submissions: dict, cik: int, limit: int = 15) -> dict:
    recent = (submissions.get("filings") or {}).get("recent") or {}
    forms = recent.get("form") or []
    dates = recent.get("filingDate") or []
    accns = recent.get("accessionNumber") or []
    docs = recent.get("primaryDocument") or []
    items = recent.get("items") or [""] * len(forms)
    out, insider_90, shelf_365 = [], 0, []
    today = datetime.now(timezone.utc).date()
    for f, d, a, doc, it in zip(forms, dates, accns, docs, items):
        try:
            dd = datetime.strptime(d, "%Y-%m-%d").date()
        except Exception:
            continue
        age = (today - dd).days
        if f in ("4", "4/A") and age <= 90:
            insider_90 += 1
        if f in ("S-3", "S-3ASR", "424B5", "S-1") and age <= 365:
            shelf_365.append({"form": f, "date": d})
        if f not in INTERESTING or f in ("4", "4/A", "144"):
            continue
        if len(out) >= limit:
            continue
        url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{a.replace('-', '')}/{doc}" if doc else \
              f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}"
        item_list = [x.strip() for x in (it or "").split(",") if x.strip()]
        out.append({
            "form": f, "date": d, "url": url,
            "label": FORM_HE.get(f.replace("/A", ""), f) + (" (תיקון)" if f.endswith("/A") else ""),
            "items": [ITEM_HE[x] for x in item_list if x in ITEM_HE],
        })
    return {"filings": out, "insider_trades_90d": insider_90, "shelf_filings_365d": shelf_365}


# ---------------------------------------------------------------------------
# כותרות
# ---------------------------------------------------------------------------
def _iso(dt: datetime | None):
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def yahoo_news(ticker: str, limit: int = 10) -> list[dict]:
    try:
        import yfinance as yf
        raw = yf.Ticker(ticker).news or []
    except Exception:
        return []
    out = []
    for n in raw:
        c = n.get("content") if isinstance(n, dict) else None
        try:
            if c:  # פורמט חדש
                title = c.get("title")
                url = ((c.get("canonicalUrl") or {}).get("url")) or ((c.get("clickThroughUrl") or {}).get("url"))
                src = (c.get("provider") or {}).get("displayName")
                when = c.get("pubDate") or c.get("displayTime")
                dt = datetime.fromisoformat(when.replace("Z", "+00:00")) if when else None
            else:  # פורמט ישן
                title, url, src = n.get("title"), n.get("link"), n.get("publisher")
                ts = n.get("providerPublishTime")
                dt = datetime.fromtimestamp(ts, tz=timezone.utc) if ts else None
            if title and url:
                out.append({"title": title, "url": url, "source": src, "time": _iso(dt), "lang": "en"})
        except Exception:
            continue
    return out[:limit]


def google_news(query: str, lang: str = "en", limit: int = 10) -> list[dict]:
    if lang == "he":
        url = f"https://news.google.com/rss/search?q={quote_plus(query)}&hl=iw&gl=IL&ceid=IL:he"
    else:
        url = f"https://news.google.com/rss/search?q={quote_plus(query)}&hl=en-US&gl=US&ceid=US:en"
    try:
        r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0 (stage-analyzer)"})
        r.raise_for_status()
        root = ET.fromstring(r.content)
    except Exception:
        return []
    out = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = item.findtext("link")
        src_el = item.find("source")
        src = src_el.text if src_el is not None else None
        if src and title.endswith(" - " + src):
            title = title[: -len(" - " + src)]
        try:
            dt = parsedate_to_datetime(item.findtext("pubDate"))
        except Exception:
            dt = None
        if title and link:
            out.append({"title": title, "url": link, "source": src, "time": _iso(dt), "lang": lang})
        if len(out) >= limit:
            break
    return out


def short_company_name(name: str) -> str:
    n = re.sub(r"[,.]?\s+(Inc|Corp|Corporation|Company|Co|Ltd|Limited|Holdings|Group|plc|N\.V|S\.A|AG|SE)\.?$", "", name or "", flags=re.I)
    n = re.sub(r"^The\s+", "", n, flags=re.I)
    return n.strip() or name


def collect_news(ticker: str, company: str, limit: int = 12) -> dict:
    en = yahoo_news(ticker, limit)
    short = short_company_name(company)
    if len(en) < 6:
        en += google_news(f"\"{short}\" {ticker} stock", "en", limit)
    # הסרת כפילויות לפי כותרת
    seen, dedup = set(), []
    for n in en:
        k = re.sub(r"\W+", "", n["title"].lower())[:60]
        if k in seen:
            continue
        seen.add(k)
        dedup.append(n)
    dedup.sort(key=lambda n: n.get("time") or "", reverse=True)
    he = google_news(f"\"{short}\"", "he", 6)
    return {"en": dedup[:limit], "he": he}
