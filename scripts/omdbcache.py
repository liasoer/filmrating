"""Zwischenspeicher für OMDb-Abfragen (cache/omdb.json), damit das Tageslimit von 1000 Abfragen reicht.
Erfolgreiche Antworten gelten 3 Tage, «nicht gefunden» 7 Tage. Bei erreichtem Limit wird nicht weiter abgefragt."""
import json, os, time, urllib.request, urllib.parse

PATH = "cache/omdb.json"
KEY = os.environ.get("OMDB_KEY", "9a64d183")
TTL_OK, TTL_MISS = 3 * 86400, 7 * 86400
_cache = None
_limit = False
stats = {"hit": 0, "call": 0}

def _load():
    global _cache
    if _cache is None:
        try: _cache = json.load(open(PATH, encoding="utf-8"))
        except Exception: _cache = {}
    return _cache

def save():
    if _cache is None: return
    os.makedirs("cache", exist_ok=True)
    now = time.time()
    keep = {k: v for k, v in _cache.items() if now - v.get("ts", 0) < TTL_MISS}
    json.dump(keep, open(PATH, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))

def get(params):
    """params ohne apikey, z.B. {"i": "tt123"} oder {"t": "Titel", "y": "2026", "type": "movie"}"""
    global _limit
    c = _load()
    key = urllib.parse.urlencode(sorted((k, v) for k, v in params.items() if v))
    e = c.get(key)
    if e and time.time() - e["ts"] < (TTL_OK if e["d"] else TTL_MISS):
        stats["hit"] += 1
        return e["d"]
    if _limit: return e["d"] if e else None
    try:
        with urllib.request.urlopen("https://www.omdbapi.com/?" + urllib.parse.urlencode({"apikey": KEY, **{k: v for k, v in params.items() if v}}), timeout=20) as r:
            d = json.load(r)
    except Exception:
        return e["d"] if e else None
    stats["call"] += 1
    if d.get("Response") != "True" and "limit" in (d.get("Error") or "").lower():
        _limit = True
        return e["d"] if e else None
    d = d if d.get("Response") == "True" else None
    c[key] = {"ts": time.time(), "d": d}
    return d
