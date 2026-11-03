"""Usage: python inspect_case.py T6 T7"""
import json, glob, os, sys

ids = sys.argv[1:] or ["T6"]
for path in sorted(glob.glob("results/traces_*.json")):
    tag = os.path.basename(path)[len("traces_"):-len(".json")]
    with open(path, encoding="utf-8") as f:
        data = {r["id"]: r for r in json.load(f)}
    for tid in ids:
        r = data[tid]
        print(f"\n===== {tag} | {tid} | {r['question']}")
        print("gold:", r["gold_sources"])
        for c in r["retrieved"]:
            print(f"  {c['score']:.3f}  {c['id']}")
        print("ANSWER:", r["answer"][:600])