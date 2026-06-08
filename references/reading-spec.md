# Reading Module Specification

## Overview
- 3 passages, increasing difficulty
- ~2,500 words total
- 40 questions total
- 60 minutes (students self-allocate)
- Official-style output: paraphrased stems, fair distractors, unambiguous answers, no end-of-test answer dump

---

## Official-Style Reading Standard

Use these checks as the quality bar for every generated Reading test:

| Area | Standard |
|---|---|
| Passage authenticity | Neutral IELTS-like topics from `topic-bank.md`; no highly specialised research, politics, or culture-specific assumptions |
| Question wording | Stems must paraphrase the source; avoid copying 4+ consecutive content words from the answer sentence |
| Skill tested | Questions should test locating, comparison, inference, writer view, and text organisation; avoid pure word matching |
| Distractors | Wrong MCQ/matching options must be real source details that are wrong for a specific reason |
| Answer order | Completion and T/F/NG or Y/N/NG questions should normally follow passage order |
| Ambiguity | One answer only; if two source lines could support different answers, rewrite the item |
| NOT GIVEN | The exact claim must be absent. Do not use NOT GIVEN when the passage implies or contradicts the statement |
| Needles | TRUE/FALSE/YES/NO/MCQ/completion need one exact supporting sentence; NOT GIVEN needs a precise absence note |

**Question rewrite rule:** after drafting, compare each item to its source sentence. If the stem repeats the same key nouns and verbs, rewrite with synonyms, changed syntax, or a broader paraphrase.

## Passage 1 — Factual / Descriptive

| Parameter | Specification |
|---|---|
| Word Count | 700–800 words |
| Topic | Historical accounts, descriptive science, natural world, processes |
| Tone | Neutral, factual — no opinions, no arguments |
| Vocabulary | Accessible (Band 5.5–6.5) |
| Questions | 13–14 across at least 3 different types |

**Required types (use at least 3):**
- True / False / Not Given — 6–7 statements; at least 2 TRUE, 2 FALSE, 2 NOT GIVEN
- Note / Sentence / Summary Completion — max 2 words per gap; answers verbatim from text
- Table Completion or Matching Features

**Writing rules:**
- Facts only. No opinions, no arguments.
- Short-to-medium sentences. Avoid complex subordinate clauses.
- At least one concrete example or statistic per paragraph.
- T/F/NG statements should include at least two tempting traps: wrong period, wrong quantity, wrong origin, or over-generalised claim.
- Completion/table answers must be short, concrete, and exactly copied from the passage.

**Structure template (5 paragraphs):**
| Para | Purpose | Content |
|---|---|---|
| 1 | Introduction | Define the subject, give brief historical/origin context |
| 2 | Key details 1 | Core factual information about the subject |
| 3 | Key details 2 | Process, mechanism, or secondary aspect |
| 4 | Significance | Practical importance or modern relevance |
| 5 | Conclusion | Current status, summary statistic, or future outlook |

**Permitted:** True / False / Not Given · Table Completion · Sentence Completion · Matching Features · Note Completion · Summary Completion (From Text) · Summary Completion (From List)
**Avoid:** Yes / No / Not Given · Matching Headings · Multiple Choice

---

## Passage 2 — Discursive / Social

| Parameter | Specification |
|---|---|
| Word Count | 800–850 words |
| Topic | Social trends · urban issues · education · technology in society · environment |
| Tone | Balanced — multiple viewpoints; at least one counterargument |
| Vocabulary | Intermediate–Advanced (Band 6.0–7.0) |
| Questions | 13–14 across at least 3 different types |

**Required types (use at least 3):**
- Matching Headings — match headings to paragraphs; at least 2 extra headings
- Matching Features — match experts/organisations to stated opinions
- Sentence Completion — NO MORE THAN TWO WORDS from the passage

**Writing rules:**
- At least 2 named experts or organisations with distinct, attributable opinions.
- Each paragraph carries a distinct sub-theme.
- Use hedging: "suggests," "appears to indicate," "according to."
- Include at least one counterargument paragraph.
- Label paragraphs A–F.
- Matching Headings must test paragraph purpose, not a single detail.
- Matching Features must include at least 2 extra options where practical, and every option must be named in the passage.

**Structure template (6 paragraphs, A–F):**
| Para | Purpose | Content |
|---|---|---|
| A | Introduction | Present the issue — multiple approaches exist |
| B | Viewpoint 1 | First approach with expert/organisation support |
| C | Viewpoint 2 | Second approach with different expert/organisation support |
| D | Counterargument | Opposing view or limitation of above approaches |
| E | Further complexity | Additional factor, debate, or emerging trend |
| F | Conclusion | Synthesis — no single solution, integrated approach needed |

