import os, re
from dotenv import load_dotenv
from github import Github
from memory import init_collection, add_incident

load_dotenv()
repo = Github(os.getenv("GITHUB_TOKEN")).get_repo(os.getenv("GITHUB_REPO"))


def grab(pattern, text):
    m = re.search(pattern, text or "", re.S)
    return m.group(1).strip() if m else ""


def learn():
    init_collection()
    saved = 0
    for pr in repo.get_pulls(state="closed"):
        if not pr.head.ref.startswith("agent/fix-"):
            continue
        alert = grab(r"## Alert\n(.*?)\n\n", pr.body)
        root = grab(r"- Root cause: ([^\n]*)", pr.body)
        action = grab(r"- Action: ([^\n]*)", pr.body)
        if not alert:
            continue
        outcome = "success" if pr.merged else "rejected"
        add_incident(1000 + pr.number, alert, root, action, outcome)
        print(f"[learn] PR #{pr.number} -> {outcome}: {action}")
        saved += 1
    print("[learn] lessons saved:", saved)


if __name__ == "__main__":
    learn()
