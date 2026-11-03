"""Runs every test case, records full traces (chunks, scores, prompt, answer) to results/.
Usage: python run_tests.py --tag baseline
       python run_tests.py --tag topk5 --top_k 5
       python run_tests.py --tag naive --prompt naive
       python run_tests.py --tag bigchunks --chunk_size 120 --overlap 20
       python run_tests.py --tag strict2 --prompt strict_v2
       python run_tests.py --tag allcontext --chunk_size 120 --overlap 20 --top_k 8
"""
import argparse, json, os, re
from rag import RAG
from test_cases import TEST_CASES

# Automatic flags are only a first filter: always confirm by reading the answers.
ABSTAIN = re.compile(
    r"don't know|do not know|not (mentioned|provided|in the)|"
    r"does not (mention|contain|say|provide)|doesn't (mention|contain|say|provide)|"
    r"cannot find|can't find|no information",
    re.I,
)
CONFLICT = re.compile(
    r"conflict|differ|disagree|outdated|superseded|discrepan|inconsisten|newer|older",
    re.I,
)

ap = argparse.ArgumentParser()
ap.add_argument("--tag", default="baseline")
ap.add_argument("--chunk_size", type=int, default=50)
ap.add_argument("--overlap", type=int, default=10)
ap.add_argument("--top_k", type=int, default=3)
ap.add_argument("--prompt", default="strict", choices=["naive", "strict", "strict_v2"])
a = ap.parse_args()

os.makedirs("results", exist_ok=True)

rag = RAG(chunk_size=a.chunk_size, overlap=a.overlap, top_k=a.top_k, prompt_mode=a.prompt)
print(f"{len(rag.chunks)} chunks indexed | config: {vars(a)}\n")

results, md = [], [f"# Trace: {a.tag}\nConfig: `{vars(a)}`\n"]
for tc in TEST_CASES:
    out = rag.ask(tc["question"])
    got = {r["source"] for r in out["retrieved"]}
    gold = set(tc["gold_sources"])
    out.update({
        "id": tc["id"], "category": tc["category"], "expected": tc["expected"],
        "gold_sources": tc["gold_sources"],
        "auto_retrieval_hit": (gold <= got) if gold else None,   # all gold docs retrieved?
        "auto_abstained": bool(ABSTAIN.search(out["answer"])),
        "auto_flagged_conflict": bool(CONFLICT.search(out["answer"])),
        "auto_asked_clarification": "?" in out["answer"],
        "manual_grade": "TODO (correct / partial / wrong / hallucinated)",
        "manual_root_cause": "TODO (chunking / retrieval / context injection / generation)",
    })
    results.append(out)
    md.append(f"## {tc['id']} [{tc['category']}] {tc['question']}\n**Expected:** {tc['expected']}\n")
    md.append("**Retrieved:**")
    for r in out["retrieved"]:
        md.append(f"- `{r['id']}` (score {r['score']}): {r['text']}")
    md.append(f"\n**Answer:** {out['answer']}\n")
    md.append(
        f"_retrieval_hit={out['auto_retrieval_hit']} abstained={out['auto_abstained']} "
        f"flagged_conflict={out['auto_flagged_conflict']} asked_clarification={out['auto_asked_clarification']}_\n"
    )
    print(f"{tc['id']:4} {tc['category']:12} hit={str(out['auto_retrieval_hit']):5} "
          f"abstain={out['auto_abstained']!s:5} conflict_flag={out['auto_flagged_conflict']!s:5} "
          f"clarify={out['auto_asked_clarification']!s:5} | {out['answer'][:60]!r}")

with open(f"results/traces_{a.tag}.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)
with open(f"results/traces_{a.tag}.md", "w", encoding="utf-8") as f:
    f.write("\n".join(md))
print(f"\nSaved results/traces_{a.tag}.json and .md  -> now grade each case manually.")