**Permitted:** Matching Headings · Matching Features · Matching Sentence Endings · Summary Completion (From Text) · Summary Completion (From List) · Multiple Choice (Single) · Sentence Completion · Table Completion · Note Completion
**Avoid:** True / False / Not Given (unless writer's view is very prominent)

---

## Passage 3 — Analytical / Abstract

| Parameter | Specification |
|---|---|
| Word Count | 900+ words |
| Topic | Philosophy · cognitive science · psychology · complex academic argument |
| Tone | Academic, argumentative, nuanced — writer must have a clear traceable thesis |
| Vocabulary | Advanced (Band 7.0–8.0+) |
| Questions | 13–14 across at least 3 different types |

**Required types (use at least 3):**
- Yes / No / Not Given — tests WRITER'S OPINION only
- Multiple Choice (Single) — tests inference and global understanding
- Summary / Note Completion with academic vocabulary

**Writing rules:**
- Writer must have a clear, traceable argument or thesis.
- Use complex sentences, nominalisation, hedged academic claims.
- Include at least one named theory, study, or framework.
- Use nuanced language: "this may partly account for," "one interpretation holds that."
- Keep the argument readable: abstract but not overloaded with named researchers or technical terms.
- MCQs should test global purpose, inference, function of examples, or the writer's evaluation, not isolated facts.

**Structure template (6 paragraphs):**
| Para | Purpose | Content |
|---|---|---|
| 1 | Thesis | Introduce the hard problem / debate, state writer's position |
| 2 | Theory 1 | Present first theory/framework with supporting evidence |
| 3 | Evidence | Study or experimental support for the theory |
| 4 | Criticism | Opposing view or limitation of the theory |
| 5 | Alternative | Different perspective or counter-framework |
| 6 | Evaluation | Writer's final assessment — strengths vs limitations |

**Permitted:** Yes / No / Not Given · Multiple Choice (Single) · Multiple Choice (Multiple) · Summary Completion (From Text) · Summary Completion (From List) · Matching Features · Matching Sentence Endings
**Avoid:** Table Completion · True / False / Not Given

---

## Markdown Format Template — Copy This Structure

Every reading test must follow this exact heading hierarchy and section order. AI must read the example in `examples/reading/example.md` before generating, but this template shows the bare skeleton.

```markdown
# IELTS Academic Reading — Full Practice Test

**Time:** 60 minutes | **Questions:** 40

---

## READING PASSAGE 1

*You should spend about 20 minutes on Questions 1–13, which are based on Reading Passage 1 below.*

### The Passage Title Here

Passage text goes here — 5 paragraphs, 700–800 words, factual only. No opinions. See structure template above.

---

### Questions 1–7

[Question type instructions — e.g., TRUE / FALSE / NOT GIVEN]

1. Statement one.
2. Statement two.
...

---

### Questions 8–13

[Question type instructions]

8. ________
...

---

### Answer Key — Questions 1–7

| Q | Answer | Needle |
|---|--------|--------|
| 1 | TRUE | "exact sentence from passage" |

---

### Questions 8–13

[Question type instructions]

8. ________
...

---

### Answer Key — Questions 8–13

| Q | Answer | Needle |
|---|--------|--------|
| 8 | answer | "exact sentence from passage" |

---

## READING PASSAGE 2

*You should spend about 20 minutes on Questions 14–26, which are based on Reading Passage 2 below.*

### A

Passage text — label paragraphs A–F. 800–850 words. Multiple viewpoints.

### B
...

---

### Questions 14–19

[List of Headings — Heading i, ii, iii...]

14. Paragraph A
15. Paragraph B
...

---

### Questions 20–23

[Match each statement with the correct person...]

---

### Questions 24–26

[Complete the sentences below...]

---

### Answer Key — Questions 14–19

| Q | Answer | Needle |
|---|--------|--------|

---

### Questions 20–23

[Match each statement with the correct person...]

---

### Answer Key — Questions 20–23

| Q | Answer | Needle |
|---|--------|--------|

---

### Questions 24–26

[Complete the sentences below...]

---

### Answer Key — Questions 24–26

| Q | Answer | Needle |
|---|--------|--------|

---

## READING PASSAGE 3

*You should spend about 20 minutes on Questions 27–40, which are based on Reading Passage 3 below.*

### The Passage Title Here

Passage text — 900+ words. Writer must have a clear thesis.

---

### Questions 27–32

[YES / NO / NOT GIVEN]

---

### Questions 33–35

[Multiple Choice]

---

### Questions 36–40

[Summary Completion]

---

### Answer Key — Questions 27–32

| Q | Answer | Needle |
|---|--------|--------|

---

### Questions 33–35

[Multiple Choice]

---

### Answer Key — Questions 33–35

| Q | Answer | Needle |
|---|--------|--------|

---

### Questions 36–40

[Summary Completion]

---

### Answer Key — Questions 36–40

| Q | Answer | Needle |
|---|--------|--------|
```

**Critical format rules:**
- `## READING PASSAGE N` — level 2 heading for each passage
- `### Title / A` — level 3 heading for passage title or paragraph label
- `### Questions N–M` — level 3 heading, en-dash between numbers
- `### Answer Key — Questions N–M` — level 3 heading
- Questions numbered sequentially across the whole test (1–40)
- Each question set followed immediately by its answer key
- `---` horizontal rule between sections

---

## QA Checklist — Run Before Output

- 40 questions exactly; ranges are continuous and non-overlapping.
- Every question set is followed immediately by its matching answer key.
- Passage 1 uses T/F/NG plus completion/table-style questions; no Y/N/NG.
- Passage 2 uses Matching Headings, Matching Features, and completion or equivalent.
- Passage 3 uses Y/N/NG, MCQ, and summary/note completion; no T/F/NG.
- Matching lists include at least two extra options unless the official-style format genuinely requires otherwise.
- MCQ distractors are source-based and plausible.
- No completion answer breaks the stated word limit.
- Each answer has one needle; NOT GIVEN has an absence note, not a fake quote.
- Stems are paraphrased from answer sentences.
