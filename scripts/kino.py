"""Einstieg für die tägliche GitHub Action: Pathé-Daten vom iPhone verwenden, sonst cineman.ch als Ersatz."""
import os, runpy, subprocess
runpy.run_path("scripts/pathe.py", run_name="__main__")
if os.environ.get("GITHUB_ACTIONS"):
    subprocess.run(["git", "-c", "user.name=kino-bot", "-c", "user.email=kino-bot@users.noreply.github.com",
                    "pull", "--rebase", "--autostash", "-q"], check=False)
