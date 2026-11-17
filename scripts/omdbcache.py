"""Zwischenspeicher für OMDb-Abfragen (cache/omdb.json), damit das Tageslimit von 1000 Abfragen reicht.
Gefundene Filme bleiben dauerhaft gespeichert (Poster, IMDb-Nummer usw.), nur die Wertungen werden einmal pro Woche aufgefrischt.
«Nicht gefunden» gilt 7 Tage. Bei erreichtem Limit wird nicht weiter abgefragt und der gespeicherte Stand verwendet."""
import json, os, time, urllib.request, urllib.parse

PATH = "cache/omdb.json"
KEY = os.environ.get("OMDB_KEY", "9a64d183")
TTL_OK, TTL_MISS = 7 * 86400, 7 * 86400
FIELDS = ("Title", "Year", "imdbID", "Type", "Poster", "imdbRating", "imdbVotes", "Metascore", "Ratings", "Genre", "Director", "Runtime", "totalSeasons", "Plot", "Response")
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
    # Gefundene Einträge nie löschen, nur «nicht gefunden» nach 7 Tagen
    keep = {k: v for k, v in _cache.items() if v.get("d") or now - v.get("ts", 0) < TTL_MISS}
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
    if d.get("Response") == "True":
        d = {k: d[k] for k in FIELDS if k in d}
    elif e and e.get("d"):
        return e["d"]  # vorher gefunden: alten Stand behalten
    else:
        d = None
    c[key] = {"ts": time.time(), "d": d}
    return d
