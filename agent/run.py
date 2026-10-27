import sys, json, pathlib
from pr import open_pr

CACHE = pathlib.Path(".last_run.json")
args = [a for a in sys.argv[1:] if not a.startswith("--")]
alert = args[0] if args else "EC2 CPU above 95 percent on cloud-pulse-web, website slow"

if CACHE.exists() and "--reuse" in sys.argv:
    r = json.loads(CACHE.read_text())
    print("[cache] reusing last agent result")
else:
    from graph import app
    r = app.invoke({"alert": alert})
    CACHE.write_text(json.dumps(r))

if not r["review"].get("approved"):
    print("Reviewer rejected. No PR created:", r["review"])
    sys.exit(1)
new = r["proposed"]
if not new.endswith("\n"):
    new += "\n"
print("PR created:", open_pr("infra/main.tf", new, alert, r["triage"], r["memory"], r["review"]))
