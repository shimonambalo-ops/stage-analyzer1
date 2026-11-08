"""
נקודת הכניסה של האתר ב-Vercel: אפליקציית WSGI אחת שמגישה את ה-API ואת קבצי האתר.

  /api/analyze?t=KO   – אבחון שלב, סיכון, סדרות לגרפים
  /api/extras?t=KO    – פרופיל, מועד דוח, נתוני מסחר, חדשות ודיווחים ל-SEC
  /api/tickers        – רשימת טיקרים להשלמה אוטומטית
  כל השאר             – קבצים מתיקיית public/ (ברירת מחדל: index.html)
"""
import json
import mimetypes
import os
import traceback
from urllib.parse import parse_qs

import webapi

ROOT = os.path.dirname(os.path.abspath(__file__))
PUBLIC = os.path.join(ROOT, "public")

TYPES = {".js": "application/javascript", ".css": "text/css", ".html": "text/html", ".svg": "image/svg+xml",
         ".json": "application/json", ".txt": "text/plain"}


def _json(start_response, status, body, cache):
    raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
    start_response(status, [
        ("Content-Type", "application/json; charset=utf-8"),
        ("Cache-Control", cache),
        ("Content-Length", str(len(raw))),
    ])
    return [raw]


def _api(path, q):
    t = (q.get("t") or "").strip()
    if path == "/api/analyze":
        return (webapi.analyze(t) if t else {"error": "חסר טיקר"}), 3600
    if path == "/api/extras":
        return (webapi.extras(t, int(q.get("cik") or 0), q.get("name", "")) if t else {"error": "חסר טיקר"}), 1800
    if path == "/api/audit":
        return (webapi.audit(t) if t else {"error": "חסר טיקר"}), 0
    if path == "/api/tickers":
        return {"tickers": webapi.tickers_list()}, 86400
    return {"error": "נתיב לא קיים"}, 600


def _static(path, start_response):
    rel = os.path.normpath(path.lstrip("/")) if path not in ("", "/") else "index.html"
    full = os.path.join(PUBLIC, rel)
    if rel.startswith("..") or not full.startswith(PUBLIC):
        start_response("403 Forbidden", [("Content-Type", "text/plain")])
        return [b"forbidden"]
    if not os.path.isfile(full):
        if os.path.splitext(rel)[1]:  # קובץ עם סיומת שלא קיים
            start_response("404 Not Found", [("Content-Type", "text/plain")])
            return [b"not found"]
        full = os.path.join(PUBLIC, "index.html")  # ניתוב צד-לקוח
        if not os.path.isfile(full):
            # ב-Vercel קבצי public/ מוגשים מה-CDN ולא תמיד נכללים בפונקציה – מפנים לדף הבית עם הטיקר
            t = rel.strip("/")
            start_response("302 Found", [("Location", f"/?t={t}" if t else "/"), ("Cache-Control", "no-store")])
            return [b""]
    ext = os.path.splitext(full)[1]
    ctype = TYPES.get(ext) or mimetypes.guess_type(full)[0] or "application/octet-stream"
    if ctype.startswith("text/") or ctype in ("application/javascript", "application/json", "image/svg+xml"):
        ctype += "; charset=utf-8"
    with open(full, "rb") as f:
        data = f.read()
    cache = "public, max-age=0, must-revalidate" if ext == ".html" else "public, max-age=300, s-maxage=3600"
    start_response("200 OK", [("Content-Type", ctype), ("Cache-Control", cache), ("Content-Length", str(len(data)))])
    return [data]


def app(environ, start_response):
    path = environ.get("PATH_INFO") or "/"
    if path.startswith("/api/"):
        q = {k: v[0] for k, v in parse_qs(environ.get("QUERY_STRING", "")).items()}
        try:
            body, ttl = _api(path, q)
            if isinstance(body, dict) and body.get("error"):
                return _json(start_response, "404 Not Found", body, "public, s-maxage=600")
            return _json(start_response, "200 OK", body, f"public, s-maxage={ttl}, stale-while-revalidate=600")
        except Exception as e:  # noqa: BLE001
            traceback.print_exc()
            return _json(start_response, "502 Bad Gateway", {"error": f"שגיאה בטעינת הנתונים: {e}"}, "no-store")
    return _static(path, start_response)


if __name__ == "__main__":  # הרצה מקומית: python app.py
    from wsgiref.simple_server import make_server
    print("http://localhost:8000")
    make_server("", 8000, app).serve_forever()
