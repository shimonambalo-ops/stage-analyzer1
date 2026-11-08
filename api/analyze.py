import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (_HERE, os.path.dirname(_HERE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from _handler import make_handler  # noqa: E402
import webapi  # noqa: E402

handler = make_handler(lambda q: webapi.analyze(q.get("t", "")) if q.get("t") else {"error": "חסר טיקר"}, 6 * 3600)
