"""Verify that the configured TG target is a group, not a channel."""
import json, os, sys, urllib.request, urllib.error, urllib.parse, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TG_BASE = "https://api.telegram.org/bot{token}"

env = dict(os.environ)
env_path = ROOT / "config" / "local_tg_publisher.env"
if env_path.exists():
    for raw in env_path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip().strip('"').strip("'")

secrets_path = ROOT / "config" / "local_secrets.ps1"
if secrets_path.exists():
    text = secrets_path.read_text(encoding="utf-8-sig", errors="replace")
    for name in ["TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"]:
        if name not in env or not env[name]:
            match = re.search(r"\$env:" + re.escape(name) + r"\s*=\s*['\"]([^'\"]+)['\"]", text)
            if match:
                env[name] = match.group(1).strip()

token = env.get("TELEGRAM_BOT_TOKEN", "").strip()
chat_id = env.get("TELEGRAM_CHAT_ID", "").strip()

if not token or not chat_id:
    print("MISSING credentials")
    sys.exit(1)

print("Credentials present: OK")
url = TG_BASE.format(token=token) + "/getChat"
data = urllib.parse.urlencode({"chat_id": chat_id}).encode("utf-8")
req = urllib.request.Request(url, data=data, method="POST")
try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        body = resp.read().decode("utf-8")
    result = json.loads(body)
    if not result.get("ok"):
        print(f"API error: {result.get('description', body[:200])}")
        sys.exit(1)
    chat = result.get("result", {})
    chat_type = chat.get("type", "unknown")
    chat_title = chat.get("title", "(no title)")
    masked_title = chat_title[:2] + "***" if len(chat_title) > 2 else chat_title
    print(f"Chat type: {chat_type}")
    print(f"Chat title: {masked_title}")
    if chat_type in ("group", "supergroup"):
        print("VERIFIED: Target is a TG group.")
    elif chat_type == "channel":
        print("BLOCKED: Target is a CHANNEL, not a group.")
        sys.exit(1)
    else:
        print(f"UNKNOWN chat type: {chat_type}")
        sys.exit(1)
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
