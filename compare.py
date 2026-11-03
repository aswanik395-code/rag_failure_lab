"""Prints a side-by-side summary of every results/traces_*.json run."""
import json, glob, os

runs = {}
for path in sorted(glob.glob("results/traces_*.json")):
    tag = os.path.basename(path)[len("traces_"):-len(".json")]
    with open(path, encoding="utf-8") as f:
        runs[tag] = {r["id"]: r for r in json.load(f)}

tags = list(runs)
print(f"{'ID':4} {'category':12} " + " | ".join(f"{t:^22}" for t in tags))
print("-" * (18 + 25 * len(tags)))
base = runs[tags[0]]
for tid, r in base.items():
    cells = []
    for t in tags:
        x = runs[t].get(tid)
        if not x:
            cells.append(f"{'-':^22}")
            continue
        s = f"hit={'-' if x['auto_retrieval_hit'] is None else int(x['auto_retrieval_hit'])} ab={int(x['auto_abstained'])} cf={int(x['auto_flagged_conflict'])}"
        cells.append(f"{s:^22}")
    print(f"{tid:4} {r['category']:12} " + " | ".join(cells))
print("\nhit=gold docs retrieved, ab=abstained, cf=flagged conflict")