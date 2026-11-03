p = "rag.py"
s = open(p, encoding="utf-8").read()
if "strict_v2" in s:
    print("already patched")
else:
    entry = r'''    "strict_v2": (
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
'''
    new = s.replace("PROMPTS = {\n", "PROMPTS = {\n" + entry, 1)
    assert new != s, "could not find PROMPTS = { in rag.py"
    open(p, "w", encoding="utf-8").write(new)
    print("patched OK")
