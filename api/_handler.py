"""בסיס משותף לפונקציות ה-API ב-Vercel (קובץ שמתחיל ב-_ לא הופך לנקודת קצה)."""
import json
import os
import sys
import traceback
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def make_handler(fn, cache_seconds=3600):
    class handler(BaseHTTPRequestHandler):
        def do_GET(self):
            q = {k: v[0] for k, v in parse_qs(urlparse(self.path).query).items()}
            status, cache = 200, f"public, s-maxage={cache_seconds}, stale-while-revalidate=86400"
            try:
                body = fn(q)
                if isinstance(body, dict) and body.get("error"):
                    status, cache = 404, "public, s-maxage=600"
            except Exception as e:  # noqa
                traceback.print_exc()
                body, status, cache = {"error": f"שגיאה בטעינת הנתונים: {e}"}, 502, "no-store"
            raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", cache)
            self.end_headers()
            self.wfile.write(raw)

        def log_message(self, *args):
            pass

    return handler
