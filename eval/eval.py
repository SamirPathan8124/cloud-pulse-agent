import sys, json, re, time, pathlib
sys.path.insert(0, "agent")
import graph
from memory import search_incidents as real_search

ORDER = ["nano", "micro", "small", "medium", "large", "xlarge", "2xlarge"]
BASE = pathlib.Path("eval/baseline_main.tf")
RES = pathlib.Path("eval/results.json")
OUT = pathlib.Path("docs/eval-results.md")

CASES = [
    ("EC2 CPU utilization above 92 percent for 10 minutes on cloud-pulse-web", "bigger"),
    ("Website slow and CPU saturated at 97 percent", "bigger"),
    ("5xx errors rising, instance memory exhausted", "bigger"),
    ("Throughput dropped during traffic spike, CPU at 90 percent", "bigger"),
    ("FinOps: instance averaged 0.2 percent CPU over 24h, oversized and wasting money", "smaller"),
    ("Latency is high but CPU is normal at 12 percent", "same"),
    ("Disk usage above 90 percent on web server", "same"),
    ("EC2 status check failed on cloud-pulse-web", "same"),
]


def size(tf):
    m = re.search(r'instance_type\s*=\s*"[a-z0-9]+\.(\w+)"', tf)
    return ORDER.index(m.group(1)) if m and m.group(1) in ORDER else None


def run_case(alert, use_memory):
    graph.search_incidents = real_search if use_memory else (lambda a: [])
    t = time.time()
    r = graph.app.invoke({"alert": alert})
    b, a = size(r["original"]), size(r["proposed"])
    if b is None or a is None:
        d = "unknown"
    else:
        d = "bigger" if a > b else "smaller" if a < b else "same"
    return {"direction": d, "approved": bool(r["review"].get("approved")),
            "attempts": r["attempts"], "seconds": round(time.time() - t, 1)}


def passed(expect, res):
    if res["direction"] != expect:
        return False
    return res["approved"] or expect == "same"


def report(results):
    rows = []
    tot = {"memory": 0, "no_memory": 0}
    n = {"memory": 0, "no_memory": 0}
    for i, (alert, expect) in enumerate(CASES):
        cells = []
        for mode in ("memory", "no_memory"):
            r = results.get(f"{i}:{mode}")
            if r is None:
                cells.append("not run")
                continue
            ok = passed(expect, r)
            n[mode] += 1
            tot[mode] += int(ok)
            cells.append(("PASS" if ok else "FAIL") + f" ({r['direction']})")
        rows.append(f"| {i+1} | {alert} | {expect} | {cells[0]} | {cells[1]} |")
    lines = ["# Evaluation: agent with memory vs without memory", "",
             "| # | Alert | Expected change | With memory | Without memory |",
             "|---|---|---|---|---|"] + rows
    lines += ["", f"**With memory: {tot['memory']}/{n['memory']} correct. "
              f"Without memory: {tot['no_memory']}/{n['no_memory']} correct.**", "",
              "Method: fixed baseline main.tf (t3.micro), rule-based scoring on the direction of the "
              "instance_type change. Memory is a small seeded set of 8 incidents plus lessons from real PRs, "
              "so this shows the memory effect, not a general benchmark."]
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


def main():
    limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else 4
    graph.INFRA_FILE = BASE
    results = json.loads(RES.read_text()) if RES.exists() else {}
    done = 0
    for i, (alert, expect) in enumerate(CASES):
        for mode in ("memory", "no_memory"):
            key = f"{i}:{mode}"
            if key in results or done >= limit:
                continue
            try:
                res = run_case(alert, mode == "memory")
            except Exception as e:
                print("[eval] stopped (probably Gemini quota):", str(e)[:150])
                RES.write_text(json.dumps(results, indent=1))
                return
            results[key] = res
            RES.write_text(json.dumps(results, indent=1))
            done += 1
            print(f"[eval] case {i+1} {mode}: expect={expect} got={res['direction']} "
                  f"approved={res['approved']} pass={passed(expect, res)} ({res['seconds']}s)")
    report(results)


if __name__ == "__main__":
    main()
