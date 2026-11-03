# RAG Failure Analysis Report

## 1. Setup
- **Knowledge base:** 8 documents in `docs/` (fictional "NovaCart" store policies) with deliberate overlaps and conflicts:
  return policy 2024 vs archived 2022 FAQ (30 vs 14 days; 5-7 vs 10-day refunds), Plus membership vs 2025 blog
  ($9.99 vs $12.99; express shipping $12.99 vs $14.99), support hours vs 2025 blog (Mon-Fri 9-6 vs Mon-Sat 8-8),
  and gift-card return wording that overlaps with the returns docs.
- **Pipeline:** fixed word-window chunking (50 words / 10 overlap -> 16 chunks) -> all-MiniLM-L6-v2 embeddings ->
  cosine top-k (k=3) -> prompt with retrieved chunks -> LLM (`openai/gpt-oss-20b` via Groq, temperature 0).
- **Tests:** 11 questions: 3 supported, 2 unsupported, 2 ambiguous, 4 conflicting (`test_cases.py`).
- **Runs (7):** baseline (strict prompt), naive (naive prompt), topk5, bigchunks (120 words / 20 overlap -> 8 chunks),
  allcontext (all 8 docs in context, an oracle run), strict2 (improved `strict_v2` prompt) and strict2_all
  (`strict_v2` + all docs). Full traces are in `results/`.
- **Note on automatic flags:** the baseline, naive, topk5, bigchunks and allcontext runs used an earlier, weaker
  abstain/conflict regex in `run_tests.py`; strict2 and strict2_all used the corrected one. Conclusions below are
  based on reading the actual answers, not only the automatic flags.

## 2. Results summary
| Run | Supported (T1-T3) | Unsupported (T4-T5) | Ambiguous (T6-T7) | Conflicting (T8-T11) |
|-----|-------------------|---------------------|-------------------|----------------------|
| baseline (strict) | correct | abstained | T6 retrieval miss; T7 guessed | flagged conflict, no newer-source judgment |
| naive prompt | correct | no clean "I don't know" | T6 answered 30 days only; T7 guessed Plus price | conflicts not flagged (silent) |
| topk5 | same as baseline | same | T6 miss persists | same as baseline |
| bigchunks | same as baseline | same | T6 miss persists | same as baseline |
| allcontext | same | same | T6 correct facts (14/30/15/60) | same |
| strict_v2 (k=3) | correct | abstained | T6: confident "30 days", Plus doc still missing; T7: asks clarifying question | prefers newer source (T9: $12.99 current, $9.99 earlier) |
| strict_v2 + all docs | correct | abstained | T6: asks Plus/electronics clarification; T7: asks clarification | prefers newer value and mentions the older one (T8, T10, T11); T9 omits the older price |

Chunk size and top-k made no difference to any outcome. Only the prompt and (for T6) the full-context run did.

## 3. Failures

### Failure 1: T6, missed Plus return window (retrieval)
- **Question:** "How long do I have to return it?"
- **Retrieved (baseline):** 01_return_policy_2024#0 (0.557), 02_faq_returns_2022#1 (0.490), 02_faq_returns_2022#0 (0.485).
  Gold doc `04_plus_membership.md` never retrieved.
- **Answer:** baseline says it "cannot determine a single correct answer" (30 vs 14 days); naive says "30 days".
  Neither mentions the 60-day Plus window.
- **Root cause: retrieval.** The question nearly matches the 2022 FAQ's wording. In the allcontext run the Plus doc
  scored 0.124 (7th of 8), below unrelated docs, so no practical k fixes it. At 120-word chunks an unrelated
  warranty chunk (0.388) still outranked it.
- **Evidence:** hit=0 in baseline, naive, topk5 and bigchunks; with all docs in context (allcontext) the model
  correctly gave 14/30/15/60 days, so generation can handle it when retrieval succeeds.
- **Fix to try:** hybrid keyword + vector search, reranking, or query expansion ("return window membership").

### Failure 2: T7, vague question answered by guessing (generation)
- **Question:** "How much does it cost?" (no subject)
- **Retrieved (baseline):** 07_blog#1 (0.414), 07_blog#0 (0.408), 04_plus#0 (0.377), all low scores.
- **Answers:** naive confidently answered "$12.99 per month"; baseline listed the Plus price conflict;
  topk5 and bigchunks also added express shipping prices. None asked what "it" means.
- **Root cause: generation (prompt).** The strict prompt never allows a clarifying question, so the model
  picks or lists interpretations itself. Low retrieval scores were a warning no component used.
- **Fix tried: `strict_v2` prompt. Result: fixed.** In both strict2 and strict2_all, T7 asks "Could you clarify what
  you're asking about the cost of - NovaCart Plus membership, express shipping, or something else?" instead of
  guessing a price.

### Failure 3: T8-T11 under the naive prompt, silent conflict resolution (generation / context injection)
- **Evidence:** retrieval is identical between naive and baseline (same chunks and scores), but conflict-flag is 0
  for all four naive answers and 1 for all four strict answers.
- **Root cause:** context contains no dates or priority signal and the naive prompt has no conflict instruction,
  so the model picks one value without telling the user older documents disagree. In the strict baseline runs the
  model lists both values but does not say which is current (e.g. T9).
