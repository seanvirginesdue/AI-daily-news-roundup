"""
Harold's review gate — run this after reviewing digest_preview.html.

  python approve_digest.py

Reads digest_pending.json, sends the Team Digest to all Tier 2 recipients,
then removes the pending file and preview file.
"""

import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

_ROOT         = Path(__file__).parent
_PENDING_FILE = _ROOT / "digest_pending.json"
_PREVIEW_FILE = _ROOT / "digest_preview.html"
_CONFIG_FILE  = _ROOT / "config.json"


def send_digest() -> None:
    if not _PENDING_FILE.exists():
        print("Nothing pending. Run main.py first to generate today's digest.")
        return

    data = json.loads(_PENDING_FILE.read_text(encoding="utf-8"))
    subject      = data["subject"]
    brief_data   = data["brief_data"]
    articles     = data["articles"]
    display_date = data["display_date"]

    config = json.loads(_CONFIG_FILE.read_text())
    all_recipients = config.get("email", {}).get("recipients", [])
    tier2 = [r for r in all_recipients if r.get("tier", 1) == 2]

    if not tier2:
        print("No Tier 2 recipients in config.json. Add them before running this.")
        return

    # Warn about placeholder emails
    placeholders = [r for r in tier2 if r["email"].endswith("@boulderseomarketing.com")
                    and r["email"].split("@")[0] in ("greg","barb","kathleen","jam")]
    if placeholders:
        names = ", ".join(r["first_name"] for r in placeholders)
        print(f"  [WARN] Placeholder emails detected for: {names}")
        print(f"         Update config.json with real addresses before sending.")
        ans = input("  Send anyway? [y/N] ").strip().lower()
        if ans != "y":
            print("Aborted.")
            return

    from pipeline.send_email import send_newsletter
    print(f"\n📬 Sending Team Digest to {len(tier2)} recipient(s)...")
    send_newsletter(
        subject, brief_data, articles, display_date,
        tier1_recipients=[],
        tier2_recipients=tier2,
        tier2_brief=brief_data,
        tier2_subject=subject,
    )

    _PENDING_FILE.unlink()
    if _PREVIEW_FILE.exists():
        _PREVIEW_FILE.unlink()
    print(f"\n✅ Digest sent and pending files cleaned up.\n")


if __name__ == "__main__":
    try:
        send_digest()
    except KeyboardInterrupt:
        print("\nCancelled.")
        sys.exit(0)
    except Exception as exc:
        print(f"\n❌ Error: {exc}")
        raise
