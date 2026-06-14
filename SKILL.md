---
name: ielts-content
description: >
  Generate complete, exam-standard IELTS mock test content — passages, scripts, questions,
  and answer keys — for the Reading and Listening modules.
  Use this skill whenever the user asks to create, generate, or write any IELTS test content,
  question sets, passages, listening scripts, or answer keys. Also use when the user asks to QA,
  check, or validate existing IELTS content against official standards. Trigger even for partial
  requests like "write a Reading Passage 1" or "give me a Listening Part 2 script."
---

# IELTS Content Generation Skill

## How to Use This Skill

### ⚠ CRITICAL — Do NOT Skip These Steps

1. **Check topic availability FIRST** — before choosing any topic, run:
   ```bash
   python3 scripts/topic_tracker.py check "<your intended topic>"
   ```
   If BLOCKED, choose a different topic and check again. Only proceed once you get OK.

2. **Read the matching example file** — before generating anything.
   - Reading: `examples/reading/example.md`
   - Listening: `examples/listening/example.md`

3. **Read the module spec** from `references/` for whichever module you are generating.

4. **Plan your question types** — follow the coverage rule:
   - All non-matching question types must appear in the test.
   - Exactly ONE matching type per test (rotate: see spec).

5. Generate following the spec and example pattern exactly.

6. Run the QA checklist (at bottom of each module reference) before outputting anything.

7. Format output using the Answer Placement Format below.

8. **After output is accepted:**
   ```bash
   python3 scripts/topic_tracker.py log <generated-file.md>
   python3 scripts/validate.py <generated-file.md>
   ```

---

## ⚠ MATCHING RULE — The Most Important Structural Rule

### Reading
Choose exactly **ONE** of these three per test:
- Matching Headings
- Matching Features
- Matching Sentence Endings

### Listening
Choose exactly **ONE** of these two per test:
- Matching (General)
- Matching Features

**All other question types must all appear somewhere in the test.**
See `references/question-types.md` → Placement Master Table.

---

## Answer Placement Format — NON-NEGOTIABLE

```
[Question Set]
→ Questions only, no answers inline

[Answer Key for above set]
→ Question number | Answer | Needle (exact source sentence)

[Next Question Set]
→ ...
```

Never dump all answers at the end. Each question set gets its answer key immediately after it.

---

## The 4 Core Rules — Apply to Every Single Question

### Rule 1 — Progressive Difficulty
Passage 1 / Part 1 = accessible. Passage 3 / Part 4 = abstract and challenging. Never reverse.

### Rule 2 — Synonym Rule (No Word-Matching)
Question stems must NEVER repeat exact content words from the source.
The validator catches **3-gram AND 4-gram** content-word overlaps.
**Exception:** proper nouns and named entities (person names, place names, titles) must appear VERBATIM — never paraphrase them.
See `references/synonym-reference.md`.

| Source Says | Question Must Say |
|---|---|
| "constructed in 1842" | "erected during the nineteenth century" |
| "children showed reduced anxiety" | "young people experienced lower stress levels" |
| "Dr Sarah Chen argued" | "Dr Sarah Chen argued" ← keep proper nouns exact |

### Rule 3 — Distractor Requirement
Every question needs at least one distractor sourced from real passage content.
- **MCQ:** every wrong option must be eliminatable ONLY by reading the passage — never by general knowledge or common sense alone
- **Listening:** distractor spoken BEFORE the correct answer (self-correction trap)
- Never invent distractors — all wrong options must be traceable to a specific passage sentence

### Rule 4 — Needle Rule
Every answer must be provable by ONE specific sentence in the source.
If no single sentence proves it → rewrite the question.

---

## ⚠ COMPLETION SET RULES — Non-Negotiable

These apply to Note Completion, Sentence Completion, Table Completion, and Summary Completion:

1. **No duplicate answers** — no two questions in the same completion set may share the same answer, even partially. If Q8 = "three to four" then Q9 cannot also be "three to four".
2. **Answers must be verbatim** — copy the exact words from the source. Never paraphrase a completion answer.
3. **Word limit is absolute** — if the answer is 3 words and the limit is 2, rewrite the source sentence. Never exceed the stated limit.
4. **Chronological order** — completion questions must follow the order information appears in the source.

---

## ⚠ PASSAGE PROSE RULES — Apply Before Writing Any Passage