- **Naive answers pick different sources silently:** naive T10 gives only the newer hours (Mon-Sat 8-8) while naive T11
  gives only the 2024 refund time (5-7 days), with no mention of the conflicting document in either case. Which source
  wins varies between questions, so the behavior is unpredictable as well as invisible.
- **Fix tried: `strict_v2`.** It tells the model to name each source, prefer the newer one, and mention the older
  value. This worked on T8, T10 and T11 in both strict2 and strict2_all (e.g. T10: "Phone support is now available
  Mon-Sat 8-8 ... (Previously, it was Mon-Fri 9-6)"; T8: "The older 2022 policy allowed 14 days, but the 2024 return
  policy supersedes it"). The one exception is T9 in strict2_all, which gave only $12.99 and omitted the older price
  (see Failure 4). Note that the automatic conflict flag showed False for strict2_all T10 and T11 even though both
  answers mention the older value, because the regex does not match words like "previously" or "for reference".

### Failure 4: T9, outdated value labeled "current" (context injection: missing dates)
- **Question:** "How much is NovaCart Plus per month?"
- **Retrieval:** fine (04_plus#0 0.748, 07_blog#0 0.693) in baseline.
- **Answer (baseline, bigchunks, allcontext):** "The current price is $9.99... the blog states it will move to $12.99
  starting January 2025." The blog is already in effect, so $12.99 is the current price.
- **Root cause:** the model is not given today's date or document dates as metadata, so it cannot tell the blog
  supersedes the membership page. Ironically the naive run answered $12.99 (correct) while the stricter,
  more transparent prompt produced the mislabeled answer.
- **Fix tried: `strict_v2`. Result: partly fixed.** strict2 T9 answers "$12.99 currently; the earlier rate was
  $9.99" and labels the blog as newer. Caveat: this works because the prompt hardcodes "Today's date is November 2026",
  not because documents carry date metadata, so it is a patch, not a general solution. In strict2_all, T9 gave only
  $12.99 and dropped the older price and the "existing members keep their rate until renewal" detail (incomplete).

### Failure 5: T6 with `strict_v2`, a better prompt hides a retrieval miss (retrieval)
- **Question:** "How long do I have to return it?"
- **strict2 (k=3):** retrieved 01_return_policy_2024#0 (0.557), 02_faq_returns_2022#1 (0.490),
  02_faq_returns_2022#0 (0.485); `04_plus_membership.md` still missing (hit=False). Answer: "You have 30 days ... the
  older FAQ from 2022 stated a 14-day return window, but the most recent policy (March 2024) extends that to 30 days."
- **What went wrong:** the answer is clean and confident but omits the 15-day electronics window and the 60-day Plus
  window. The improved prompt resolved the old-vs-new conflict well, which makes the incomplete answer look complete.
- **Control:** with all documents in context (strict2_all) the model asked "Could you let me know if you're a NovaCart
  Plus member and whether the item is a standard product or an electronic?", which is the correct behavior.
- **Root cause: retrieval.** The Plus doc scored 0.124 for this query (7th of 8), below unrelated docs. No prompt can
  use context it never receives.
- **Caveat:** the all-documents run only works because the knowledge base is tiny (8 chunks); it does not scale.

### Minor observations
- T4/T5 (naive): the T4 answer begins "No - the available information does not mention..." and the leading "No"
  asserts something the documents never say. T5 correctly says the context does not mention the CEO.
- The early automatic abstain regex missed "does not mention" phrasing (naive T4/T5 showed abstain=False), so
  automatic metrics needed manual correction.
- Even with all docs in context under the strict prompt, T6 said the answer "depends on which policy is currently in
  effect" instead of using the "archived 2022" label; `strict_v2` was needed to resolve that.

## 4. Experiments
| Run | Change | Effect |
|-----|--------|--------|
| baseline | k=3, 50-word chunks, strict prompt | reference |
| naive | naive prompt | conflicts silent; T4/T5 no clean abstention |
| topk5 | k=5 | no change; T6 gold doc still missing |
| bigchunks | 120-word chunks (8 chunks) | no change; T6 gold doc still missing |
| allcontext | all 8 docs in context | T6 answered correctly -> proves retrieval was the cause |
| strict2 | `strict_v2` prompt (k=3) | T7 asks to clarify; T9 labels $12.99 as current; T6 still misses Plus doc and answers confidently |
| strict2_all | `strict_v2` + all docs | T6 asks the right clarifying question; T7 clarifies; T8, T10, T11 give the newer value and mention the older; T9 drops the older price |

## 5. Lessons
- Check retrieval before blaming the LLM: log chunk IDs and scores for every query.
- Raising k and chunk size did not fix a semantic-similarity miss.
- Prompts control abstention, conflict reporting and clarifying questions, but cannot supply missing context.
- A better prompt fixes generation failures (guessing, silent conflicts) but can make retrieval failures harder to
  notice, because the answer sounds more confident and complete.
- Conflicting documents need metadata (dates, version, status) in the retrieved context rather than relying on a
  hardcoded "today" in the prompt.
- Compare runs that share the same retrieval to isolate which pipeline stage is at fault.
- Automatic metrics are only a first filter; manual grading found errors in them.