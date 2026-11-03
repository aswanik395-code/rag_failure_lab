"""Minimal, deliberately naive RAG pipeline (a testbed, not a product).
Stages: load -> chunk -> embed -> retrieve -> prompt (context injection) -> generate.
LLM: any OpenAI-compatible endpoint via env vars (OpenAI, Groq, Ollama...).
No key set -> MOCK mode (returns top chunk) so you can still test retrieval.
"""
import os, glob
import numpy as np
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

load_dotenv()
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

PROMPTS = {
    "strict_v2": (
        "You are a support assistant. Answer ONLY using the context below.\n"
        "Rules:\n- If the context does not contain the answer, reply exactly: \"I don't know based on the provided documents.\"\n"
        "- If the question is too vague or ambiguous to answer (for example, unclear what 'it' refers to), "
        "ask ONE clarifying question instead of guessing.\n"
        "- If sources conflict, name each source, say which is newer based on any dates in the text, "
        "prefer the newer one, and mention the older value. Today's date is November 2026.\n"
        "- If the answer depends on conditions (item type, membership), list each case.\n"
        "- Cite sources like [source: filename].\n\n"
        "Context:\n{context}\n\nQuestion: {question}\nAnswer:"
    ),
    # naive: invites hallucination, useful as a baseline for comparison
    "naive": "Use the context below to answer the question.\n\nContext:\n{context}\n\nQuestion: {question}\nAnswer:",
    # strict: grounded, cites sources, allowed to abstain, must flag conflicts
    "strict": (
        "You are a support assistant. Answer ONLY using the context below.\n"
        "Rules:\n- If the context does not contain the answer, reply exactly: \"I don't know based on the provided documents.\"\n"
        "- If the context contains conflicting information, point out the conflict and name each source.\n"
        "- Cite sources like [source: filename].\n\n"
        "Context:\n{context}\n\nQuestion: {question}\nAnswer:"
    ),
}


def load_docs(folder="docs"):
    docs = []
    for path in sorted(glob.glob(os.path.join(folder, "*.md"))):
        with open(path, encoding="utf-8") as f:
            docs.append({"source": os.path.basename(path), "text": f.read().strip()})
    return docs


def chunk_words(text, size, overlap):
    """Fixed-size word window chunking. Naive on purpose: can split facts in half."""
    words = text.split()
    step = max(size - overlap, 1)
    chunks = []
    for start in range(0, len(words), step):
        piece = words[start:start + size]
        if piece:
            chunks.append(" ".join(piece))
        if start + size >= len(words):
            break
    return chunks


class RAG:
    def __init__(self, docs_folder="docs", chunk_size=50, overlap=10, top_k=3, prompt_mode="strict"):
        self.top_k, self.prompt_mode = top_k, prompt_mode
        self.embedder = SentenceTransformer(EMBED_MODEL)
        self.chunks = []
        for d in load_docs(docs_folder):
            for i, c in enumerate(chunk_words(d["text"], chunk_size, overlap)):
                self.chunks.append({"id": f'{d["source"]}#{i}', "source": d["source"], "text": c})
        self.emb = self.embedder.encode([c["text"] for c in self.chunks], normalize_embeddings=True)

    def retrieve(self, question):
        q = self.embedder.encode([question], normalize_embeddings=True)[0]
        scores = self.emb @ q  # cosine similarity (vectors are normalized)
        idx = np.argsort(-scores)[: self.top_k]
        return [{**self.chunks[i], "score": round(float(scores[i]), 4)} for i in idx]

    def build_prompt(self, question, retrieved):
        context = "\n\n".join(f'[source: {r["source"]}]\n{r["text"]}' for r in retrieved)
        return PROMPTS[self.prompt_mode].format(context=context, question=question)

    def generate(self, prompt, retrieved):
        key = os.getenv("LLM_API_KEY")
        if not key:
            return "[MOCK MODE - no LLM_API_KEY] top chunk: " + retrieved[0]["text"]
        from openai import OpenAI
        client = OpenAI(api_key=key, base_url=os.getenv("LLM_BASE_URL") or None)
        resp = client.chat.completions.create(
            model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        return resp.choices[0].message.content.strip()

    def ask(self, question):
        retrieved = self.retrieve(question)
        prompt = self.build_prompt(question, retrieved)
        answer = self.generate(prompt, retrieved)
        return {"question": question, "retrieved": retrieved, "prompt": prompt, "answer": answer}


if __name__ == "__main__":
    import sys
    out = RAG().ask(" ".join(sys.argv[1:]) or "How long do I have to return an item?")
    for r in out["retrieved"]:
        print(r["score"], r["id"], "|", r["text"][:80])
    print("\nANSWER:", out["answer"])