# RAG Failure & Hallucination Investigator

```
pip install -r requirements.txt
export LLM_API_KEY=...                               # omit for MOCK mode (retrieval only)
export LLM_BASE_URL=https://api.groq.com/openai/v1   # or http://localhost:11434/v1 for Ollama; omit for OpenAI
export LLM_MODEL=llama-3.1-8b-instant                # or gpt-4o-mini / llama3.2 etc.
python run_tests.py --tag baseline
python run_tests.py --tag naive --prompt naive
python run_tests.py --tag topk5 --top_k 5
python run_tests.py --tag bigchunks --chunk_size 120 --overlap 20
```

Then grade `results/traces_*.md`, and complete `REPORT.md`.