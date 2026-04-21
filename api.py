"""
FastAPI backend for the AI Daily News dashboard.
Run: uvicorn api:app --reload --port 8000
"""

import json
import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Generator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

ROOT = Path(__file__).parent

# DATA_DIR env var points to a persistent volume on Railway (set to /data).
# Falls back to the repo root for local dev.
import os as _os
_DATA_DIR = Path(_os.environ["DATA_DIR"]) if "DATA_DIR" in _os.environ else ROOT
_DATA_DIR.mkdir(parents=True, exist_ok=True)

CONFIG_FILE = _DATA_DIR / "config.json"
SEEN_FILE   = _DATA_DIR / "seen_articles.json"

# On first boot with a fresh volume, seed config.json from the repo copy.
_REPO_CONFIG = ROOT / "config.json"
if not CONFIG_FILE.exists() and _REPO_CONFIG.exists() and CONFIG_FILE != _REPO_CONFIG:
    import shutil as _shutil
    _shutil.copy(_REPO_CONFIG, CONFIG_FILE)

app = FastAPI(title="AI Daily News API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Config helpers ─────────────────────────────────────────
_lock = threading.Lock()

def _load() -> dict:
    with _lock:
        return json.loads(CONFIG_FILE.read_text())

def _save(cfg: dict) -> None:
    with _lock:
        CONFIG_FILE.write_text(json.dumps(cfg, indent=2))

# ── Run state ──────────────────────────────────────────────
_process:    subprocess.Popen | None = None
_run_status: str  = "idle"          # idle | running | success | error
_last_run:   str  = ""
_last_error: str  = ""
_log_lines:  list[str] = []

# ── Models ─────────────────────────────────────────────────
class Feed(BaseModel):
    name: str
    url:  str

class Recipient(BaseModel):
    first_name: str
    email:      str

class Settings(BaseModel):
    max_articles:    int
    from_name:       str
    from_address:    str
    reply_to:        str
    send_hour_utc:   int = 0

# ── Config ─────────────────────────────────────────────────
@app.get("/config")
def get_config():
    return _load()

# ── Feeds ──────────────────────────────────────────────────
@app.get("/feeds")
def get_feeds():
    return _load()["rss_feeds"]

@app.post("/feeds", status_code=201)
def add_feed(feed: Feed):
    cfg = _load()
    cfg["rss_feeds"].append({"name": feed.name, "url": feed.url})
    _save(cfg)
    return cfg["rss_feeds"]

@app.put("/feeds/{index}")
def update_feed(index: int, feed: Feed):
    cfg = _load()
    if index < 0 or index >= len(cfg["rss_feeds"]):
        raise HTTPException(404, "Feed not found")
    cfg["rss_feeds"][index] = {"name": feed.name, "url": feed.url}
    _save(cfg)
    return cfg["rss_feeds"]

@app.delete("/feeds/{index}")
def delete_feed(index: int):
    cfg = _load()
    if index < 0 or index >= len(cfg["rss_feeds"]):
        raise HTTPException(404, "Feed not found")
    cfg["rss_feeds"].pop(index)
    _save(cfg)
    return cfg["rss_feeds"]

# ── Recipients ─────────────────────────────────────────────
@app.get("/recipients")
def get_recipients():
    return _load()["email"]["recipients"]

@app.post("/recipients", status_code=201)
def add_recipient(r: Recipient):
    cfg = _load()
    cfg["email"]["recipients"].append({"first_name": r.first_name, "email": r.email})
    _save(cfg)
    return cfg["email"]["recipients"]

@app.put("/recipients/{index}")
def update_recipient(index: int, r: Recipient):
    cfg = _load()
    recs = cfg["email"]["recipients"]
    if index < 0 or index >= len(recs):
        raise HTTPException(404, "Recipient not found")
    recs[index] = {"first_name": r.first_name, "email": r.email}
    _save(cfg)
    return recs

@app.delete("/recipients/{index}")
def delete_recipient(index: int):
    cfg = _load()
    recs = cfg["email"]["recipients"]
    if index < 0 or index >= len(recs):
        raise HTTPException(404, "Recipient not found")
    recs.pop(index)
    _save(cfg)
    return recs

# ── Settings ───────────────────────────────────────────────
@app.get("/settings")
def get_settings():
    cfg = _load()
    ec  = cfg["email"]
    return {
        "max_articles":  cfg.get("max_articles", 22),
        "from_name":     ec.get("from_name", ""),
        "from_address":  ec.get("from_address", ""),
        "reply_to":      ec.get("reply_to", ""),
        "send_hour_utc": cfg.get("send_hour_utc", 0),
    }

@app.put("/settings")
def update_settings(s: Settings):
    cfg = _load()
    cfg["max_articles"]        = s.max_articles
    cfg["send_hour_utc"]       = s.send_hour_utc
    cfg["email"]["from_name"]  = s.from_name
    cfg["email"]["from_address"] = s.from_address
    cfg["email"]["reply_to"]   = s.reply_to
    _save(cfg)
    return s

# ── Seen articles ──────────────────────────────────────────
@app.get("/seen-articles")
def seen_count():
    if SEEN_FILE.exists():
        data = json.loads(SEEN_FILE.read_text())
        return {"count": len(data)}
    return {"count": 0}

@app.delete("/seen-articles")
def clear_seen():
    SEEN_FILE.write_text("[]")
    return {"count": 0}

# ── Run pipeline ───────────────────────────────────────────
@app.get("/run/status")
def run_status():
    return {
        "status":     _run_status,
        "last_run":   _last_run,
        "last_error": _last_error,
    }

@app.post("/run")
def trigger_run():
    global _process, _run_status, _last_run, _last_error, _log_lines

    if _run_status == "running":
        raise HTTPException(409, "A run is already in progress")

    _log_lines  = []
    _run_status = "running"
    _last_error = ""
    _last_run   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    github_token = _os.environ.get("GITHUB_TOKEN")
    github_repo  = _os.environ.get("GITHUB_REPO", "")

    if github_token and github_repo:
        # Dispatch to GitHub Actions — SMTP works there
        import urllib.request as _ur, urllib.error as _ue
        url  = f"https://api.github.com/repos/{github_repo}/actions/workflows/newsletter.yml/dispatches"
        body = json.dumps({"ref": "main"}).encode()
        req  = _ur.Request(url, data=body, method="POST")
        req.add_header("Authorization", f"Bearer {github_token}")
        req.add_header("Accept", "application/vnd.github+json")
        req.add_header("Content-Type", "application/json")
        try:
            _ur.urlopen(req, timeout=10)
        except _ue.HTTPError as e:
            _run_status = "error"
            _last_error = f"GitHub dispatch failed: {e.code} {e.reason}"
            return {"status": "error"}

        actions_url = f"https://github.com/{github_repo}/actions"
        _log_lines.append("Dispatched to GitHub Actions.")
        _log_lines.append(f"Track live progress at: {actions_url}")
        _log_lines.append("This window will update when the run completes (~3 min).")

        def _poll_gh():
            global _run_status, _last_error
            import time as _t, urllib.request as _ur2
            _t.sleep(10)  # wait for the run to register
            for _ in range(60):  # poll up to 5 min
                try:
                    runs_url = f"https://api.github.com/repos/{github_repo}/actions/runs?per_page=1&event=workflow_dispatch"
                    r = _ur2.Request(runs_url)
                    r.add_header("Authorization", f"Bearer {github_token}")
                    r.add_header("Accept", "application/vnd.github+json")
                    with _ur2.urlopen(r, timeout=10) as resp:
                        data = json.loads(resp.read())
                    runs = data.get("workflow_runs", [])
                    if runs:
                        conclusion = runs[0].get("conclusion")
                        status     = runs[0].get("status")
                        if conclusion == "success":
                            _log_lines.append("GitHub Actions run completed successfully.")
                            _run_status = "success"
                            return
                        elif conclusion in ("failure", "cancelled"):
                            _log_lines.append(f"GitHub Actions run {conclusion}.")
                            _run_status = "error"
                            _last_error = f"GitHub Actions run {conclusion}"
                            return
                        elif status == "in_progress":
                            _log_lines.append("Still running...")
                except Exception:
                    pass
                _t.sleep(5)
            _run_status = "success"  # assume done if we stop polling

        threading.Thread(target=_poll_gh, daemon=True).start()

    else:
        # Local dev — run subprocess directly
        if _process is not None and _process.poll() is None:
            raise HTTPException(409, "A run is already in progress")

        _process = subprocess.Popen(
            [sys.executable, str(ROOT / "main.py")],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            cwd=str(ROOT),
        )

        def _collect():
            global _run_status, _last_error
            for line in _process.stdout:
                _log_lines.append(line.rstrip())
            _process.wait()
            if _process.returncode == 0:
                _run_status = "success"
            else:
                _run_status = "error"
                _last_error = _log_lines[-1] if _log_lines else "Unknown error"

        threading.Thread(target=_collect, daemon=True).start()

    return {"status": "started"}

@app.get("/run/stream")
def stream_logs():
    def _gen() -> Generator[str, None, None]:
        sent = 0
        while True:
            while sent < len(_log_lines):
                yield f"data: {_log_lines[sent]}\n\n"
                sent += 1
            if _run_status != "running" and sent >= len(_log_lines):
                yield f"data: [DONE:{_run_status}]\n\n"
                break
            import time; time.sleep(0.3)

    return StreamingResponse(_gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache",
                                      "X-Accel-Buffering": "no"})
