"""Holt das aktuelle Schweizer Kinoprogramm von cineman.ch und ergänzt IMDb, Rotten Tomatoes und Metacritic via OMDb.
Läuft täglich als GitHub Action und schreibt kino.json. Höfliche Abfragen mit Pausen, nur von robots.txt erlaubte Seiten."""
import json, os, re, time, html, urllib.request, urllib.parse, datetime

OMDB = os.environ.get("OMDB_KEY", "9a64d183")
BASE = "https://www.cineman.ch"
UA = {"User-Agent": "Mozilla/5.0 (compatible; Filmrating/1.0; +https://liasoer.github.io/filmrating/)", "Accept-Language": "de-CH,de;q=0.9"}
MONTHS = {m: i+1 for i, m in enumerate(["januar","februar","märz","april","mai","juni","juli","august","september","oktober","november","dezember"])}
FORMATS = [("IMAX", r"imax"), ("4DX", r"4dx"), ("D-BOX", r"d-?box"), ("Dolby Atmos", r"dolby.?atmos"), ("Dolby Cinema", r"dolby.?cinema"),
           ("ScreenX", r"screen.?x"), ("3D", r"^3d$"), ("VIP & Premium", r"vip|premium|lounge")]

def fetch(url, tries=3):
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
                return r.read().decode("utf-8", "ignore")
        except Exception as e:
            if k == tries - 1: raise
            time.sleep(2 + k * 3)

def clean(s): return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s or ""))).strip()

def listing(path, pages=6):
    out, seen = [], set()
    for p in range(1, pages + 1):
        try: s = fetch(f"{BASE}{path}?page={p}")
        except Exception: break
        items = re.split(r'<div class="teaser-item"', s)[1:]
        new = 0
        for it in items:
            m = re.search(r'href="(/movie/(\d{4})/[^/"]+/)"', it)
            if not m or m.group(1) in seen: continue
            seen.add(m.group(1)); new += 1
            t = re.search(r'<h4 class="teaser-title[^"]*">(.*?)</h4>', it, re.S)
            img = re.search(r'data-src="([^"]+)"', it)
            txt = re.search(r'<p class="teaser-text">(.*?)</p>', it, re.S)
            out.append({"path": m.group(1), "year": m.group(2), "title": clean(t.group(1)) if t else "",
                        "poster": img.group(1).replace("cinemanteaser149x206", "cinemanteaser174x240x2") if img else None,
                        "teaser": clean(txt.group(1)) if txt else ""})
        if not new: break
        time.sleep(0.6)
    return out

def details(m):
    try: s = fetch(BASE + m["path"])
    except Exception: return {}
    d = {}
    d["genres"] = list(dict.fromkeys(clean(g) for g in re.findall(r'class="label label-genre">(.*?)</span>', s)))
    labels = {clean(x).lower() for x in re.findall(r'class="label label-showtime[^"]*">(.*?)</span>', s)}
    d["formats"] = [n for n, rx in FORMATS if any(re.search(rx, l) for l in labels)]
    d["imdb_id"] = (re.search(r'imdb\.com/title/(tt\d+)', s) or [None, None])[1]
    rel = re.search(r'Deutschschweiz:\s*(?:</strong>)?\s*(\d{1,2})\.\s*([A-Za-zäöü]+)\s+(\d{4})', s)
    if rel and rel.group(2).lower() in MONTHS:
        d["release"] = f"{rel.group(3)}-{MONTHS[rel.group(2).lower()]:02d}-{int(rel.group(1)):02d}"
    def people(section):
        blk = re.search(rf'id="linkcollection-{section}"(.*?)<!-- linkcollection-{section} link collection for desktop', s, re.S)
        return [clean(x) for x in re.findall(r'<strong>(.*?)</strong>', blk.group(1))] if blk else []
    d["directors"] = people("regie")[:3]
    d["cast"] = people("darsteller")[:5]
    langs = set(re.findall(r'spoken_modal/\?spoken=([A-Za-z/]+)"', s))
    d["languages"] = sorted({{"D": "Deutsch", "E": "Englisch", "F": "Französisch", "I": "Italienisch", "Dial": "Schweizerdeutsch"}.get(l, l) for l in langs})
    return d

def omdb(m):
    q = {"apikey": OMDB}
    if m.get("imdb_id"): q["i"] = m["imdb_id"]
    else: q.update({"t": m["title"], "y": m["year"], "type": "movie"})
    try:
        with urllib.request.urlopen("https://www.omdbapi.com/?" + urllib.parse.urlencode(q), timeout=20) as r:
            d = json.load(r)
    except Exception: return None
    return d if d.get("Response") == "True" else None

def entry(m, soon=False, new=False):
    det = details(m); time.sleep(0.6)
    e = {"title": m["title"], "slug": m["path"].strip("/").split("/")[-1], "url": BASE + m["path"], "poster": m["poster"],
         "release": det.get("release"), "genres": det.get("genres", []), "directors": det.get("directors", []),
         "cast": det.get("cast", []), "formats": det.get("formats", []), "languages": det.get("languages", []),
         "synopsis": m.get("teaser", ""), "isNew": new, "imdb_id": det.get("imdb_id")}
    d = omdb({**m, **det})
    if d:
        rt = next((r["Value"] for r in d.get("Ratings", []) if r["Source"] == "Rotten Tomatoes"), None)
        e["imdb_id"] = e["imdb_id"] or d.get("imdbID")
        e["ext"] = {"imdb": None if d.get("imdbRating") == "N/A" else d.get("imdbRating"), "rt": rt,
                    "mc": None if d.get("Metascore") == "N/A" else d.get("Metascore"),
                    "genre": d.get("Genre"), "director": d.get("Director"), "runtime": d.get("Runtime")}
        rt_min = re.match(r"(\d+)", d.get("Runtime") or "")
        if rt_min: e["duration"] = int(rt_min.group(1))
        if not e["poster"] and d.get("Poster") not in (None, "N/A"): e["poster"] = d["Poster"]
        if not e["synopsis"] and d.get("Plot") not in (None, "N/A"): e["synopsis"] = d["Plot"]
    return e

try:
    now = listing("/de/filme/jetztimkino/")
except Exception as ex:
    print("Cineman nicht erreichbar:", ex); raise SystemExit(0)
if len(now) < 10:
    print("Zu wenige Filme gefunden, kino.json bleibt unverändert"); raise SystemExit(0)
newp = {m["path"] for m in listing("/de/filme/neuimkino/", 2)}
soon = [m for m in listing("/de/filme/baldimkino/", 2) if m["path"] not in {x["path"] for x in now}]

out = {"updated": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="minutes"), "source": "cineman.ch",
       "now": [], "soon": []}
for i, m in enumerate(now):
    e = entry(m, new=m["path"] in newp); e["order"] = i + 1; out["now"].append(e)
for m in soon[:20]:
    out["soon"].append(entry(m, soon=True))
out["soon"].sort(key=lambda e: e.get("release") or "9999")
with open("kino.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print(len(out["now"]), "im Kino,", len(out["soon"]), "demnächst,", sum(1 for x in out["now"] if x.get("formats")), "mit Formaten")
