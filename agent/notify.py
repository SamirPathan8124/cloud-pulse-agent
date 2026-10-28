import os, json, urllib.request
from dotenv import load_dotenv

load_dotenv()


def notify(title, lines, url=None):
    hook = (os.getenv("DISCORD_WEBHOOK_URL") or "").strip()
    if not hook:
        return False
    content = f"**{title}**\n" + "\n".join(lines) + (f"\n{url}" if url else "")
    req = urllib.request.Request(
        hook,
        data=json.dumps({"content": content[:1900]}).encode(),
        headers={"Content-Type": "application/json", "User-Agent": "cloud-pulse-agent"},
        method="POST")
    urllib.request.urlopen(req, timeout=15)
    return True
