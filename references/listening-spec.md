# Listening Module Specification

## Overview
- 4 parts, increasing complexity
- 40 questions total (10 per part)
- Audio plays ONCE only — no pause, rewind, replay
- 30 seconds pre-listening per part (read questions)
- 30 seconds post-listening per part (check answers)

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
- **DISTRACTOR:** An incorrect option mentioned then clearly discarded before correct answer confirmed

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
| Primary Task | Multiple Choice (Single) (5 questions) |
| Secondary Task | Matching or Note Completion (5 questions) |
| Difficulty | Moderate (Band 5.5–6.5) |
| Script Length | 350–400 words spoken |

**Script structure:**
| Section | Content | Questions |
|---|---|---|
| Opening | Speaker introduces themselves, welcomes audience, states purpose | — |
| Background | Brief history or context of the venue/topic | MCQ 1 |
| Key details | Facilities, opening times, services, practical info | MCQ 2–3 |
| Directions/Locations | Description of where things are located | Matching Qs |
| Closing | Final instructions, thanks, next steps | MCQ 4–5 |

---

## Part 3 — Academic Discussion

| Parameter | Specification |
|---|---|
| Format | 2–3 speakers (students + tutor, or research partners) |
| Context | Discussing research project · reviewing assignment · planning presentation |
| Primary Task | Matching (speakers to opinions) |
| Secondary Task | Multiple Choice (Single) |
| Difficulty | Challenging (Band 6.0–7.5) |
| Script Length | 400–450 words spoken |

**Mandatory script features:**
- **AGREEMENT & DISAGREEMENT TRACKING:** Script clearly shows agreeing, partially agreeing, disagreeing
- **SPEAKER ATTRIBUTION:** Every matched statement said by a specific named speaker — never ambiguous
- **HEDGED LANGUAGE:** "I'm not entirely convinced," "That's a fair point, but...," "I'd argue that..."
- **OPINION CHANGE:** At least one speaker changes or softens their view

**Script structure:**
| Section | Content | Questions |
|---|---|---|
| Opening | Tutor sets agenda, asks for update | — |
| Topic selection | Students discuss focus, disagree → one convinces the other (OPINION CHANGE) | Matching 1–2 |
| Methodology | Debate on research methods, agreement/rejection | Matching 3–4 |
| Concerns | Practical concerns raised, solutions offered | MCQ 1–2 |
| Guidance | Tutor gives timeline/methodology advice | MCQ 3–4 |
| Closing | Summary of decisions, next steps | MCQ 5 |

**Matching rules:**
- Each question asks who holds a specific view
- Options: A. [Name] only / B. [Name] only / C. Both [Name] and [Name]
- Distractor: another speaker mentions same topic but does NOT hold same opinion

---

## Part 4 — Academic Lecture

| Parameter | Specification |
|---|---|
| Format | Single academic speaker, no interruptions |
| Context | University lecture — science · history · social science · research findings |
| Primary Task | Note / Summary Completion |
| Secondary Task | Matching Features (match researcher to finding) |
| Difficulty | Most challenging (Band 7.0–8.5) |
| Script Length | 800–900 words spoken (~6 minutes) |

**Mandatory script features:**
- **HIGH-LEVEL SYNONYMS:** Script uses advanced vocabulary; questions use paraphrases. Synonym Rule is critical here.
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
# IELTS Listening — Full Practice Test

**Time:** Approx. 30 minutes | **Questions:** 40

---

## LISTENING PART 1

*You will hear a conversation between a [role] and a [role].*
*First, you have 30 seconds to read Questions 1–10.*

---

### Questions 1–10

Complete the notes below.
Write **NO MORE THAN TWO WORDS AND/OR A NUMBER** for each answer.

| | |
|---|---|
| **Example:** Membership type: | Annual |
| **Membership Application** | |
| 1 Name: | \_\_\_\_\_\_\_\_\_\_\_ |
| 2 Date of birth: | \_\_\_\_\_\_\_\_\_\_\_ |
...

---

### Answer Key — Questions 1–10

| Q | Answer | Needle |
|---|--------|--------|
| 1 | Kowalczyk | "that's K-O-W-A-L-C-Z-Y-K" |

**Mandatory traps used:** Spelling: Q1 — Self-correction: Q2 — Distractor: Q7

---

## LISTENING PART 2

*You will hear a [role] speaking to [audience].*
*First, you have 30 seconds to read Questions 11–20.*

---

### Questions 11–15

Choose the correct letter, A, B, or C.

11. ...
...

### Questions 16–20

What is the location of each of the following...?

---

### Answer Key — Questions 11–20

| Q | Answer | Needle |
|---|--------|--------|

---

## LISTENING PART 3

*You will hear [two/three] students discussing [topic] with their [tutor/supervisor].*
*First, you have 30 seconds to read Questions 21–30.*

---

### Questions 21–25

What opinion does each person express...?

---

### Questions 26–30

Choose the correct letter, A, B, or C.

---

### Answer Key — Questions 21–30

| Q | Answer | Needle |
|---|--------|--------|

---

## LISTENING PART 4

*You will hear a lecture on [topic].*
*First, you have 30 seconds to read Questions 31–40.*

---

### Questions 31–40

Complete the notes below.
Write **NO MORE THAN TWO WORDS** for each answer.

---

### Answer Key — Questions 31–40

| Q | Answer | Needle |
|---|--------|--------|
```

**Critical format rules:**
- `## LISTENING PART N` — level 2 heading for each part
- `### Questions N–M` — level 3 heading, en-dash between numbers
- `### Answer Key — Questions N–M` — level 3 heading
- Questions numbered sequentially across the whole test (1–40)
- Each question set followed immediately by its answer key
- `---` horizontal rule between sections
- Script content embedded inside its part section (see example for script placement)

---

## QA Checklist — Run Before Output