### Passage 1
- Write in **flowing prose only** — never stack attributes as list-like sentences.
- BAD: "It has a red bill, a black cap, a white body, and a wingspan of 80cm."
- GOOD: "The bird's predominantly white plumage is marked by a black cap, and its bill is a vivid red — features that make it immediately recognisable even at distance."
- Every paragraph must carry narrative momentum, not just deliver facts.

### Passage 2
- Every paragraph must contain at minimum: one claim + one piece of supporting evidence + one attributed expert or organisation.
- Thin paragraphs that consist only of summary statements will fail Cambridge standard.
- Each paragraph must have cause-effect texture: not just "X happens" but "X happens because Y, which leads to Z."

### Passage 3
- The writer must have a clear, traceable thesis stated in the first paragraph.
- The final paragraph must NOT simply restate what has already been argued. It must add the writer's qualified evaluation — acknowledging limits, open questions, or implications not yet explored.
- Use nominalisation, hedging, and complex subordination throughout.

---

## ⚠ NOT GIVEN / NOT GIVEN Quality Rule

A NOT GIVEN statement must:
1. Be on a topic that **is discussed** in the passage — not on something completely absent or obviously invented.
2. Be neither confirmed nor contradicted by any sentence in the passage.
3. Be **plausible enough** that a careless reader might mark it TRUE or FALSE.

**Bad NOT GIVEN:** "Arctic terns eat squid." (squid never mentioned — too easy to spot)
**Good NOT GIVEN:** "Arctic terns undertake their first migration alone, without guidance from adult birds." (plausible, passage discusses solo navigation but never confirms or denies whether juveniles travel alone)

---

## Generation Workflow

**Reading:** all 3 passages + 40 questions at once.
**Listening:** all 4 parts + 40 questions at once.

```
1. Check topic (topic_tracker.py check) — REQUIRED
2. Choose topics from spec topic bank
3. Decide which matching type to use this test (rotate)
4. Write ALL source content FIRST
   → Embed distractors and traps before writing questions
   → Apply Passage Prose Rules above to every paragraph
5. Draft ALL questions
   → Confirm every non-matching type is covered
   → Confirm only one matching type is used
   → Confirm no duplicate answers in any completion set
   → Confirm every NOT GIVEN arises from near-miss content
   → Confirm every MCQ distractor requires passage reading to eliminate
6. Confirm every answer has a Needle
7. Run QA checklist from module spec
8. Format using Answer Placement Format
9. After acceptance: topic_tracker.py log + validate.py
```

---

## Module Reference Files

| Module | Reference File | Example File |
|---|---|---|
| Reading | `references/reading-spec.md` | `examples/reading/example.md` |
| Listening | `references/listening-spec.md` | `examples/listening/example.md` |
| Question Types | `references/question-types.md` | — |
| Synonyms | `references/synonym-reference.md` | — |
| Topic Bank | `references/topic-bank.md` | — |
| Used Topics | `references/used-topics.json` | (auto-maintained) |

---

## Hard Placement Rules — Never Violate

| Rule | Detail |
|---|---|
| Yes/No/Not Given | NEVER in Passage 1 |
| True/False/Not Given | NEVER in Passage 3 |
| Note Completion | Part 1 is always Note Completion |
| Academic Attribution | ONLY in Listening Part 4 |
| Matching types | MAXIMUM ONE per test |

---

## Common AI Failures — NEVER Do These

| Failure | Fix |
|---|---|
| Duplicate answers in a completion set | Check every answer in the set against all others before finalising |
| List-stacking in Passage 1 prose | Rewrite as flowing narrative — every sentence must connect to the next |
| Thin P2 paragraphs (summary-only) | Add evidence + expert attribution + cause-effect to every paragraph |
| P3 conclusion restates the thesis | Add qualified evaluation, open questions, or unexplored implications |
| NOT GIVEN on an obviously absent topic | Choose a topic the passage discusses but leaves unresolved |
| MCQ distractor eliminatable by common sense | Source every wrong option from a specific passage sentence |
| Paraphrasing proper nouns in question stems | Keep all names, titles, and place names exactly as in the passage |
| Two matching types in one test | Remove one — keep only the planned matching type |
| Answer requires two sentences to prove | Rewrite question — one Needle only |
| Part 4 researcher names sound similar | Use phonetically distinct names |
| Repeat topic from previous test | Run topic_tracker.py check first |
