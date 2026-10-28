import difflib
import pathlib
from typing import TypedDict

from langgraph.graph import StateGraph, END

from llm import ask_json
from memory import search_incidents

INFRA_FILE = pathlib.Path("infra/main.tf")
FORBIDDEN = ["provisioner", "local-exec", "0.0.0.0/0", "destroy"]
MAX_CHANGED_LINES = 6


class State(TypedDict, total=False):
    alert: str
    memory: list
    original: str
    triage: dict
    proposed: str
    review: dict
    attempts: int


def retrieve(state: State) -> State:
    hits = search_incidents(state["alert"])
    memory = [{"score": round(s, 3), **p} for s, p in hits]
    return {"memory": memory, "original": INFRA_FILE.read_text(), "attempts": 0}


def triage(state: State) -> State:
    prompt = f"""You are an SRE triage agent.
Alert: {state['alert']}
Similar past incidents (outcome 'failed' or 'rejected' means that fix did not work or a human rejected it): {state['memory']}
Current Terraform:
{state['original']}

Return JSON only: {{"root_cause": str, "severity": "low|medium|high", "action": str}}"""
    return {"triage": ask_json(prompt)}


def coder(state: State) -> State:
    feedback = state.get("review", {}).get("reason", "")
    prompt = f"""You are a Terraform engineer. Apply the smallest possible fix.
Triage: {state['triage']}
Past incidents: {state['memory']}
Reviewer feedback from the previous attempt (if any): {feedback}
Current infra/main.tf:
{state['original']}

Rules: change only what the triage action needs. Do not remove resources.
Do not add provisioners or open security groups.
Return JSON only: {{"new_content": "<the full updated main.tf>"}}"""
    out = ask_json(prompt)
    return {"proposed": out["new_content"], "attempts": state.get("attempts", 0) + 1}


def changed_lines(old: str, new: str) -> list:
    diff = difflib.unified_diff(old.splitlines(), new.splitlines(), lineterm="")
    return [l for l in diff if l.startswith(("+", "-")) and not l.startswith(("+++", "---"))]


def reviewer(state: State) -> State:
    old, new = state["original"], state["proposed"]
    count = lambda t: sum(1 for l in t.splitlines() if l.strip().startswith('resource "'))

    if count(old) != count(new):
        return {"review": {"approved": False, "reason": "Resource count changed"}}
    if len(changed_lines(old, new)) > MAX_CHANGED_LINES:
        return {"review": {"approved": False, "reason": "Too many lines changed"}}
    bad = [w for w in FORBIDDEN if w in new and w not in old]
    if bad:
        return {"review": {"approved": False, "reason": f"Forbidden content: {bad}"}}

    prompt = f"""You are a strict infrastructure security reviewer.
Alert: {state['alert']}
Diff:
{chr(10).join(changed_lines(old, new))}

Is this a safe, minimal fix for the alert?
Return JSON only: {{"approved": bool, "reason": str}}"""
    return {"review": ask_json(prompt)}


def route(state: State) -> str:
    if state["review"].get("approved") or state["attempts"] >= 2:
        return "end"
    return "retry"


g = StateGraph(State)
g.add_node("retrieve", retrieve)
g.add_node("triage", triage)
g.add_node("coder", coder)
g.add_node("reviewer", reviewer)
g.set_entry_point("retrieve")
g.add_edge("retrieve", "triage")
g.add_edge("triage", "coder")
g.add_edge("coder", "reviewer")
g.add_conditional_edges("reviewer", route, {"retry": "coder", "end": END})
app = g.compile()

if __name__ == "__main__":
    pathlib.Path("docs").mkdir(exist_ok=True)
    pathlib.Path("docs/agent-graph.mmd").write_text(app.get_graph().draw_mermaid())

    alert = "EC2 CPU above 95 percent on cloud-pulse-web, website slow"
    result = app.invoke({"alert": alert})

    print("\n=== MEMORY ===")
    for m in result["memory"]:
        print(m["score"], "|", m["resolution"], "|", m["outcome"])
    print("\n=== TRIAGE ===")
    print(result["triage"])
    print("\n=== PROPOSED DIFF ===")
    print("\n".join(changed_lines(result["original"], result["proposed"])))
    print("\n=== REVIEW ===")
    print(result["review"], "| attempts:", result["attempts"])
