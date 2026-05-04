"""
FastAPI backend for the AI Daily News dashboard.
Run: uvicorn api:app --reload --port 8000
"""

import hashlib
import hmac
import json
import secrets as _secrets
import subprocess
import sys
import threading
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Generator

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel

ROOT = Path(__file__).parent

# DATA_DIR env var points to a persistent volume on Railway (set to /data).
# Falls back to the repo root for local dev.
import os as _os
_DATA_DIR = Path(_os.environ["DATA_DIR"]) if "DATA_DIR" in _os.environ else ROOT
try:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
except Exception as _e:
    print(f"WARNING: Could not create data dir {_DATA_DIR}: {_e}. Falling back to repo root.")
    _DATA_DIR = ROOT

CONFIG_FILE = _DATA_DIR / "config.json"
SEEN_FILE   = _DATA_DIR / "seen_articles.json"

# On first boot with a fresh volume, seed config.json from the repo copy.
_REPO_CONFIG = ROOT / "config.json"
if not CONFIG_FILE.exists() and _REPO_CONFIG.exists() and CONFIG_FILE != _REPO_CONFIG:
    import shutil as _shutil
    _shutil.copy(_REPO_CONFIG, CONFIG_FILE)

# ── Preferences token helpers ──────────────────────────────
def _make_prefs_token(email: str, secret: str) -> str:
    return hmac.new(secret.encode(), email.encode(), hashlib.sha256).hexdigest()[:24]

def _verify_prefs_token(email: str, token: str, secret: str) -> bool:
    if not secret:
        return False
    return hmac.compare_digest(_make_prefs_token(email, secret), token)

