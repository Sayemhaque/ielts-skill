# Listening Module Specification

## Overview
- 4 parts, increasing complexity
- 40 questions total (10 per part)
- Audio plays ONCE only — no pause, rewind, replay
- 30 seconds pre-listening per part (read questions)
- 30 seconds post-listening per part (check answers)

---

## ⚠ MATCHING RULE — Read Before Planning Questions

Each Listening test must use **exactly ONE** of these two matching types:
- Matching (General) — typically Part 2
- Matching Features — typically Part 3 or 4

All other question types (non-matching) **must all appear** in every test.
Never use both matching types in the same test.

**Rotate the matching type across tests:**
- Test 1 → Matching (General)
- Test 2 → Matching Features
- Test 3 → Matching (General) (cycle repeats)

---

## Required Question Type Coverage Per Test

All of the following must appear in every Listening test:

| # | Type | Part |
|---|---|---|
| 1 | Note Completion | Part 1 (required) |
| 2 | Multiple Choice (Single) | Part 2–4 |
| 3 | Multiple Choice (Multiple) | Part 2–4 |
| 4 | Table Completion | Part 3–4 |
| 5 | Sentence Completion | Part 3–4 |
| 6 | Summary Completion | Part 3–4 |
| 7 | **ONE matching type** (rotate per test) | Part 2–4 |

---

## Part 1 — Everyday Social Dialogue

| Parameter | Specification |
|---|---|
| Format | Conversation between 2 people |
| Context | Booking accommodation · enrolling in a course · reporting a problem · making a reservation |
| Primary Task | Note Completion (form filling) |
| Difficulty | Accessible (Band 4.5–6.0) |
| Script Length | 250–300 words spoken |

**Mandatory script features — ALL THREE required:**
- **SPELLING TRAP:** One speaker spells out a name/address letter by letter (e.g., "that's K-O-W-A-L-C-Z-Y-K")
- **SELF-CORRECTION:** One speaker changes a detail just given (e.g., "the 14th... no wait, it's the 15th")
- **DISTRACTOR:** An incorrect option mentioned then clearly discarded before correct answer confirmed. The wrong option MUST be spoken BEFORE the correct answer — never after. The listener must hear the distractor first, then hear it rejected, then hear the correct answer.

**Structure template:**
| Turn | Speaker | Purpose | Trap |
|---|---|---|---|
| 1 | Official | Greeting + ask for first detail | — |
| 2 | Customer | Answer + give name to spell | SPELLING TRAP |
| 3 | Official | Confirm detail + ask next | — |
| 4 | Customer | Answer with number/date → self-correct | SELF-CORRECTION |
| 5 | Official | Ask next detail | — |
| 6–8 | Both | Exchange remaining details | DISTRACTOR (wrong option mentioned, then rejected) |
| 9–10 | Both | Confirm final details + closing | — |

**Note completion rules:**
- Answers must be factual: names, dates, numbers, times, places
- Word limit: NO MORE THAN TWO WORDS AND/OR A NUMBER
- Questions follow chronological order of script

---

## Part 2 — Everyday Social Monologue

| Parameter | Specification |
|---|---|
| Format | One speaker presenting practical information |
| Context | Tour of a facility · local radio announcement · community event briefing |
| Primary Task | Multiple Choice (Single) — 5 questions |
| Secondary Task | Matching (General) OR Note/Table Completion — 5 questions |
| Difficulty | Moderate (Band 5.5–6.5) |
| Script Length | 350–400 words spoken |

If this test's chosen matching type is **Matching (General)**, place it here as the secondary task.
If this test's chosen matching type is **Matching Features**, use Note Completion or Table Completion here instead.

**Script structure:**
| Section | Content | Questions |
|---|---|---|
| Opening | Speaker introduces themselves, welcomes audience, states purpose | — |
| Background | Brief history or context of the venue/topic | MCQ 1 |
| Key details | Facilities, opening times, services, practical info | MCQ 2–3 |
| Directions/Locations | Description of where things are located | Matching / Note Qs |
| Closing | Final instructions, thanks, next steps | MCQ 4–5 |

---

## Part 3 — Academic Discussion

| Parameter | Specification |
|---|---|
| Format | 2–3 speakers (students + tutor, or research partners) |
| Context | Discussing research project · reviewing assignment · planning presentation |
| Primary Task | Multiple Choice (Multiple Answers) — 5 questions |
| Secondary Task | Table Completion OR Sentence Completion OR Matching Features — 5 questions |
| Difficulty | Challenging (Band 6.0–7.5) |
| Script Length | 400–450 words spoken |

If this test's chosen matching type is **Matching Features**, place it here as the secondary task (match researchers/studies to findings discussed in the conversation).

**Mandatory script features:**
- **AGREEMENT & DISAGREEMENT TRACKING:** Script clearly shows agreeing, partially agreeing, disagreeing
- **SPEAKER ATTRIBUTION:** Every matched statement said by a specific named speaker — never ambiguous
- **HEDGED LANGUAGE:** "I'm not entirely convinced," "That's a fair point, but...," "I'd argue that..."
- **OPINION CHANGE:** At least one speaker changes or softens their view

**Script structure:**
| Section | Content | Questions |
|---|---|---|
| Opening | Tutor sets agenda, asks for update | — |
| Topic selection | Students discuss focus, disagree → one convinces the other | MCQ Multiple 1–2 |
| Methodology | Debate on research methods, agreement/rejection | MCQ Multiple 3–4 |
| Concerns | Practical concerns raised, solutions offered | MCQ Multiple 5 |
| Guidance | Tutor gives timeline/methodology advice | Table / Sentence / Matching Qs |
| Closing | Summary of decisions, next steps | — |

