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

### ⚠ CRITICAL — Do NOT Skip Step 1

1. **Read the matching example file FIRST** — before reading anything else, before generating anything. The example in `examples/` is the single source of truth for format, structure, and quality.
   - Reading: `examples/reading/example.md` (340 lines)
   - Listening: `examples/listening/example.md` (480 lines)
   - If you skip this step, your output will have structural errors.

2. Read the module spec from `references/` for whichever module you are generating
3. Generate following the spec and example pattern exactly
4. Run the QA checklist (at bottom of each module reference) before outputting anything
5. Format output following the Answer Placement Format below

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
Always paraphrase. See `references/synonym-reference.md` for synonym pairs.

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
1. Choose topics / contexts from the module spec
2. Write ALL source content FIRST (3 passages / 4 scripts)
   → Embed distractors and traps BEFORE writing questions
3. Draft ALL questions — apply Synonym Rule to every stem
4. Confirm every answer has a Needle
5. Run the module QA checklist
6. Format output using Answer Placement Format
```

---

## Module Reference Files

Read the relevant file before generating:

| Module | Reference File | Example File |
|---|---|---|
| Reading | `references/reading-spec.md` | `examples/reading/example.md` |
| Listening | `references/listening-spec.md` | `examples/listening/example.md` |
| Question Types | `references/question-types.md` | — |
| Synonyms | `references/synonym-reference.md` | — |
| Topic Bank | `references/topic-bank.md` | — |

---

## Hard Placement Rules — Never Violate

| Rule | Detail |
|---|---|
| Yes/No/Not Given | NEVER in Reading Passage 1 |
| True/False/Not Given | NEVER in Reading Passage 3 |
| Note Completion | ONLY in Listening Part 1 |
| Academic Attribution | ONLY in Listening Part 4 |

---

## Common AI Failures — NEVER Do These

| Failure | Why It Fails | Fix |
|---|---|---|
| Passage uses opinions/arguments in Passage 1 | Passage 1 must be purely factual | Rewrite — no opinions, no writer's voice |
| Matching Features entities are not named in the text | AI invents opinions not actually stated | Every entity must have a direct quote in the passage |
| Topic is too technical or niche | Wind turbines, AI algorithms — not standard IELTS | Use topic-bank.md — pick from approved categories only |
| NOT GIVEN when text actually discusses the topic | AI assumes not mentioned without checking thoroughly | Search the entire passage, not just nearby sentences |
| Listening dialogue sounds robotic | "Could you please provide your date of birth?" | Write naturally: "And when were you born?" |
| Part 1 dialogue is symmetrical (equal turns) | Real conversations have one speaker driving | Official asks most questions; customer gives short answers |
| MCQ distractors are invented | Wrong options must come from the source text | Every distractor must be traceable to a real sentence |
| Question stem copies passage wording exactly | Violates Synonym Rule | Read each stem → find the source sentence → change 80% of the words |
| Passage 3 summary uses simple vocabulary | Must match academic register | Use nominalisation, hedging, complex structures |
| Part 4 lecture has opinion language | Lectures present research findings, not personal views | "Studies show..." not "I believe..." |

---

## Common Mistakes — Check Before Output

| Mistake | Fix |
|---|---|
| Same words in question as source | Remap every stem with synonyms |
| FALSE when text just doesn't mention it | Only FALSE if text directly contradicts |
| Gap answer exceeds word limit | Rewrite sentence so answer fits |
| Distractor is obviously wrong | Use real source info, make it plausible |
| Part 4 researcher names sound similar | Use phonetically distinct names |
| Answer needs two sentences to prove | Rewrite — one Needle only |
| Matching Features word list has too few options | At least 2 extra options beyond number of questions |