"""Aktuelle Serien und neue Staffeln der grossen Streamingdienste (Daten: TVmaze, CC BY-SA) plus IMDb via OMDb.
Schreibt series.json für den Tab «Neu» (Serien)."""
import json, os, re, sys, time, html, datetime, urllib.request, urllib.parse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

OMDB = os.environ.get("OMDB_KEY", "9a64d183")
PLATFORMS = {"Netflix": "Netflix", "Disney+": "Disney+", "Apple TV+": "Apple TV+", "Apple TV": "Apple TV+", "Prime Video": "Prime Video",
             "Amazon Prime Video": "Prime Video", "HBO Max": "HBO Max", "Max": "HBO Max", "HBO": "HBO Max", "Paramount+": "Paramount+",
             "Peacock": "Peacock", "Hulu": "Hulu", "Sky Atlantic": "Sky", "Sky One": "Sky", "WOW": "Sky", "FX": "FX", "FX on Hulu": "Hulu",
             "AMC": "AMC", "AMC+": "AMC", "Showtime": "Paramount+", "Starz": "Starz", "BBC One": "BBC", "BBC iPlayer": "BBC", "Channel 4": "Channel 4"}
TYPES = {"Scripted", "Animation", "Documentary"}
LANGS = {"English", "German"}

def get(url):
    for k in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Filmrating/1.0 (liasoer.github.io/filmrating)"}), timeout=25) as r:
                return json.load(r)
        except Exception:
            time.sleep(2 + 2 * k)
    return []

def clean(s): return html.unescape(re.sub(r"<[^>]+>", "", s or "")).strip()

today = datetime.date.today()
shows = {}
for off in range(-10, 11):
    day = (today + datetime.timedelta(days=off)).isoformat()
    for url in (f"https://api.tvmaze.com/schedule/web?date={day}", f"https://api.tvmaze.com/schedule?country=US&date={day}",
                f"https://api.tvmaze.com/schedule?country=GB&date={day}"):
        for e in get(url) or []:
            s = e.get("show") or (e.get("_embedded") or {}).get("show")
            if not s: continue
            plat = PLATFORMS.get((s.get("webChannel") or {}).get("name") or (s.get("network") or {}).get("name"))
            if not plat or s.get("type") not in TYPES or s.get("language") not in LANGS: continue
            x = shows.setdefault(s["id"], {"s": s, "platform": plat, "eps": []})
            x["eps"].append({"date": e.get("airdate") or (e.get("airstamp") or "")[:10], "season": e.get("season"), "number": e.get("number")})
        time.sleep(0.5)

def omdb(imdb):
    import omdbcache
    return omdbcache.get({"i": imdb})

out = []
for sid, x in shows.items():
    s = x["s"]; eps = sorted(x["eps"], key=lambda e: e["date"])
    if len(eps) > 8 or (eps and (eps[-1].get("season") or 0) > 1900): continue  # Daily Soaps und Shows auslassen
    past = [e for e in eps if e["date"] and e["date"] <= today.isoformat()]
    fut = [e for e in eps if e["date"] and e["date"] > today.isoformat()]
    cur = (past or fut)[-1] if past else fut[0]
    premiere = any(e.get("number") == 1 for e in eps)
    imdb = (s.get("externals") or {}).get("imdb")
    e = {"title": s["name"], "tvmaze_id": sid, "imdb_id": imdb, "platform": x["platform"],
         "poster": (s.get("image") or {}).get("medium"), "poster_l": (s.get("image") or {}).get("original"),
         "genres": s.get("genres") or [], "season": cur.get("season"), "latest": past[-1]["date"] if past else None,
         "next": fut[0]["date"] if fut else None, "premiere": premiere, "isNew": bool(s.get("premiered") and s["premiered"] >= (today - datetime.timedelta(days=45)).isoformat()),
         "summary": clean(s.get("summary"))[:600], "url": f"https://www.justwatch.com/ch/Suche?q={urllib.parse.quote(s['name'])}",
         "ext": {"kind": "series", "tvm": (s.get("rating") or {}).get("average"), "platform": x["platform"]}, "votes": 0}
    if imdb:
        d = omdb(imdb)
        if d:
            e["ext"].update({"imdb": None if d.get("imdbRating") == "N/A" else d.get("imdbRating"),
                             "seasons": None if d.get("totalSeasons") in (None, "N/A") else d.get("totalSeasons"),
                             "genre": d.get("Genre")})
            try: e["votes"] = int((d.get("imdbVotes") or "0").replace(",", ""))
            except ValueError: pass
            if not e["poster"] and d.get("Poster") not in (None, "N/A"): e["poster"] = e["poster_l"] = d["Poster"]
    if e["poster"]: out.append(e)

out.sort(key=lambda e: e["votes"], reverse=True)
res = {"updated": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="minutes"), "source": "TVmaze", "shows": out[:80]}
if len(res["shows"]) >= 5:
    json.dump(res, open("series.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
import omdbcache; omdbcache.save()
print(len(shows), "Serien gefunden,", len(res["shows"]), "gespeichert")
