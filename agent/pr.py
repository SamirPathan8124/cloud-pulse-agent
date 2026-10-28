import os, time
from dotenv import load_dotenv
from github import Github

load_dotenv()
REPO = os.getenv("GITHUB_REPO")
ALLOWED_PREFIX = "infra/"


def open_pr(path, new_content, alert, triage, memory, review):
    if not path.startswith(ALLOWED_PREFIX):
        raise PermissionError(f"Agent may only change files under {ALLOWED_PREFIX}")
    repo = Github(os.getenv("GITHUB_TOKEN")).get_repo(REPO)
    base = repo.get_branch("main")
    branch = f"agent/fix-{int(time.time())}"
    repo.create_git_ref(ref=f"refs/heads/{branch}", sha=base.commit.sha)
    current = repo.get_contents(path, ref=branch)
    repo.update_file(path, "fix: agent remediation", new_content, current.sha, branch=branch)
    past = "\n".join(f"- {m['resolution']} ({m['outcome']}, score {m['score']})" for m in memory)
    body = (
        f"## Alert\n{alert}\n\n## Triage\n- Root cause: {triage.get('root_cause')}\n"
        f"- Severity: {triage.get('severity')}\n- Action: {triage.get('action')}\n\n"
        f"## Similar past incidents\n{past}\n\n"
        f"## AI reviewer\n{review.get('reason')}\n\n"
        "Human approval required before merge."
    )
    pr = repo.create_pull(title="Agent fix: " + str(triage.get("action"))[:70],
                          body=body, head=branch, base="main")
    try:
        from notify import notify
        notify("Cloud-Pulse: agent fix needs your approval",
               [f"Alert: {alert}", f"Severity: {triage.get('severity')}",
                f"Action: {triage.get('action')}",
                "CI checks are running. Review the PR, then merge or close it."],
               pr.html_url)
    except Exception as e:
        print("[notify] failed:", e)
    return pr.html_url

