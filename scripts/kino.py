"""Einstieg für die tägliche GitHub Action: Pathé-Daten vom iPhone verwenden, sonst cineman.ch als Ersatz."""
import os, runpy, subprocess, urllib.request

# Lebenszeichen an Supabase: hält die Gratis-Datenbank wach (sonst Pause nach 7 Tagen ohne Aktivität)
try:
    req = urllib.request.Request("https://vpdgwopcsevtvvaufegr.supabase.co/rest/v1/rpc/heartbeat", data=b"{}", method="POST",
        headers={"apikey": "sb_publishable_8igcj2eTIqMjcsjkAxum7A_jSyR96RY", "Content-Type": "application/json"})
    print("Supabase-Lebenszeichen:", urllib.request.urlopen(req, timeout=20).read().decode())
except Exception as e:
    print("Supabase-Lebenszeichen fehlgeschlagen:", e)
runpy.run_path("scripts/pathe.py", run_name="__main__")
try:
    runpy.run_path("scripts/series.py", run_name="__main__")
except Exception as e:
    print("Serien fehlgeschlagen:", e)
if os.environ.get("GITHUB_ACTIONS"):
    subprocess.run(["git", "-c", "user.name=kino-bot", "-c", "user.email=kino-bot@users.noreply.github.com",
                    "pull", "--rebase", "--autostash", "-q"], check=False)
    subprocess.run(["git", "add", "pathe/urls.txt", "series.json", "cache/omdb.json"], check=False)
