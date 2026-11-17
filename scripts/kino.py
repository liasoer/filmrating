"""Einstieg für die tägliche GitHub Action: Pathé-Daten vom iPhone verwenden, sonst cineman.ch als Ersatz."""
import os, runpy, subprocess
runpy.run_path("scripts/pathe.py", run_name="__main__")
try:
    runpy.run_path("scripts/series.py", run_name="__main__")
except Exception as e:
    print("Serien fehlgeschlagen:", e)
if os.environ.get("GITHUB_ACTIONS"):
    subprocess.run(["git", "-c", "user.name=kino-bot", "-c", "user.email=kino-bot@users.noreply.github.com",
                    "pull", "--rebase", "--autostash", "-q"], check=False)
    subprocess.run(["git", "add", "pathe/urls.txt", "series.json", "cache/omdb.json"], check=False)
