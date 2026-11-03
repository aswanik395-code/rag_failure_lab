# RAG Failure & Hallucination Investigator

A deliberately messy RAG testbed (8 NovaCart policy docs with overlaps and conflicts, 11 test questions)
used to find and diagnose where a RAG pipeline fails. See `REPORT.md` for the analysis.

## Setup
```
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```
Copy `.env.example` to `.env` and add your key:
```
LLM_API_KEY=your_key_here
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_MODEL=openai/gpt-oss-20b
```

## Runs
```
python run_tests.py --tag baseline
python run_tests.py --tag naive --prompt naive
python run_tests.py --tag topk5 --top_k 5
python run_tests.py --tag bigchunks --chunk_size 120 --overlap 20
python run_tests.py --tag allcontext --chunk_size 120 --overlap 20 --top_k 8
python run_tests.py --tag strict2 --prompt strict_v2
python run_tests.py --tag strict2_all --prompt strict_v2 --chunk_size 120 --overlap 20 --top_k 8
python compare.py
python inspect_case.py T6 T7 T9
```
Traces (retrieved chunks, scores, prompts, answers) are saved in `results/`.