_PREFS_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Manage Email Preferences — Micro SEO</title>
<style>
  *,*::before,*::after{{box-sizing:border-box}}
  body{{margin:0;padding:40px 16px;background:#F4F4F5;
       font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;color:#09090B}}
  .card{{max-width:480px;margin:0 auto;background:#fff;border-radius:16px;
         padding:40px;box-shadow:0 4px 24px rgba(0,0,0,.10)}}
  .brand{{font-size:20px;font-weight:900;letter-spacing:-.3px;margin-bottom:28px}}
  .brand em{{font-style:italic;font-weight:400;color:#6366F1}}
  h1{{font-size:22px;font-weight:700;margin:0 0 8px}}
  .sub{{font-size:14px;color:#52525B;margin:0 0 28px;line-height:1.6}}
  .option{{display:flex;align-items:flex-start;gap:14px;padding:16px;
           border:1.5px solid #E4E4E7;border-radius:10px;margin-bottom:12px;cursor:pointer}}
  .option:has(input:checked){{border-color:#6366F1;background:#FAFAFA}}
  .option input[type=checkbox]{{margin-top:3px;accent-color:#6366F1;width:17px;height:17px;flex-shrink:0;cursor:pointer}}
  .opt-title{{font-size:15px;font-weight:600;margin:0 0 4px}}
  .opt-desc{{font-size:13px;color:#71717A;margin:0;line-height:1.5}}
  .btn{{width:100%;padding:13px;background:#6366F1;color:#fff;font-size:15px;font-weight:600;
        border:none;border-radius:8px;cursor:pointer;margin-top:4px;letter-spacing:.2px}}
  .btn:hover{{background:#4F46E5}}
  hr{{border:none;border-top:1px solid #E4E4E7;margin:24px 0}}
  .unsub{{text-align:center;font-size:13px;color:#A1A1AA}}
  .unsub a{{color:#A1A1AA}}
  .banner{{background:#F0FDF4;border:1.5px solid #86EFAC;border-radius:10px;
           padding:14px 18px;color:#166534;font-size:14px;font-weight:500;margin-bottom:24px}}
</style>
</head>
<body>
<div class="card">
  <div class="brand">Micro<em>&nbsp;SEO</em></div>
  {banner}
  <h1>Manage Your AI News Preferences</h1>
  <p class="sub">Choose which updates you want in your daily digest.</p>
  <form method="POST" action="/preferences">
    <input type="hidden" name="email" value="{email}">
    <input type="hidden" name="token" value="{token}">
    <label class="option">
      <input type="checkbox" name="marketing" value="1" {marketing_checked}>
      <div>
        <p class="opt-title">Marketing Insights</p>
        <p class="opt-desc">SEO updates, AI Overviews research, Google Business Profile changes, and GEO strategy signals.</p>
      </div>
    </label>
    <label class="option">
      <input type="checkbox" name="development" value="1" {development_checked}>
      <div>
        <p class="opt-title">Development &amp; AI Engineering</p>
        <p class="opt-desc">OpenAI, Anthropic, and Perplexity product releases, model updates, and API changes.</p>
      </div>
    </label>
    <button type="submit" class="btn">Save Preferences</button>
  </form>
  <hr>
  <p class="unsub"><a href="mailto:{email}?subject=Unsubscribe%20from%20Micro%20SEO">Unsubscribe from all emails</a></p>
</div>
</body>
</html>"""


@asynccontextmanager
async def _lifespan(app: FastAPI):
    cfg = _load()
    if not cfg.get("preferences_secret"):
        cfg["preferences_secret"] = _secrets.token_hex(32)
        _save(cfg)
    yield


app = FastAPI(title="AI Daily News API", lifespan=_lifespan)
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

@app.get("/config-export")
def export_config():
    """Returns raw config.json for GitHub Actions to consume before each run."""
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(CONFIG_FILE.read_text(), media_type="application/json")

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
    existing = recs[index]
    recs[index] = {**existing, "first_name": r.first_name, "email": r.email}
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
        except Exception as e:
            _run_status = "error"
            _last_error = f"GitHub dispatch failed: {type(e).__name__}: {str(e)[:120]}"
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
            _log_lines.append("Polling window ended — check GitHub Actions for final status.")
            _run_status = "success"

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


# ── Preferences ────────────────────────────────────────────
def _prefs_page_html(email: str, token: str, saved: bool, prefs: dict) -> str:
    return _PREFS_HTML.format(
        email=email,
        token=token,
        banner='<div class="banner">&#10003; Your preferences have been updated.</div>' if saved else "",
        marketing_checked="checked" if prefs.get("marketing", True) else "",
        development_checked="checked" if prefs.get("development", True) else "",
    )

@app.get("/preferences", response_class=HTMLResponse)
def preferences_page(email: str = "", token: str = ""):
    cfg    = _load()
    secret = cfg.get("preferences_secret", "")
    if not email or not _verify_prefs_token(email, token, secret):
        return HTMLResponse("<p style='font-family:sans-serif;padding:40px'>Invalid or expired link.</p>", status_code=400)
    recipients = cfg.get("email", {}).get("recipients", [])
    recip  = next((r for r in recipients if r.get("email") == email), None)
    prefs  = (recip or {}).get("preferences", {"marketing": True, "development": True})
    return HTMLResponse(_prefs_page_html(email, token, False, prefs))

@app.post("/preferences", response_class=HTMLResponse)
async def save_preferences(
    email:       str = Form(""),
    token:       str = Form(""),
    marketing:   str | None = Form(None),
    development: str | None = Form(None),
):
    cfg    = _load()
    secret = cfg.get("preferences_secret", "")
    if not email or not _verify_prefs_token(email, token, secret):
        return HTMLResponse("<p style='font-family:sans-serif;padding:40px'>Invalid or expired link.</p>", status_code=400)
    prefs = {"marketing": marketing is not None, "development": development is not None}
    recipients = cfg.get("email", {}).get("recipients", [])
    for r in recipients:
        if r.get("email") == email:
            r["preferences"] = prefs
            r["preferences_updated"] = datetime.utcnow().isoformat()
    _save(cfg)
    return HTMLResponse(_prefs_page_html(email, token, True, prefs))
