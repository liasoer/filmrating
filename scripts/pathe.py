"""Baut kino.json aus Pathé-Daten, die der iPhone-Kurzbefehl täglich nach pathe/raw.txt hochlädt.
Format von raw.txt: Blöcke '<<<URL>>> https://...' gefolgt vom JSON-Text der Seite, getrennt durch '<<<END>>>'.
Schreibt ausserdem pathe/urls.txt: die Adressen, die der Kurzbefehl am nächsten Morgen holen soll."""
import json, os, re, subprocess, time, urllib.request, urllib.parse, datetime

OMDB = os.environ.get("OMDB_KEY", "9a64d183")
SHOWS = "https://www.pathe.ch/api/shows?language=de"
DETAIL = "https://www.pathe.ch/api/show/{}?language=de"
FORMATS = [("IMAX", {"imax", "imaxvip"}), ("4DX", {"4dx"}), ("D-BOX", {"dbox"}), ("Dolby Atmos", {"atmos"}),
           ("ScreenX", {"screenx"}), ("3D", {"3d"}), ("VIP & Premium", {"vip", "vipbed", "viplounge", "premium", "premium-seats", "imaxvip"}),
           ("Kinderkino", {"kidscinema"})]
LANGS = {"allemand": "Deutsch", "anglais": "Englisch", "français": "Französisch", "italien": "Italienisch", "espagnol": "Spanisch",
         "japonais": "Japanisch", "coréen": "Koreanisch", "hindi": "Hindi", "russe": "Russisch", "albanais": "Albanisch", "suisse allemand": "Schweizerdeutsch"}

def read_raw(path="pathe/raw.txt"):
    if not os.path.exists(path): return {}
    txt = open(path, encoding="utf-8", errors="ignore").read()
    out = {}
    for block in txt.split("<<<END>>>"):
        m = re.search(r"<<<URL>>>\s*(\S+)\s*\n?(.*)", block, re.S)
        if not m: continue
        try: out[m.group(1).strip()] = json.loads(m.group(2).strip())
        except Exception: pass
    return out

def raw_age_hours(path="pathe/raw.txt"):
    """Alter der letzten iPhone-Lieferung, über die öffentliche GitHub-API (funktioniert auch bei flachem Checkout)."""
    try:
        url = "https://api.github.com/repos/liasoer/filmrating/commits?" + urllib.parse.urlencode({"path": path, "per_page": 1})
        with urllib.request.urlopen(urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"}), timeout=20) as r:
            d = json.load(r)[0]["commit"]["committer"]["date"]
        ts = datetime.datetime.fromisoformat(d.replace("Z", "+00:00")).timestamp()
        return (time.time() - ts) / 3600
    except Exception:
        return 1e9 if not os.path.exists(path) else (time.time() - os.path.getmtime(path)) / 3600

def omdb(title, year, imdb=None):
    tries = [{"i": imdb}] if imdb else []
    tries += [{"t": title, "y": year, "type": "movie"}, {"t": title, "type": "movie"}, {"t": re.sub(r"\s*[-:–].*$", "", title), "y": year, "type": "movie"}]
    for q in tries:
        if not any(v for k, v in q.items() if k in ("i", "t")): continue
        try:
            with urllib.request.urlopen("https://www.omdbapi.com/?" + urllib.parse.urlencode({"apikey": OMDB, **{k: v for k, v in q.items() if v}}), timeout=20) as r:
                d = json.load(r)
            if d.get("Response") == "True": return d
        except Exception: pass
    return None

def entry(s, det):
    tags = {t.lower() for t in (det.get("tags") or [])}
    rel = (s.get("releaseAt") or {}).get("CH_DE") or (s.get("releaseAt") or {}).get("CH_FR")
    e = {"title": s["title"], "slug": s["slug"], "release": rel, "poster": (s.get("posterPath") or {}).get("lg") or (s.get("posterPath") or {}).get("md"),
         "backdrop": (s.get("backgroundPath") or {}).get("lg"), "duration": s.get("duration"),
         "genres": [g for g in (s.get("genres") or []) if g != "Fiction"], "directors": s.get("directors") or [],
         "cast": [c for c in (s.get("hubbleCasting") or "").split(", ") if c][:5], "age": ((s.get("contentRating") or {}).get("ref") or ""),
         "url": f"https://www.pathe.ch/de/films/{s['slug']}", "isNew": bool(s.get("isNew")), "order": s.get("homeOrder"),
         "formats": [n for n, keys in FORMATS if tags & keys], "languages": [LANGS[t] for t in sorted(tags) if t in LANGS],
         "synopsis": re.sub(r"<[^>]+>", "", det.get("synopsis") or "").strip()[:600]}
    d = omdb(s["title"], (rel or "")[:4] or None)
    if d:
        rt = next((r["Value"] for r in d.get("Ratings", []) if r["Source"] == "Rotten Tomatoes"), None)
        e["imdb_id"] = d.get("imdbID")
        e["ext"] = {"imdb": None if d.get("imdbRating") == "N/A" else d.get("imdbRating"), "rt": rt,
                    "mc": None if d.get("Metascore") == "N/A" else d.get("Metascore"),
                    "genre": d.get("Genre"), "director": d.get("Director"), "runtime": d.get("Runtime")}
    return e

def build():
    raw = read_raw()
    shows = (raw.get(SHOWS) or {}).get("shows")
    if not shows: return None
    now = sorted([s for s in shows if s.get("isMovie") and not s.get("isComingSoon") and (s.get("next24ShowtimesCount") or 0) > 0], key=lambda s: s.get("homeOrder") or 999)[:40]
    soon = sorted([s for s in shows if s.get("isMovie") and s.get("isComingSoon")], key=lambda s: ((s.get("releaseAt") or {}).get("CH_DE") or "9999", s.get("upcomingOrder") or 999))[:15]
    os.makedirs("pathe", exist_ok=True)
    with open("pathe/urls.txt", "w") as f:
        f.write("\n".join([SHOWS] + [DETAIL.format(s["slug"]) for s in now + soon]))
    return {"updated": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="minutes"), "source": "Pathé Schweiz",
            "now": [entry(s, raw.get(DETAIL.format(s["slug"])) or {}) for s in now],
            "soon": [entry(s, raw.get(DETAIL.format(s["slug"])) or {}) for s in soon]}

if __name__ == "__main__":
    age = raw_age_hours()
    print(f"pathe/raw.txt ist {age:.1f} Stunden alt")
    out = build() if age < 36 else None
    if out:
        json.dump(out, open("kino.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(len(out["now"]), "im Kino (Pathé),", sum(1 for x in out["now"] if x["formats"]), "mit Formaten")
    else:
        print("Keine frischen Pathé-Daten, nutze cineman.ch als Ersatz")
        subprocess.run(["python3", "scripts/kino_cineman.py"], check=False)
