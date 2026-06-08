---
name: ielts-content
description: >
  Generate complete, exam-standard IELTS mock test content — passages, scripts, questions,
  answer keys, and model answers — for all four modules: Reading, Listening, Writing, and Speaking.
  Use this skill whenever the user asks to create, generate, or write any IELTS test content,
  question sets, passages, listening scripts, writing tasks, speaking cue cards, model answers,
  or answer keys. Also use when the user asks to QA, check, or validate existing IELTS content
  against official standards. Trigger even for partial requests like "write a Reading Passage 1"
  or "give me a Listening Part 2 script."
---

# IELTS Content Generation Skill

## How to Use This Skill

1. **Read this file** — core rules and generation workflow
2. **Read the module spec** from `references/` for whichever module you are generating
3. **Read the matching example** from `examples/` before generating — examples are the standard
4. **Generate** original content following the spec and example pattern exactly
5. **Run the QA checklist** (at bottom of each module reference) before outputting anything
6. **Format output** following the Answer Placement Format below

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

For every piece of content, follow this order:

```
1. Choose topic / context from the module spec
2. Write source content FIRST (passage / script)
   → Embed distractors and traps BEFORE writing questions
3. Draft questions — apply Synonym Rule to every stem
4. Confirm every answer has a Needle
5. For Listening Part 2 / Reading Passage 1 visuals:
   → Complete Spatial Mapping Grid (see references/spatial-mapping-grid.md)
6. Run the module QA checklist
7. Format output using Answer Placement Format
```

---

## Module Reference Files

Read the relevant file before generating:

| Module | Reference File | Example File |
|---|---|---|
| Reading | `references/reading-spec.md` | `examples/reading/passage1-example.md` |
| Listening | `references/listening-spec.md` | `examples/listening/part1-example.md` |
| Writing | `references/writing-spec.md` | `examples/writing/task1-example.md` |
| Speaking | `references/speaking-spec.md` | `examples/speaking/part2-example.md` |
| Question Types | `references/question-types.md` | — |
| Synonyms | `references/synonym-reference.md` | — |
| Spatial Mapping | `references/spatial-mapping-grid.md` | `examples/listening/part2-spatial-grid-example.md` |

---

## Hard Placement Rules — Never Violate

| Rule | Detail |
|---|---|
| Yes/No/Not Given | NEVER in Reading Passage 1 |
| True/False/Not Given | NEVER in Reading Passage 3 |
| Map Labelling | ONLY in Listening Part 2 |
| Form Completion | ONLY in Listening Part 1 |
| Academic Attribution | ONLY in Listening Part 4 |

---

## Common Mistakes — Check Before Output

| Mistake | Fix |
|---|---|
| Same words in question as source | Remap every stem with synonyms |
| FALSE when text just doesn't mention it | Only FALSE if text directly contradicts |
| Map and script directions disagree | Complete Spatial Mapping Grid first |
| Gap answer exceeds word limit | Rewrite sentence so answer fits |
| Distractor is obviously wrong | Use real source info, make it plausible |
| Part 4 researcher names sound similar | Use phonetically distinct names |
| Answer needs two sentences to prove | Rewrite — one Needle only |