import sys
from graph import app
from pr import open_pr

alert = sys.argv[1] if len(sys.argv) > 1 else "EC2 CPU above 95 percent on cloud-pulse-web, website slow"
r = app.invoke({"alert": alert})
if not r["review"].get("approved"):
    print("Reviewer rejected. No PR created:", r["review"])
    sys.exit(1)
new = r["proposed"]
if not new.endswith("\n"):
    new += "\n"
print("PR created:", open_pr("infra/main.tf", new, alert, r["triage"], r["memory"], r["review"]))
