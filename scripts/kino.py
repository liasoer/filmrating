"""Holt das aktuelle Kinoprogramm (Pathé Schweiz) und ergänzt IMDb, Rotten Tomatoes und Metacritic via OMDb.
Läuft täglich als GitHub Action und schreibt kino.json."""
import json, os, re, urllib.request, urllib.parse, datetime

OMDB = os.environ.get("OMDB_KEY", "9a64d183")
UA = {"User-Agent": "Mozilla/5.0 (Filmrating kino.json)"}

def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        return json.load(r)

def omdb(title, year):
    tries = [(title, year), (title, None), (re.sub(r"\s*[-:–].*$", "", title), year)]
    for t, y in tries:
        if not t: continue
        q = {"apikey": OMDB, "t": t, "type": "movie"}
        if y: q["y"] = y
        try:
            d = get("https://www.omdbapi.com/?" + urllib.parse.urlencode(q))
        except Exception:
            continue
        if d.get("Response") == "True":
            return d
    return None

def entry(s):
    rel = (s.get("releaseAt") or {}).get("CH_DE") or (s.get("releaseAt") or {}).get("CH_FR")
    year = (rel or "")[:4] or None
    e = {
        "title": s["title"], "slug": s["slug"], "release": rel,
        "poster": (s.get("posterPath") or {}).get("md"),
        "duration": s.get("duration"), "genres": [g for g in (s.get("genres") or []) if g != "Fiction"],
        "directors": s.get("directors") or [], "cast": (s.get("hubbleCasting") or "").split(", ")[:4],
        "age": ((s.get("contentRating") or {}).get("ref") or ""),
        "url": f"https://www.pathe.ch/de/filme/{s['slug']}",
    }
    d = omdb(s["title"], year)
    if d:
        rt = next((r["Value"] for r in d.get("Ratings", []) if r["Source"] == "Rotten Tomatoes"), None)
        e["imdb_id"] = d.get("imdbID")
        e["ext"] = {"imdb": None if d.get("imdbRating") == "N/A" else d.get("imdbRating"), "rt": rt,
                    "mc": None if d.get("Metascore") == "N/A" else d.get("Metascore"),
                    "genre": d.get("Genre"), "director": d.get("Director"), "runtime": d.get("Runtime")}
        if not e["poster"] and d.get("Poster") not in (None, "N/A"):
            e["poster"] = d["Poster"]
    return e

shows = get("https://www.pathe.ch/api/shows?language=de")["shows"]
now = [s for s in shows if s.get("isMovie") and not s.get("isComingSoon") and (s.get("next24ShowtimesCount") or 0) > 0]
now.sort(key=lambda s: s.get("homeOrder") or 999)
soon = [s for s in shows if s.get("isMovie") and s.get("isComingSoon")]
soon.sort(key=lambda s: ((s.get("releaseAt") or {}).get("CH_DE") or "9999", s.get("upcomingOrder") or 999))

out = {
    "updated": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="minutes"),
    "source": "Pathé Schweiz",
    "now": [entry(s) for s in now[:40]],
    "soon": [entry(s) for s in soon[:15]],
}
with open("kino.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print(len(out["now"]), "im Kino,", len(out["soon"]), "demnächst,", sum(1 for x in out["now"] if x.get("imdb_id")), "mit IMDb")
