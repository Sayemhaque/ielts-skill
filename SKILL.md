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

2. **Determine category rotation for hardest passage/part** — topic diversity at the advanced level:
   - **Reading Passage 3** — run:
     ```bash
     python3 scripts/topic_tracker.py get_reading_p3_category
     ```
     Select a topic from the returned category only.
   - **Listening Part 4** — run:
     ```bash
     python3 scripts/topic_tracker.py get_listening_p4_category
     ```
     Select a topic from the returned category only.

3. **Read the matching example file** — before generating anything. The example in `examples/` is the single source of truth for format, structure, and quality.
   - Reading: `examples/reading/example.md`
   - Listening: `examples/listening/example.md`

4. **Read the module spec** from `references/` for whichever module you are generating.

5. **Plan your question types** — follow the coverage rule:
   - All non-matching question types must appear in the test.
   - Exactly ONE matching type per test (rotate: see spec).

6. Generate following the spec and example pattern exactly.

7. Run the QA checklist (at bottom of each module reference) before outputting anything.

8. Format output following the Answer Placement Format below.

9. **After output is accepted** — log topics, category usage, and validate:
   ```bash
   python3 scripts/topic_tracker.py log <generated-file.md>
   python3 scripts/topic_tracker.py log_reading_p3_category  # if Reading
   python3 scripts/topic_tracker.py log_listening_p4_category  # if Listening
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
See `references/question-types.md` → Placement Master Table for the full required list.

---

## Answer Placement Format — NON-NEGOTIABLE

Structure every test output as:

```
[Question Set]
→ Questions only, no answers inline

[Answer Key for above set]
→ Question number | Answer | Needle (exact source sentence that proves it)

[Next Question Set]
→ Questions only

[Answer Key for above set]
→ ...
```

Never dump all answers at the end of the full test. Each question set gets its answer key immediately after it.

---

## The 4 Core Rules — Apply to Every Single Question

### Rule 1 — Progressive Difficulty
Passage 1 / Part 1 = accessible. Passage 3 / Part 4 = abstract and challenging. Never reverse.

### Rule 2 — Synonym Rule (No Word-Matching)
Question stems must NEVER repeat exact words from the source text or script.
Always paraphrase. The validator catches **3-gram AND 4-gram** content-word overlaps.
See `references/synonym-reference.md` for synonym pairs.

| Source Says | Question Must Say |
|---|---|
| "constructed in 1842" | "erected during the nineteenth century" |
| "children showed reduced anxiety" | "young people experienced lower stress levels" |
| "sleep deprivation impairs consolidation" | "insufficient rest damages the brain's ability to retain information" |

### Rule 3 — Distractor Requirement
Every question needs at least one distractor — real information from the source that looks like the answer but isn't.
- Must be actually present in the source — never invented
- Must be eliminated by careful reading/listening, not guessing
- For Listening: spoken BEFORE the correct answer (self-correction trap)

### Rule 4 — Needle Rule
Every answer must be provable by ONE specific sentence in the source.
Ask: *"Can I underline the exact line that proves this answer?"*
If no → rewrite the question. No exceptions.

---

## Generation Workflow

Generate a complete test in a single output. Do NOT generate passages/parts individually.

**Reading:** all 3 passages + 40 questions at once.
**Listening:** all 4 parts + 40 questions at once.

```
1. Check topic availability (topic_tracker.py check) — REQUIRED
2. Get category rotation for Passage 3 / Part 4 (run get_reading_p3_category / get_listening_p4_category)
3. Choose topics / contexts from the module spec
4. Decide which matching type to use this test (rotate)
5. Write ALL source content FIRST (3 passages / 4 scripts)
   → Embed distractors and traps BEFORE writing questions
6. Draft ALL questions — apply Synonym Rule to every stem
   → Confirm every non-matching type is covered
   → Confirm only one matching type is used
7. Confirm every answer has a Needle
8. Run the module QA checklist
9. Format output using Answer Placement Format
10. After acceptance: run topic_tracker.py log, log_reading_p3_category / log_listening_p4_category, then validate.py
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
| Used Topics | `references/used-topics.json` | (auto-maintained by topic_tracker.py) |
| Category Rotation | `references/usage-state.json` | (auto-maintained by topic_tracker.py) |

---

## Hard Placement Rules — Never Violate

| Rule | Detail |
|---|---|
| Yes/No/Not Given | NEVER in Reading Passage 1 |
| True/False/Not Given | NEVER in Reading Passage 3 |
| Note Completion | Part 1 is always Note Completion |
| Academic Attribution | ONLY in Listening Part 4 |
| Matching types | MAXIMUM ONE per test |

---

## Common AI Failures — NEVER Do These

| Failure | Why It Fails | Fix |
|---|---|---|
| Using two matching types in one test | Violates the matching rule | Pick one and use it consistently across the whole test |
| Skipping a non-matching question type | Every type must appear | Plan the type coverage before writing any questions |
| Passage uses opinions in Passage 1 | Passage 1 must be purely factual | Rewrite — no opinions, no writer's voice |
| Matching Features entities not named in text | AI invents opinions not actually stated | Every entity must have a direct quote in the passage |
| Topic too technical or niche | Not standard IELTS | Use topic-bank.md — pick from approved categories only |
| NOT GIVEN when text actually discusses the topic | Careless reading | Search the entire passage, not just nearby sentences |
| Listening dialogue sounds robotic | Unnatural phrasing | Write naturally: "And when were you born?" not "Please provide your date of birth" |
| Question stem copies passage wording | Violates Synonym Rule — caught at 3-gram level | Change 80% of the words in every stem |
| Passage 3 uses simple vocabulary | Must match academic register | Use nominalisation, hedging, complex structures |
| Part 4 lecture has opinion language | Lectures present findings, not personal views | "Studies show..." not "I believe..." |
| Repeat topic from previous test | Reduces exam realism | Always run topic_tracker.py check before choosing |
| Passage 3 category repeats | Reduces topic diversity across tests | Run get_reading_p3_category before choosing |
| Part 4 category repeats | Reduces topic diversity across tests | Run get_listening_p4_category before choosing |
| Passage 3 lacks academic vocabulary | FRE > 50 means too easy | Aim for FRE < 40; use nominalisation, hedging, complex clauses |
| Part 4 too simple | FRE > 50 means not academic enough | Use complex sentence structures, academic attribution, signpost language |

---

## Common Mistakes — Check Before Output

| Mistake | Fix |
|---|---|
| Two matching types in one test | Remove one — keep only the planned matching type |
| A question type missing from the test | Add it; consult question-types.md for placement rules |
| Same words in question as source | Remap every stem with synonyms |
| FALSE when text just doesn't mention it | Only FALSE if text directly contradicts |
| Gap answer exceeds word limit | Rewrite sentence so answer fits |
| Distractor is obviously wrong | Use real source info, make it plausible |
| Part 4 researcher names sound similar | Use phonetically distinct names |
| Answer needs two sentences to prove | Rewrite — one Needle only |
| Matching word list has too few options | At least 2 extra options beyond number of questions |
| T/F/NG set has fewer than 2 NOT GIVEN | Add genuinely absent claims |
| Topic already used in a previous test | Check used-topics.json; if similar — pick something else |