---

## Part 4 — Academic Lecture

| Parameter | Specification |
|---|---|
| Format | Single academic speaker, no interruptions |
| Context | University lecture — science · history · social science · research findings |
| Primary Task | Note Completion + Summary Completion |
| Secondary Task | Sentence Completion |
| Difficulty | Most challenging (Band 7.0–8.5) |
| Script Length | 800–900 words spoken (~6 minutes) |

**Mandatory script features:**
- **HIGH-LEVEL SYNONYMS:** Script uses advanced vocabulary; questions use paraphrases. Synonym Rule critical here.
- **ACADEMIC ATTRIBUTION:** At least 3 named researchers/institutions, each attributed to a distinct finding. Use phonetically distinct names.
- **SIGNPOST LANGUAGE:** "Turning now to...," "What is particularly noteworthy is...," "This brings us to the question of..."
- **LOGICAL STRUCTURE:** Cause → effect, problem → solution, or chronological

**Note completion rules:**
- Answers: NO MORE THAN TWO WORDS (or ONE WORD AND/OR A NUMBER — specify clearly)
- Questions follow exact chronological order of the lecture
- Test key ideas only — not minor details

---

## Markdown Format Template — Copy This Structure

Every listening test must follow this exact heading hierarchy and section order. AI must read the example in `examples/listening/example.md` before generating, but this template shows the bare skeleton.

```markdown
# IELTS Academic Listening — Full Practice Test

**Time:** Approximately 30 minutes | **Questions:** 40

---

## LISTENING PART 1

*You will hear a conversation between a [role] and a [role].*
*First, you have 30 seconds to read Questions 1–10.*

### Questions 1–10
Complete the notes below.
Write **NO MORE THAN TWO WORDS AND/OR A NUMBER** for each answer.

| | |
|---|---|
| **Field:** | (1) ______ |
...

### Script: Part 1
[dialogue]

### Answer Key — Questions 1–10
| Q | Answer | Needle |
|---|--------|--------|
**Mandatory traps used:** Spelling: Q? — Self-correction: Q? — Distractor: Q?

---

## LISTENING PART 2

*You will hear a [role] speaking to [audience].*
*First, you have 30 seconds to read Questions 11–20.*

### Questions 11–15
Choose the correct letter, A, B, or C.

### Questions 16–20
[Matching (General) OR Note/Table Completion]

### Script: Part 2
[monologue]

### Answer Key — Questions 11–20
| Q | Answer | Needle |
|---|--------|--------|

---

## LISTENING PART 3

*You will hear [speakers] discussing [topic].*
*First, you have 30 seconds to read Questions 21–30.*

### Questions 21–25
Choose TWO letters, A–E. (Multiple Choice Multiple)

### Questions 26–30
[Table Completion / Sentence Completion / Matching Features]

### Script: Part 3
[discussion]

### Answer Key — Questions 21–30
| Q | Answer | Needle |
|---|--------|--------|

---

## LISTENING PART 4

*You will hear a lecture on [topic].*
*First, you have 30 seconds to read Questions 31–40.*

### Questions 31–36
Complete the notes below. Write **NO MORE THAN TWO WORDS** for each answer.

### Questions 37–40
[Summary Completion / Sentence Completion]

### Script: Part 4
[lecture]

### Answer Key — Questions 31–40
| Q | Answer | Needle |
|---|--------|--------|
```

**Critical format rules:**
- `## LISTENING PART N` — level 2 heading for each part
- `### Questions N–M` — level 3 heading, en-dash between numbers
- `### Script: Part N` — level 3 heading for each script
- `### Answer Key — Questions N–M` — level 3 heading
- Questions numbered sequentially across the whole test (1–40)
- Each question set followed immediately by its answer key
- `---` horizontal rule between sections

---

## QA Checklist — Run Before Output

- 40 questions exactly; ranges are continuous and non-overlapping (1–10, 11–20, 21–30, 31–40).
- Every question set is followed immediately by its matching answer key.
- ALL non-matching question types appear somewhere in the test.
- Exactly ONE matching type used across the entire test (Matching General OR Matching Features — never both).
- Part 1 uses Note Completion only; script includes a spelling trap, a self-correction, and a distractor.
- Part 2 uses MCQ Single plus Matching (General) or Note/Table Completion.
- Part 3 uses MCQ Multiple plus Table/Sentence Completion or Matching Features.
- Part 4 uses Note Completion plus Summary Completion and/or Sentence Completion.
- Script word counts are within spec: Part 1 (250–300), Part 2 (350–400), Part 3 (400–450), Part 4 (800–900).
- All completion answers are verbatim from the script and obey the stated word limit.
- No two questions in the same completion set share the same answer — duplicates are a critical error.
- Matching lists include at least two extra options beyond the number of questions.
- Each answer has one needle quoting the exact script line; NOT GIVEN is not used in Listening.
- Stems are paraphrased — no 3-gram content-word overlap with answer line.
- Part 1 questions follow chronological script order.
- Part 4 questions follow chronological lecture order.
- Dialogue in Parts 1 and 3 sounds natural, not robotic.
- Part 4 lecture uses academic attribution, not personal opinion.
- Part 4 researcher names are phonetically distinct — no two names should sound similar when spoken aloud.
- Part 1 readability: FRE > 65 (conversational)
- Part 2 readability: FRE 50–75 (moderate)
- Part 3 readability: FRE 40–65 (academic discussion)
- Part 4 readability: FRE < 50 (academic lecture)
- Question difficulty progression: Part 1 < Part 2 < Part 3 < Part 4
- Part 4 category is selected from get_listening_p4_category rotation (never repeat the same category consecutively)
