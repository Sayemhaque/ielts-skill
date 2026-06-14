#!/usr/bin/env python3
"""
IELTS Test Validator
Validates generated Reading and Listening tests against spec rules.
Produces an Official Standard Score (0-100%) alongside binary PASS/FAIL checks.

Usage:  python3 scripts/validate.py [--json] [--score-only] [--no-score] <file.md>
"""

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# Allow local imports from scripts/
sys.path.insert(0, str(Path(__file__).resolve().parent))
from readability import flesch_reading_ease, coleman_liau_index, estimate_ielts_band, validate_readability
from question_difficulty import (
    validate_progressive_difficulty as _check_q_diff,
    compute_qds,
    vocabulary_rarity,
    _COMMON as _QDS_COMMON_WORDS,
)


# ---------------------------------------------------------------------------
# Scoring data structures
# ---------------------------------------------------------------------------

@dataclass
class CheckScore:
    """Score for a single sub-check within a category."""
    name: str
    percentage: float          # 0-100
    detail: str = ""
    suggestion: str = ""       # auto-fix suggestion when score < 100

    def to_dict(self):
        return {
            "name": self.name,
            "percentage": round(self.percentage, 1),
            "detail": self.detail,
            "suggestion": self.suggestion,
        }


@dataclass
class CategoryScore:
    """Score for one scoring category (e.g. 'Structure & Format')."""
    name: str
    letter: str               # A, B, C, ...
    weight: float             # percentage weight in overall score
    percentage: float = 0.0   # 0-100 — mean of sub-check percentages
    checks: list = field(default_factory=list)  # list[CheckScore]

    def to_dict(self):
        return {
            "name": self.name,
            "letter": self.letter,
            "weight": round(self.weight, 1),
            "percentage": round(self.percentage, 1),
            "checks": [c.to_dict() for c in self.checks],
        }


@dataclass
class OfficialScore:
    """Overall Official Standard Score with breakdown."""
    overall_percentage: float
    grade: str                 # A+, A, B, C, D
    grade_label: str           # human-readable label
    categories: list = field(default_factory=list)  # list[CategoryScore]
    action_items: list = field(default_factory=list) # suggestions for weakest categories

    def to_dict(self):
        return {
            "overall_percentage": round(self.overall_percentage, 1),
            "grade": self.grade,
            "grade_label": self.grade_label,
            "categories": [c.to_dict() for c in self.categories],
            "action_items": self.action_items,
        }


# ---------------------------------------------------------------------------
# Grade bands
# ---------------------------------------------------------------------------

GRADE_BANDS = [
    (95, "A+", "Official Standard — indistinguishable from Cambridge IELTS"),
    (85, "A",  "Near-Official — minor gaps, high quality"),
    (70, "B",  "Good Practice Test — some areas need work"),
    (50, "C",  "Below Standard — significant revision needed"),
    (0,  "D",  "Not IELTS-Compliant — fundamental issues"),
]


def _grade_for_score(pct: float) -> tuple:
    """Return (grade_letter, grade_label) for a percentage score."""
    for threshold, letter, label in GRADE_BANDS:
        if pct >= threshold:
            return letter, label
    return "D", "Not IELTS-Compliant — fundamental issues"


# ---------------------------------------------------------------------------
# Category weights — Reading uses A-G (pro-rata to 100%); Listening uses A-H
# ---------------------------------------------------------------------------

_CATEGORY_WEIGHTS_READING = {
    "A": 16.0,   # Structure & Format
    "B": 13.0,   # Readability & Progression
    "C": 20.0,   # Question Type Compliance
    "D": 16.0,   # Synonym Rule
    "E": 13.0,   # Distractor & Trap Quality
    "F": 13.0,   # Needle & Answer Quality
    "G": 9.0,    # Content & Tone Quality
    # H is Listening-only
}

_CATEGORY_WEIGHTS_LISTENING = {
    "A": 15.0,   # Structure & Format
    "B": 12.0,   # Readability & Progression
    "C": 18.0,   # Question Type Compliance
    "D": 15.0,   # Synonym Rule
    "E": 12.0,   # Distractor & Trap Quality
    "F": 12.0,   # Needle & Answer Quality
    "G": 8.0,    # Content & Tone Quality
    "H": 8.0,    # Listening-Specific
}

# Pro-rata: Reading weights must sum to 100
_READING_TOTAL = sum(_CATEGORY_WEIGHTS_READING.values())
for k in _CATEGORY_WEIGHTS_READING:
    _CATEGORY_WEIGHTS_READING[k] = round(_CATEGORY_WEIGHTS_READING[k] / _READING_TOTAL * 100, 1)

# Listening weights must sum to 100
_LISTENING_TOTAL = sum(_CATEGORY_WEIGHTS_LISTENING.values())
for k in _CATEGORY_WEIGHTS_LISTENING:
    _CATEGORY_WEIGHTS_LISTENING[k] = round(_CATEGORY_WEIGHTS_LISTENING[k] / _LISTENING_TOTAL * 100, 1)


# Mapping existing PASS/FAIL check names → scoring category
# (prefix-matched; first match wins)
_CHECK_CATEGORY_MAP = [
    # A: Structure & Format
    ("Format:", "A"),
    ("word count", "A"),
    ("Total questions", "A"),
    ("Exact question coverage", "A"),
    ("Answer key rows", "A"),
    ("Question ranges continuous", "A"),
    ("Answer key immediately follows", "A"),
    ("script length", "A"),
    ("Listening total questions", "A"),
    # B: Readability & Progression
    ("readability", "B"),
    ("Progressive question difficulty", "B"),
    # C: Question Type Compliance
    ("required types", "C"),
    ("Global type coverage", "C"),
    ("Y/N/NG not in Passage", "C"),
    ("T/F/NG not in Passage", "C"),
    # D: Synonym Rule
    ("synonym rule", "D"),
    # E: Distractor & Trap Quality
    ("Spelling trap", "E"),
    ("Self-correction", "E"),
    ("Distractor (alternative", "E"),
    ("Opinion change", "E"),
    ("Hedged language", "E"),
    ("Named researchers", "E"),
    ("Signpost language", "E"),
    # F: Needle & Answer Quality
    ("Answer keys present", "F"),
    ("All answers have Needle", "F"),
    ("Needles found in passage", "F"),
    ("word limits", "F"),
    ("Boolean distribution", "F"),
    ("NOT GIVEN uses absence", "F"),
]


def _map_check_to_category(check_name: str) -> str:
    """Map an existing PASS/FAIL check name to a scoring category letter."""
    for prefix, cat in _CHECK_CATEGORY_MAP:
        if check_name.startswith(prefix) or prefix in check_name:
            return cat
    return "?"   # unmapped


# ---------------------------------------------------------------------------
# Academic vocabulary list for G3 check (supplements _QDS_COMMON_WORDS)
# ---------------------------------------------------------------------------

_BASIC_WORDS = _QDS_COMMON_WORDS | {
    "able", "also", "always", "among", "another", "away", "became", "become",
    "begin", "behind", "below", "beside", "better", "between", "beyond",
    "body", "both", "bring", "built", "carry", "cause", "certain", "clear",
    "close", "common", "country", "cover", "cross", "day", "decide", "deep",
    "done", "draw", "drive", "early", "earth", "eight", "else", "end",
    "enough", "enter", "equal", "even", "ever", "every", "eye", "face",
    "far", "feel", "few", "field", "fight", "final", "fire", "five",
    "foot", "force", "form", "four", "free", "full", "give", "go",
    "grow", "half", "hard", "head", "hear", "help", "hold", "home",
    "horse", "hot", "hour", "house", "keep", "kind", "king", "known",
    "land", "late", "lay", "learn", "leave", "left", "less", "let",
    "life", "light", "like", "line", "live", "long", "look", "lose",
    "made", "main", "man", "many", "mark", "may", "might", "mind",
    "mine", "miss", "move", "name", "near", "need", "never", "next",
    "night", "north", "nothing", "once", "open", "own", "page", "past",
    "person", "plan", "point", "power", "present", "press", "price",
    "quite", "read", "real", "run", "say", "sea", "self", "set",
    "side", "since", "six", "something", "south", "stand", "start",
    "step", "stop", "sun", "table", "take", "tell", "ten", "thing",
    "think", "three", "time", "today", "together", "top", "toward",
    "try", "turn", "two", "upon", "use", "walk", "want", "water",
    "went", "west", "white", "whole", "without", "woman", "women",
    "word", "world", "write", "young",
    # IELTS task instruction words
    "according", "answer", "below", "choose", "complete", "correct",
    "false", "following", "given", "letter", "list", "match", "passage",
    "questions", "reading", "select", "statement", "true", "write",
    "yes", "none",
}

_OPINION_WORDS = {
    "argue", "argues", "argued", "claim", "claims", "claimed",
    "believe", "believes", "believed", "contend", "contends", "contended",
    "assert", "asserts", "asserted", "maintain", "maintains", "maintained",
    "insist", "insists", "insisted", "advocate", "advocates", "advocated",
    "propose", "proposes", "proposed",
}

_ARGUMENT_MARKERS = {
    "argue", "argues", "argued", "argument", "contend", "contends", "contended",
    "however", "nevertheless", "nonetheless", "critic", "critics", "criticism",
    "conversely", "contrary", "dispute", "disputes", "disputed", "refute",
    "refutes", "refuted", "challenge", "challenges", "challenged",
    "controversial", "debate", "controversy", "counter-argument",
    "notwithstanding",
}

_AGREEMENT_PHRASES = [
    r"I\s+(?:completely\s+)?agree",
    r"you['']?re\s+(?:absolutely\s+)?right",
    r"that['']?s\s+(?:a\s+)?(?:fair|good|valid|excellent)\s+point",
    r"I\s+see\s+(?:what\s+you\s+)?mean",
    r"you['']?ve\s+convinced\s+me",
    r"I\s+(?:think|believe)\s+you['']?re\s+right",
    r"exactly",
    r"absolutely",
    r"definitely",
]

_DISAGREEMENT_PHRASES = [
    r"I\s+(?:don['']?t|do\s+not)\s+(?:think|agree|believe)",
    r"I['']?m\s+not\s+(?:entirely\s+)?convinced",
    r"that['']?s\s+not\s+(?:quite\s+)?right",
    r"I\s+(?:have\s+to\s+)?disagree",
    r"I['']?d\s+(?:have\s+to\s+)?argue",
    r"that['']?s\s+a\s+bit\s+of\s+a\s+stretch",
    r"I['']?m\s+skeptical",
    r"I['']?m\s+not\s+sure\s+(?:I\s+)?(?:can|would)",
]

# ---------------------------------------------------------------------------
# Question difficulty helpers (shared by reading & listening validation)
# ---------------------------------------------------------------------------

_BOILERPLATE_Q = re.compile(
    r"(do the following statements agree with the information|"
    r"in boxes \d+[-–]\d+ on your answer sheet|"
    r"true if the statement|false if the statement|not given if there|"
    r"choose the correct letter|choose the correct heading|"
    r"complete the (notes|table|summary|sentence) below|"
    r"write no more than \w+ words|"
    r"match each (statement|heading|sentence ending|sentence|feature)|"
    r"list of (headings|people|experts|statements|endings)|"
    r"using the list of words below|"
    r"your answers in the spaces provided|"
    r"you may use any letter more than once|"
    r"which paragraph contains the following information)",
    re.IGNORECASE,
)


def _strip_q_boilerplate(text: str) -> str:
    return _BOILERPLATE_Q.sub("", text).strip()


def _detect_q_type(content: str) -> str:
    """Detect question type from section content keywords."""
    cl = content.lower()
    if "yes" in cl and "no" in cl and "not given" in cl:
        return "ynng"
    if "true" in cl and "false" in cl and "not given" in cl:
        return "tfng"
    if "choose the correct heading" in cl or "list of headings" in cl:
        return "headings"
    # Detect MCQs: "Choose the correct letter" (standard) OR "Choose TWO letters, A–E" (demo variant)
    has_mcq_keywords = "choose" in cl and "letter" in cl
    if "choose the correct letter" in cl or has_mcq_keywords:
        # Use word boundaries so "two" in "networks" doesn't cause a false positive
        if re.search(r"\btwo\b", cl) or re.search(r"\bthree\b", cl):
            return "mcq_multiple"
        return "mcq_single"
    if "match each statement" in cl or "list of people" in cl or "list of experts" in cl:
        return "features"
    if "match each sentence ending" in cl:
        return "matching_sentence_endings"
    if "complete the summary" in cl and ("list of words" in cl or "from the list" in cl):
        return "summary_completion_from_list"
    if "complete the summary" in cl:
        return "summary_completion_from_text"
    if "complete the notes" in cl:
        return "note_completion"
    if "complete the table" in cl:
        return "table_completion"
    if "complete the sentence" in cl or "complete the sentences" in cl:
        return "sentence_completion"
    return "completion"

# ---------------------------------------------------------------------------
# STOPWORDS — excluded from n-gram synonym overlap checks
# These are structural/instruction words that legitimately appear in both
# source passages and question stems without violating the Synonym Rule.
# ---------------------------------------------------------------------------
STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "that", "this", "which", "who", "what",
    "how", "when", "where", "is", "are", "was", "were", "be", "been",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "can", "not", "no", "it", "its", "they",
    "their", "he", "she", "we", "you", "as", "if", "than", "then", "so",
    "also", "more", "most", "some", "any", "all", "each", "both", "about",
    "into", "through", "during", "before", "after", "between", "under",
    "over", "while", "although", "because", "since", "however", "therefore",
    "thus", "such", "other", "there", "here", "these", "those",
    # Question instruction words
    "write", "choose", "complete", "notes", "below", "following", "correct",
    "letter", "answer", "questions", "passage", "reading", "listening",
    "according", "statements", "agree", "information", "given", "true",
    "false", "yes", "none", "one", "two", "three", "four", "five",
    "words", "number", "maximum",
}


def read_file(path):
    with open(path) as f:
        return f.read()


def extract_sections(text, level="###"):
    pattern = rf"^{level}\s+(.+?)$"
    lines = text.split("\n")
    sections = []
    current = None
    for line in lines:
        m = re.match(pattern, line)
        if m:
            if current:
                sections.append(current)
            current = {"heading": m.group(1).strip(), "lines": []}
        elif current is not None:
            current["lines"].append(line)
    if current:
        sections.append(current)
    return sections


def count_words(text):
    return len(text.split())


def find_answer_tables(text):
    tables = []
    lines = text.split("\n")
    in_table = False
    header_passed = False
    table_lines = []
    for line in lines:
        if line.strip().startswith("| Q | Answer | Needle |"):
            in_table = True
            header_passed = False
            table_lines = [line]
        elif in_table:
            if line.strip().startswith("|---|"):
                header_passed = True
                table_lines.append(line)
            elif line.strip().startswith("|") and header_passed:
                table_lines.append(line)
            else:
                in_table = False
                if len(table_lines) > 2:
                    tables.append(parse_table(table_lines))
                table_lines = []
    if len(table_lines) > 2:
        tables.append(parse_table(table_lines))
    return tables


def parse_table(lines):
    rows = []
    for line in lines[2:]:
        line = line.strip()
        if line.startswith("|") and line.endswith("|"):
            cells = [c.strip() for c in line.split("|")[1:-1]]
            if len(cells) >= 3:
                q_raw = cells[0]
                # Handle range format like "20-21" or "20–21"
                range_match = re.match(r'^(\d+)\s*[–-]\s*(\d+)$', q_raw)
                if range_match:
                    start_q = int(range_match.group(1))
                    end_q = int(range_match.group(2))
                    for q_num in range(start_q, end_q + 1):
                        rows.append({"q": str(q_num), "answer": cells[1], "needle": cells[2]})
                else:
                    rows.append({"q": cells[0], "answer": cells[1], "needle": cells[2]})
    return rows


def find_matching_word_list(text):
    lines = text.split("\n")
    in_list = False
    options = []
    for line in lines:
        if re.search(r"(Word list|List of|Locations|Contributions)", line, re.IGNORECASE):
            in_list = True
            continue
        if in_list:
            if "|" in line and "---" not in line:
                cells = [c.strip() for c in line.split("|") if c.strip()]
                for c in cells:
                    if c not in ["", " ", "List of Experts / Organisations"] and not re.match(r"^[A-Z]$", c):
                        if c not in options:
                            options.append(c)
            elif line.strip() == "" or line.strip().startswith("###") or line.strip().startswith("---"):
                if options:
                    break
            elif "·" in line or ":" in line:
                items = re.split(r"[·,]", line)
                for item in items:
                    item = item.strip().lstrip("*")
                    if item and item not in ["Word list", ""] and not item.startswith("List"):
                        options.append(item)
    return options


def extract_questions(text):
    questions = re.findall(r"^(\d+)\.", text, re.MULTILINE)
    return [int(q) for q in questions]


def count_gap_questions(text):
    gaps = re.findall(r"\((\d+)\)\s*_{3,}", text)
    return [int(g) for g in gaps]


def extract_question_sections(text):
    pattern = re.compile(
        r"^### Questions? (\d+)(?:[–-](\d+))?\s*$"
        r"(.*?)(?=^### (?:Questions|Answer Key)|^## |\Z)",
        re.MULTILINE | re.DOTALL,
    )
    return [
        {
            "start": int(m.group(1)),
            "end": int(m.group(2) or m.group(1)),
            "content": m.group(3),
            "pos": m.start(),
        }
        for m in pattern.finditer(text)
    ]


def extract_answer_key_sections(text):
    pattern = re.compile(
        r"^### Answer Key\s*[—:-]\s*Questions? (\d+)(?:[–-](\d+))?\s*$"
        r"(.*?)(?=^### (?:Questions|Answer Key)|^## |\Z)",
        re.MULTILINE | re.DOTALL,
    )
    return [
        {
            "start": int(m.group(1)),
            "end": int(m.group(2) or m.group(1)),
            "content": m.group(3),
            "pos": m.start(),
        }
        for m in pattern.finditer(text)
    ]


def extract_numbered_questions_from_section(section):
    numbered = [int(q) for q in re.findall(r"^(\d+)\.", section, re.MULTILINE)]
    gaps = [int(q) for q in re.findall(r"\b(\d+)\s+_+", section)]
    parenthesised_gaps = [int(q) for q in re.findall(r"\((\d+)\)\s*_{3,}", section)]
    return sorted(set(numbered + gaps + parenthesised_gaps))


def add_check(checks, check, passed, detail=""):
    checks.append({
        "check": check,
        "status": "PASS" if passed else "FAIL",
        "detail": detail,
    })


def extract_passages(text):
    lines = text.split("\n")
    passages = []
    in_passage = False
    current = []
    title = ""
    passage_start = re.compile(r"^##\s+READING PASSAGE (\d)")
    passage_end = re.compile(r"^#{2,4}\s+(Questions|Answer|Key)")
    content_filter = re.compile(r"^#{2,3}\s")

    for line in lines:
        stripped = line.strip()
        m = passage_start.match(stripped)
        if m:
            if in_passage and current:
                passages.append({"title": title, "content": "\n".join(current)})
            title = f"Passage {m.group(1)}"
            current = []
            in_passage = True
            continue
        if in_passage:
            if passage_end.match(stripped) or passage_start.match(stripped):
                if current:
                    passages.append({"title": title, "content": "\n".join(current)})
                in_passage = False
                current = []
                continue
            if content_filter.match(stripped):
                if stripped and len(stripped) > 3:
                    current.append(line)
            elif stripped and (len(stripped) > 20 or stripped.startswith("**")):
                current.append(line)
    if in_passage and current:
        passages.append({"title": title, "content": "\n".join(current)})
    return passages


def extract_scripts(text):
    scripts = []
    for m in re.finditer(r"### Script: (Part \d+)\s*\n(.*?)(?=---|\Z)", text, re.DOTALL):
        scripts.append({"part": m.group(1), "content": m.group(2).strip()})
    return scripts


def check_spelling_trap(text):
    return bool(re.search(r"[A-Z](?:-[A-Z]){2,}", text))


def check_self_correction(text):
    patterns = [
        r"no\s*[,!]?\s*(wait|sorry|actually|correction|let me)",
        r"sorry[,!]\s",
        r"that['']s\s+\w+,\s+not\s+",
        r"actually.*?\d+.*?no",
        r"\d+\s*\.{3,}\s*no\s+wait",
    ]
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)


def check_distractor(text):
    patterns = [
        r"also.*?(?:popular|many|other).*?(?:but|however|actually)",
        r"(?:instead of|rather than)",
        r"you could also.*?(?:but|however)",
    ]
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)


def check_opinion_change(text):
    patterns = [
        r"you['']?ve convinced me",
        r"you know what.*?actually",
        r"I think you['']?re right",
        r"that['']?s a (?:fair|good) point",
        r"actually.*?I (?:think|agree)",
    ]
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)


def check_hedged_language(text):
    patterns = [
        r"I['']m not entirely convinced",
        r"that['']?s a fair point",
        r"I['']d argue",
        r"that['']?s possible",
        r"I see what you mean",
    ]
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)


def check_signpost_language(text):
    patterns = [
        r"turning now to",
        r"this brings us to",
        r"what is particularly noteworthy",
        r"what is interesting",
        r"let me turn to",
        r"now let['']?s (?:look|consider|examine|turn)",
    ]
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)


def count_researcher_names(text):
    title_pattern = r"\b(?:Dr|Professor|Sir)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?"
    names = set(re.findall(title_pattern, text))
    role_pattern = r"\b[A-Z][a-z]+\s+[A-Z][a-z]+,\s+(?:a|an)\s+[a-z]+(?:\s+[a-z]+){0,3}"
    for match in re.findall(role_pattern, text):
        names.add(match.split(",")[0])
    return len(names)


# ---------------------------------------------------------------------------
# IMPROVED SYNONYM RULE CHECK
# Now catches 3-gram AND 4-gram overlaps after stripping stopwords.
# Reports violations grouped by question number for actionable output.
# ---------------------------------------------------------------------------

def get_content_ngrams(text, n):
    """
    Extract content-word n-grams from text.
    Strips stopwords so that function-word matches don't trigger false positives.
    Returns a set of n-gram strings.
    """
    import string
    text = text.translate(str.maketrans('', '', string.punctuation))
    words = [w.lower() for w in text.split()]
    # Keep only content words
    content_words = [w for w in words if w not in STOPWORDS and len(w) > 2]
    if len(content_words) < n:
        return set()
    return set(" ".join(content_words[i:i+n]) for i in range(len(content_words) - n + 1))


# These n-grams appear in question instructions themselves, not question stems.
INSTRUCTION_PATTERNS = {
    "complete summary below",
    "choose correct letter",
    "write more than",
    "following statements agree",
    "agree information given",
    "choose correct heading",
    "read passage",
    "reading passage",
    "answer sheet",
    "correct letter",
    "correct number",
    "complete notes below",
    "complete sentences below",
    "complete table below",
    "list headings",
    "list people",
    "list experts",
}


def check_synonym_rule_v2(source_text, questions_text, question_numbers=None):
    """
    Improved synonym check using 3-gram AND 4-gram content-word overlap.

    Returns:
        violations (list of str): human-readable violation descriptions
        overlap_3 (set): matching 3-grams
        overlap_4 (set): matching 4-grams
    """
    src_3 = get_content_ngrams(source_text, 3)
    src_4 = get_content_ngrams(source_text, 4)
    q_3 = get_content_ngrams(questions_text, 3)
    q_4 = get_content_ngrams(questions_text, 4)

    raw_3 = src_3 & q_3
    raw_4 = src_4 & q_4

    # Filter out instruction boilerplate
    overlap_3 = {g for g in raw_3 if not any(pat in g for pat in INSTRUCTION_PATTERNS)}
    overlap_4 = {g for g in raw_4 if not any(pat in g for pat in INSTRUCTION_PATTERNS)}

    violations = []
    if overlap_4:
        violations.append(f"4-gram hits ({len(overlap_4)}): {', '.join(sorted(overlap_4)[:5])}")
    if overlap_3:
        violations.append(f"3-gram hits ({len(overlap_3)}): {', '.join(sorted(overlap_3)[:5])}")

    return violations, overlap_3, overlap_4


# ---------------------------------------------------------------------------
# NEW SCORING CHECK FUNCTIONS (22 total)
# Each returns a CheckScore with percentage, detail, and suggestion.
# ---------------------------------------------------------------------------

def _score_mcq_option_format(text, q_sections):
    """A1: MCQ option format — options labeled A/B/C/D consistently."""
    mcq_sections = []
    for s in q_sections:
        content = s["content"]
        cl = content.lower()
        if "choose" in cl and "letter" in cl:
            mcq_sections.append(content)

    if not mcq_sections:
        return CheckScore("MCQ option format", 100.0, "No MCQ sections found", "")

    total_ok = 0
    total_issues = 0
    for content in mcq_sections:
        # Find option lines: "A  ...", "B  ...", etc.
        option_lines = re.findall(r"^\s*([A-E])\s+(.+)$", content, re.MULTILINE)
        if option_lines:
            labels = [ol[0] for ol in option_lines]
            # Should be consecutive A, B, C, D (or A-E for multi)
            expected = "ABCDE"[:len(labels)]
            if labels == list(expected):
                total_ok += 1
            else:
                total_issues += 1
        else:
            total_issues += 1

    pct = (total_ok / max(1, total_ok + total_issues)) * 100
    suggestion = "" if pct == 100 else "Label MCQ options consecutively (A, B, C, D)"
    return CheckScore("MCQ option format", pct,
                      f"{total_ok}/{total_ok + total_issues} sections have consistent A/B/C/D labels",
                      suggestion)


def _score_within_passage_qds(text, q_sections, passages_or_scripts, is_reading=True):
    """B1: Within-passage QDS progression — later questions harder than earlier."""
    n_passages = 3 if is_reading else 4
    passages_with_progression = 0

    for p_idx in range(1, n_passages + 1):
        if is_reading:
            lo = [1, 14, 27][p_idx - 1]
            hi = [13, 26, 40][p_idx - 1]
        else:
            lo = (p_idx - 1) * 10 + 1
            hi = p_idx * 10

        p_sections = [s for s in q_sections if s["start"] >= lo and s["end"] <= hi]
        q_list = []
        for section in p_sections:
            section_text = _strip_q_boilerplate(section["content"])
            if len(section_text.split()) < 3:
                continue
            sec_type = _detect_q_type(section["content"])
            q_list.append({"text": section_text, "type": sec_type})

        if len(q_list) < 2:
            continue

        # Split into first half and second half
        mid = len(q_list) // 2
        first_half = q_list[:mid]
        second_half = q_list[mid:]

        qds_first = [compute_qds(q["text"], q["type"]) for q in first_half]
        qds_second = [compute_qds(q["text"], q["type"]) for q in second_half]

        mean_first = sum(qds_first) / max(1, len(qds_first))
        mean_second = sum(qds_second) / max(1, len(qds_second))

        if mean_second >= mean_first:
            passages_with_progression += 1

    pct = (passages_with_progression / n_passages) * 100
    suggestion = "" if pct == 100 else (
        "Arrange harder question types later within each passage/part"
    )
    return CheckScore("Within-passage QDS progression", pct,
                      f"{passages_with_progression}/{n_passages} passages show internal difficulty increase",
                      suggestion)


def _score_fre_gap(passage_texts, is_reading=True):
    """B2: FRE gap between passages — FRE should decrease (easier → harder)."""
    if len(passage_texts) < 2:
        return CheckScore("FRE gap between passages", 100.0, "Not enough passages", "")

    fre_scores = [flesch_reading_ease(t) for t in passage_texts]
    inversions = 0
    for i in range(len(fre_scores) - 1):
        if fre_scores[i] <= fre_scores[i + 1]:  # not decreasing
            inversions += 1

    if inversions == 0:
        pct = 100.0
    elif inversions == 1:
        pct = 50.0
    else:
        pct = 0.0

    fre_str = " > ".join(f"{f:.0f}" for f in fre_scores)
    suggestion = "" if pct == 100 else (
        f"Adjust passage vocabulary so readability decreases: got {fre_str}"
    )
    return CheckScore("FRE gap between passages", pct,
                      f"FRE progression: {fre_str} ({inversions} inversion(s))",
                      suggestion)


def _score_cli_crosscheck(passage_texts):
    """B3: CLI cross-check — CLI should increase as FRE decreases."""
    if len(passage_texts) < 2:
        return CheckScore("CLI cross-check", 100.0, "Not enough passages", "")

    fre_scores = [flesch_reading_ease(t) for t in passage_texts]
    cli_scores = [coleman_liau_index(t) for t in passage_texts]

    # Check: when FRE goes down, CLI should go up
    consistent = 0
    total_pairs = 0
    for i in range(len(fre_scores) - 1):
        total_pairs += 1
        fre_decreases = fre_scores[i] > fre_scores[i + 1]
        cli_increases = cli_scores[i] < cli_scores[i + 1]
        if fre_decreases == cli_increases:
            consistent += 1

    pct = (consistent / max(1, total_pairs)) * 100
    suggestion = "" if pct == 100 else (
        "Check readability metrics consistency — FRE and CLI should agree on difficulty direction"
    )
    return CheckScore("CLI cross-check", pct,
                      f"CLI consistent with FRE for {consistent}/{total_pairs} passage pairs",
                      suggestion)


def _score_min_types_per_passage(q_sections, is_reading=True):
    """C1: Minimum 3 question types per passage/part."""
    n_passages = 3 if is_reading else 4
    passages_meeting = 0

    for p_idx in range(1, n_passages + 1):
        if is_reading:
            lo = [1, 14, 27][p_idx - 1]
            hi = [13, 26, 40][p_idx - 1]
        else:
            lo = (p_idx - 1) * 10 + 1
            hi = p_idx * 10

        p_sections = [s for s in q_sections if s["start"] >= lo and s["end"] <= hi]
        types = set()
        for section in p_sections:
            detected = _detect_q_type(section["content"])
            types.add(detected)
            # Add parent categories
            if detected in ("note_completion", "table_completion", "sentence_completion",
                            "summary_completion_from_text", "summary_completion_from_list"):
                types.add("completion")
            if detected in ("mcq_single", "mcq_multiple"):
                types.add("mcq")
            if detected in ("headings", "features", "matching_sentence_endings"):
                types.add("matching")

        if len(types) >= 3:
            passages_meeting += 1

    pct = (passages_meeting / n_passages) * 100
    suggestion = "" if pct == 100 else (
        "Add at least 3 distinct question types per passage/part"
    )
    return CheckScore("Min 3 question types per passage", pct,
                      f"{passages_meeting}/{n_passages} passages have ≥3 types",
                      suggestion)


def _score_matching_extra_options(text, q_sections):
    """C2: Matching/Summary list extra options — need ≥2 extras."""
    # Find all lists in the document (word lists, heading lists, ending lists)
    list_sections = []
    current_list = None
    in_list = False
    list_type = None
    list_gap_count = 0

    for section in q_sections:
        content = section["content"]
        cl = content.lower()

        # Count the number of gaps/questions that need matching
        n_gaps = len(extract_numbered_questions_from_section(content))

        # Find option entries (lines starting with roman numerals, or A  ..., B  ..., etc.)
        # For heading lists: numbered list items
        heading_items = re.findall(r"^\s*(?:ix|iv|v?i{0,3})\s+.*$", content, re.MULTILINE | re.IGNORECASE)
        letter_items = re.findall(r"^\s*([A-I])\s+(?:[A-Z]|.*\w)", content, re.MULTILINE)

        # For summary-from-list: explicit word list
        word_list_match = re.search(
            r"(?:Word list|List of words|from the list)[^\n]*\n((?:[A-I]\s+\S+.*\n?)+)",
            content, re.IGNORECASE
        )
        word_list_items = []
        if word_list_match:
            word_list_items = re.findall(r"^\s*([A-I])\s+", word_list_match.group(1), re.MULTILINE)

        total_options = len(heading_items) + len(letter_items) + len(word_list_items)
        if total_options > 0 and n_gaps > 0:
            extras = total_options - n_gaps
            list_sections.append({
                "type": "matching/summary list",
                "options": total_options,
                "gaps": n_gaps,
                "extras": extras,
            })

    if not list_sections:
        return CheckScore("Matching/Summary list extra options", 100.0, "No matching/summary lists found", "")

    ok_lists = sum(1 for ls in list_sections if ls["extras"] >= 2)
    pct = (ok_lists / len(list_sections)) * 100
    suggestion = "" if pct == 100 else (
        "Add ≥2 extra options to every matching and summary-from-list question"
    )
    detail = f"{ok_lists}/{len(list_sections)} lists have ≥2 extra options"
    return CheckScore("Matching/Summary list extra options", pct, detail, suggestion)


def _score_mcq_multi_consistency(text, q_sections, tables):
    """C3: MCQ Multiple answer count — 'Choose TWO' should have 2 correct in key."""
    mcq_multi_sections = []
    for section in q_sections:
        cl = section["content"].lower()
        if "choose" in cl and "letter" in cl:
            if re.search(r"\btwo\b", cl) or re.search(r"\bthree\b", cl):
                # Determine how many answers expected
                if re.search(r"\btwo\b", cl):
                    expected_count = 2
                else:
                    expected_count = 3
                mcq_multi_sections.append({
                    "start": section["start"],
                    "end": section["end"],
                    "expected": expected_count,
                })

    if not mcq_multi_sections or not tables:
        return CheckScore("MCQ Multiple answer count", 100.0, "No MCQ multi-select found", "")

    all_rows = [r for t in tables for r in t]
    ok_sections = 0
    for ms in mcq_multi_sections:
        # Count answers for these question numbers
        q_answers = []
        for r in all_rows:
            try:
                q_num = int(r["q"])
            except ValueError:
                continue
            if ms["start"] <= q_num <= ms["end"]:
                q_answers.append(r["answer"].strip())
        # For "Choose TWO letters", answers like "B AND E" or "B, E" or "20 B, 21 E"
        # Count distinct letter answers
        letter_answers = re.findall(r'\b([A-E])\b', " ".join(q_answers))
        if len(letter_answers) == ms["expected"]:
            ok_sections += 1

    pct = (ok_sections / max(1, len(mcq_multi_sections))) * 100
    suggestion = "" if pct == 100 else (
        "Ensure MCQ multi-select answers match the stated count (e.g. 'Choose TWO' → exactly 2 correct answers)"
    )
    return CheckScore("MCQ Multiple answer count", pct,
                      f"{ok_sections}/{len(mcq_multi_sections)} sections match expected answer count",
                      suggestion)


def _score_2gram_overlap(source_text, questions_text):
    """D1: 2-gram content-word overlap rate — should be <5%."""
    src_2 = get_content_ngrams(source_text, 2)
    q_2 = get_content_ngrams(questions_text, 2)
    overlap_2 = {g for g in (src_2 & q_2) if not any(pat in g for pat in INSTRUCTION_PATTERNS)}

    if not q_2:
        return CheckScore("2-gram overlap rate", 100.0, "No question 2-grams", "")

    overlap_rate = len(overlap_2) / len(q_2) * 100
    if overlap_rate < 5:
        pct = 100.0
    elif overlap_rate < 10:
        pct = 70.0
    elif overlap_rate < 20:
        pct = 40.0
    else:
        pct = 0.0

    suggestion = "" if pct == 100 else (
        f"Paraphrase question stems more — 2-gram overlap is {overlap_rate:.1f}% (target <5%)"
    )
    return CheckScore("2-gram overlap rate", pct,
                      f"{overlap_rate:.1f}% overlap ({len(overlap_2)}/{len(q_2)} 2-grams)",
                      suggestion)


def _score_unigram_overlap(source_text, questions_text):
    """D2: Unigram content-word overlap — should be <30%."""
    import string
    src_clean = source_text.translate(str.maketrans('', '', string.punctuation))
    q_clean = questions_text.translate(str.maketrans('', '', string.punctuation))

    src_words = set(w.lower() for w in src_clean.split() if w.lower() not in STOPWORDS and len(w) > 2)
    q_words = [w.lower() for w in q_clean.split() if w.lower() not in STOPWORDS and len(w) > 2]

    if not q_words:
        return CheckScore("Unigram content-word overlap", 100.0, "No content words in questions", "")

    q_word_set = set(q_words)
    overlap = src_words & q_word_set
    overlap_rate = len(overlap) / len(q_word_set) * 100

    if overlap_rate < 30:
        pct = 100.0
    elif overlap_rate < 50:
        pct = 60.0
    elif overlap_rate < 70:
        pct = 30.0
    else:
        pct = 0.0

    suggestion = "" if pct == 100 else (
        f"Replace more source words in stems — unigram overlap is {overlap_rate:.0f}% (target <30%)"
    )
    return CheckScore("Unigram content-word overlap", pct,
                      f"{overlap_rate:.0f}% overlap ({len(overlap)}/{len(q_word_set)} words)",
                      suggestion)


def _score_mcq_distractor_vocab(text, q_sections, passages):
    """E1: MCQ distractor source vocabulary — wrong options should use passage words."""
    if not passages:
        return CheckScore("MCQ distractor source vocabulary", 100.0, "No passages to check against", "")

    passage_content = " ".join(p["content"] for p in passages).lower()
    passage_words = set(re.findall(r"[a-z]{3,}", passage_content))

    mcq_sections = []
    for section in q_sections:
        cl = section["content"].lower()
        if "choose" in cl and "letter" in cl:
            mcq_sections.append(section)

    if not mcq_sections:
        return CheckScore("MCQ distractor source vocabulary", 100.0, "No MCQ sections found", "")

    # For each MCQ section, find option text (lines starting with A/B/C/D/E)
    total_distractors = 0
    good_distractors = 0

    for section in mcq_sections:
        content = section["content"]
        # Find answer letters from answer key
        tables = find_answer_tables(text)
        all_answers = [r for t in tables for r in t]

        section_start = section["start"]
        section_end = section["end"]
        correct_letters = set()
        for r in all_answers:
            try:
                q_num = int(r["q"])
            except ValueError:
                continue
            if section_start <= q_num <= section_end:
                ans = r["answer"].strip().upper()
                # Extract letter(s) from answer
                letters = re.findall(r'\b([A-E])\b', ans)
                correct_letters.update(letters)

        # Parse option lines
        option_lines = re.findall(r"^\s*([A-E])\s+(.+)$", content, re.MULTILINE)
        for label, opt_text in option_lines:
            if label in correct_letters:
                continue  # This is a correct answer, not a distractor
            total_distractors += 1
            opt_words = set(re.findall(r"[a-z]{3,}", opt_text.lower()))
            # Check if ≥1 content word from option appears in passage
            if opt_words & passage_words:
                good_distractors += 1

    if total_distractors == 0:
        return CheckScore("MCQ distractor source vocabulary", 100.0, "No MCQ distractors found", "")

    pct = (good_distractors / total_distractors) * 100
    suggestion = "" if pct == 100 else (
        "Use passage vocabulary in MCQ wrong options — distractors should come from the source text"
    )
    return CheckScore("MCQ distractor source vocabulary", pct,
                      f"{good_distractors}/{total_distractors} distractors use source vocabulary",
                      suggestion)


def _score_tfng_trap_density(text, q_sections, tables):
    """E2: T/F/NG trap density — should have ≥2 'trap' items (tempting wrong details)."""
    # Find T/F/NG sections
    tfng_sections = []
    for section in q_sections:
        cl = section["content"].lower()
        if "true" in cl and "false" in cl and "not given" in cl:
            tfng_sections.append(section)

    if not tfng_sections or not tables:
        return CheckScore("T/F/NG trap density", 100.0, "No T/F/NG sections found", "")

    all_rows = [r for t in tables for r in t]
    trap_count = 0

    # Heuristic: FALSE answers are "traps" when the needle mentions wrong period/quantity/origin
    # Also count NOT GIVEN as traps
    for section in tfng_sections:
        for r in all_rows:
            try:
                q_num = int(r["q"])
            except ValueError:
                continue
            if not (section["start"] <= q_num <= section["end"]):
                continue
            ans = r["answer"].strip().upper()
            needle = r["needle"].lower()
            if ans == "FALSE":
                # Check for trap indicators in needle
                trap_indicators = [
                    r"wrong\b", r"incorrect\b", r"actually\b", r"in fact\b",
                    r"misleading\b", r"contradicts?\b", r"overstate[ds]?\b",
                    # Wrong detail indicators
                    r"not\s+\w+\b", r"different\s+", r"rather\s+than\b",
                    r"instead\s+of\b", r"confuse[ds]?\b",
                ]
                if any(re.search(p, needle) for p in trap_indicators):
                    trap_count += 1
                else:
                    # Every FALSE is inherently a trap (contradiction)
                    trap_count += 1
            elif ans == "NOT GIVEN":
                trap_count += 1  # NOT GIVEN items are always traps

    total_tfng = sum(1 for r in all_rows
                     if r["answer"].strip().upper() in ("TRUE", "FALSE", "NOT GIVEN"))

    if total_tfng == 0:
        return CheckScore("T/F/NG trap density", 100.0, "No T/F/NG answers found", "")

    if trap_count >= 2:
        pct = 100.0
    elif trap_count >= 1:
        pct = 50.0
    else:
        pct = 0.0

    suggestion = "" if pct == 100 else (
        "Add tempting trap items to T/F/NG sets (wrong period, quantity, or origin in statements)"
    )
    return CheckScore("T/F/NG trap density", pct,
                      f"{trap_count} trap items found across {total_tfng} T/F/NG answers",
                      suggestion)


def _score_needle_precision(tables):
    """F1: Needle precision — quoted needle text should be ≤40 words."""
    if not tables:
        return CheckScore("Needle precision", 100.0, "No answer tables found", "")

    precise_count = 0
    total_count = 0

    for t in tables:
        for r in t:
            if r["answer"].strip().upper() == "NOT GIVEN":
                continue  # NOT GIVEN needles are absence notes, exempt
            needle = r["needle"].strip()
            if not needle:
                continue
            total_count += 1
            # Extract quoted portion
            quoted = re.findall(r'"([^"]+)"', needle)
            if quoted:
                # Use the longest quoted segment
                main_quote = max(quoted, key=len)
            else:
                # Use text before commentary separator
                main_quote = re.split(r'\s*[—–;]\s*', needle)[0]

            main_quote = re.sub(r'\*\*', '', main_quote)
            word_count = len(main_quote.split())

            if word_count <= 40:
                precise_count += 1

    if total_count == 0:
        return CheckScore("Needle precision", 100.0, "No needles to check", "")

    pct = (precise_count / total_count) * 100
    # Score: 100% if ≥80% needles are precise, 50% if 50-80%, 0% if <50%
    if pct >= 80:
        score = 100.0
    elif pct >= 50:
        score = 50.0
    else:
        score = 0.0

    suggestion = "" if score == 100 else (
        "Shorten needle quotes — cite only the one sentence that proves the answer (≤40 words)"
    )
    return CheckScore("Needle precision", score,
                      f"{precise_count}/{total_count} needles ≤40 words ({pct:.0f}%)",
                      suggestion)


def _score_completion_verbatim(text, q_sections, passages, tables):
    """F2: Completion answer verbatim match — answers should appear in source."""
    if not passages or not tables:
        return CheckScore("Completion answer verbatim match", 100.0, "No passages or tables", "")

    passage_content = " ".join(p["content"] for p in passages).lower()
    passage_content = re.sub(r'\*\*', '', passage_content)
    passage_content = re.sub(r'\s+', ' ', passage_content)

    all_rows = [r for t in tables for r in t]
    total_completion = 0
    matched = 0

    # Identify completion questions
    completion_types = {"note_completion", "table_completion", "sentence_completion",
                       "summary_completion_from_text", "summary_completion_from_list"}

    for section in q_sections:
        detected = _detect_q_type(section["content"])
        if detected in completion_types:
            for r in all_rows:
                try:
                    q_num = int(r["q"])
                except ValueError:
                    continue
                if not (section["start"] <= q_num <= section["end"]):
                    continue
                ans = r["answer"].strip()
                # Skip boolean and letter answers
                if ans.upper() in ("TRUE", "FALSE", "NOT GIVEN", "YES", "NO"):
                    continue
                if re.match(r'^[A-E]$', ans.strip()):
                    continue
                total_completion += 1
                # Check if answer text appears verbatim in passage
                ans_lower = ans.lower().strip()
                if ans_lower in passage_content:
                    matched += 1

    if total_completion == 0:
        return CheckScore("Completion answer verbatim match", 100.0, "No completion answers found", "")

    pct = (matched / total_completion) * 100
    suggestion = "" if pct == 100 else (
        "Ensure all completion answers are copied verbatim from the source passage/script"
    )
    return CheckScore("Completion answer verbatim match", pct,
                      f"{matched}/{total_completion} completion answers found verbatim in source",
                      suggestion)


def _score_answer_uniqueness(tables):
    """F3: Answer uniqueness — no two questions should share the same answer."""
    if not tables:
        return CheckScore("Answer uniqueness", 100.0, "No answer tables found", "")

    all_answers = {}
    for t in tables:
        for r in t:
            ans = r["answer"].strip()
            q = r["q"]
            if ans.upper() in ("TRUE", "FALSE", "NOT GIVEN", "YES", "NO"):
                continue  # Boolean answers are expected to repeat
            if re.match(r'^[A-E]$', ans):
                continue  # Single letter MCQ answers can repeat
            if ans not in all_answers:
                all_answers[ans] = []
            all_answers[ans].append(q)

    dupes = {ans: qs for ans, qs in all_answers.items() if len(qs) > 1}

    if not dupes:
        return CheckScore("Answer uniqueness", 100.0, "All non-boolean answers are unique", "")

    dupe_count = sum(len(qs) for qs in dupes.values())
    if dupe_count <= 2:
        pct = 50.0
    else:
        pct = 0.0

    suggestion = "" if pct == 100 else (
        f"Duplicate answers found: {', '.join(f'{ans} (Q{qs})' for ans, qs in list(dupes.items())[:3])} — make each answer unique"
    )
    return CheckScore("Answer uniqueness", pct,
                      f"{len(dupes)} duplicate answer values across {dupe_count} questions",
                      suggestion)


def _score_p1_factual_tone(passages):
    """G1: Passage 1 factual tone — should have low opinion-language density."""
    if not passages:
        return CheckScore("P1 factual tone", 0.0, "No passages found", "Add Passage 1 content")

    p1_content = passages[0]["content"].lower()
    opinion_count = sum(1 for w in _OPINION_WORDS if w in p1_content.split())

    if opinion_count <= 1:
        pct = 100.0
    elif opinion_count <= 3:
        pct = 50.0
    else:
        pct = 0.0

    suggestion = "" if pct == 100 else (
        "Remove opinion language from Passage 1 (argue, claim, believe, contend) — keep it purely factual"
    )
    return CheckScore("P1 factual tone", pct,
                      f"{opinion_count} opinion words in Passage 1 (target ≤1)",
                      suggestion)


def _score_p3_argumentative_tone(passages):
    """G2: Passage 3 argumentative tone — should have ≥3 argument markers."""
    if len(passages) < 3:
        return CheckScore("P3 argumentative tone", 0.0, "No Passage 3 found", "Add Passage 3 content")

    p3_content = passages[2]["content"].lower()
    marker_count = sum(1 for w in _ARGUMENT_MARKERS if re.search(r'\b' + re.escape(w) + r'\b', p3_content))

    if marker_count >= 3:
        pct = 100.0
    elif marker_count >= 1:
        pct = 50.0
    else:
        pct = 0.0

    suggestion = "" if pct == 100 else (
        "Add argument markers to Passage 3 (argue, contend, however, nevertheless, critic, controversial)"
    )
    return CheckScore("P3 argumentative tone", pct,
                      f"{marker_count} argument markers in Passage 3 (target ≥3)",
                      suggestion)


def _score_academic_vocab_density(passages, is_reading=True):
    """G3: Academic vocabulary density — P3/P4 should be higher than P1/P2."""
    if len(passages) < 2:
        return CheckScore("Academic vocabulary density", 100.0, "Not enough passages", "")

    densities = []
    for p in passages:
        words = re.findall(r"[a-z]{3,}", p["content"].lower())
        if not words:
            densities.append(0.0)
            continue
        rare_count = sum(1 for w in words if w not in _BASIC_WORDS)
        densities.append(rare_count / len(words))

    if is_reading:
        # Compare P3 density vs P1 density
        if len(densities) >= 3:
            if densities[2] > densities[0]:
                pct = 100.0
            elif densities[2] == densities[0]:
                pct = 50.0
            else:
                pct = 0.0
            detail = f"P1={densities[0]:.1%}, P3={densities[2]:.1%} rare-word density"
        else:
            pct = 50.0
            detail = "Insufficient passages for comparison"
    else:
        # Compare P4 density vs P1 density
        if len(densities) >= 4:
            if densities[3] > densities[0]:
                pct = 100.0
            elif densities[3] == densities[0]:
                pct = 50.0
            else:
                pct = 0.0
            detail = f"Part1={densities[0]:.1%}, Part4={densities[3]:.1%} rare-word density"
        else:
            pct = 50.0
            detail = "Insufficient scripts for comparison"

    suggestion = "" if pct == 100 else (
        "Use more advanced/academic vocabulary in later passages (P3/P4) vs earlier ones (P1/P2)"
    )
    return CheckScore("Academic vocabulary density", pct, detail, suggestion)


def _score_named_experts(passages):
    """G4: Named experts in P2/P3 — P2 needs ≥2, P3 needs ≥1 theory/study."""
    if len(passages) < 2:
        return CheckScore("Named experts in P2/P3", 0.0, "Not enough passages", "Add Passage 2 and 3")

    p2_count = count_researcher_names(passages[1]["content"]) if len(passages) >= 2 else 0
    p3_has_theory = bool(re.search(
        r"\b(theory|framework|model|hypothesis|study|studies|experiment)\b",
        passages[2]["content"] if len(passages) >= 3 else "",
        re.IGNORECASE,
    ))
    p3_count = count_researcher_names(passages[2]["content"]) if len(passages) >= 3 else 0

    p2_ok = p2_count >= 2
    p3_ok = p3_count >= 1 and p3_has_theory

    if p2_ok and p3_ok:
        pct = 100.0
    elif p2_ok or p3_ok:
        pct = 50.0
    else:
        pct = 0.0

    suggestion = "" if pct == 100 else (
        f"Add named experts: P2 has {p2_count}/2, P3 has {p3_count} researchers"
        + (" and no named theory" if not p3_has_theory else "")
    )
    return CheckScore("Named experts in P2/P3", pct,
                      f"P2: {p2_count} researchers, P3: {p3_count} researchers"
                      + (", theory present" if p3_has_theory else ", no named theory"),
                      suggestion)


def _score_speaker_differentiation(text, scripts_found):
    """H1: Speaker differentiation — Part 1/3 scripts should have speaker labels."""
    parts_to_check = ["Part 1", "Part 3"]
    parts_ok = 0

    for part_name in parts_to_check:
        if part_name in scripts_found:
            script = scripts_found[part_name]
            # Look for speaker labels: M:, W:, Speaker:, Man:, Woman:, etc.
            has_labels = bool(re.search(
                r"^(?:M|W|Man|Woman|Speaker|Tutor|Student|Interviewer|Interviewee|Lecturer)\s*:",
                script, re.MULTILINE | re.IGNORECASE
            ))
            if has_labels:
                parts_ok += 1

    total_parts = len([p for p in parts_to_check if p in scripts_found])
    if total_parts == 0:
        return CheckScore("Speaker differentiation", 100.0, "No dialogue scripts found", "")

    pct = (parts_ok / total_parts) * 100
    suggestion = "" if pct == 100 else (
        "Add speaker labels (M:, W:, Tutor:, etc.) to dialogue scripts in Part 1 and Part 3"
    )
    return CheckScore("Speaker differentiation", pct,
                      f"{parts_ok}/{total_parts} dialogue parts have speaker labels",
                      suggestion)


def _score_chronological_answer_order(text, q_sections, scripts_found, tables):
    """H2: Chronological answer order — Part 1 & 4 answers should follow script order."""
    if not tables or not scripts_found:
        return CheckScore("Chronological answer order", 100.0, "No scripts or tables", "")

    parts_ok = 0
    parts_checked = 0

    for part_name, q_lo, q_hi in [("Part 1", 1, 10), ("Part 4", 31, 40)]:
        if part_name not in scripts_found:
            continue
        parts_checked += 1
        script = scripts_found[part_name]

        # Get completion answers for this part
        all_rows = [r for t in tables for r in t]
        part_answers = []
        for r in all_rows:
            try:
                q_num = int(r["q"])
            except ValueError:
                continue
            if q_lo <= q_num <= q_hi:
                ans = r["answer"].strip()
                if ans.upper() in ("TRUE", "FALSE", "NOT GIVEN", "YES", "NO"):
                    continue
                if re.match(r'^[A-E]$', ans):
                    continue
                part_answers.append((q_num, ans.lower()))

        if len(part_answers) < 2:
            parts_ok += 1  # Not enough answers to check
            continue

        # Check if each answer appears later in the script than the previous one
        positions = []
        for q_num, ans in part_answers:
            pos = script.lower().find(ans)
            positions.append((q_num, pos))

        # Check: position should increase with question number
        is_ordered = True
        for i in range(len(positions) - 1):
            curr_pos = positions[i][1]
            next_pos = positions[i + 1][1]
            if curr_pos >= 0 and next_pos >= 0 and curr_pos > next_pos:
                is_ordered = False
                break

        if is_ordered:
            parts_ok += 1

    if parts_checked == 0:
        return CheckScore("Chronological answer order", 100.0, "No applicable parts found", "")

    pct = (parts_ok / parts_checked) * 100
    suggestion = "" if pct == 100 else (
        "Reorder completion questions so answers appear in the same order as the script/lecture"
    )
    return CheckScore("Chronological answer order", pct,
                      f"{parts_ok}/{parts_checked} parts have chronologically ordered answers",
                      suggestion)


def _score_agreement_tracking(text, scripts_found):
    """H3: Agreement/disagreement tracking — Part 3 should have both."""
    if "Part 3" not in scripts_found:
        return CheckScore("Agreement/disagreement tracking", 100.0, "No Part 3 script found", "")

    p3 = scripts_found["Part 3"]

    has_agreement = any(re.search(p, p3, re.IGNORECASE) for p in _AGREEMENT_PHRASES)
    has_disagreement = any(re.search(p, p3, re.IGNORECASE) for p in _DISAGREEMENT_PHRASES)

    # Also check the existing opinion_change and hedged_language patterns
    if not has_agreement:
        has_agreement = check_opinion_change(p3)  # opinion change implies prior agreement
    if not has_disagreement:
        has_disagreement = check_hedged_language(p3)  # hedging implies disagreement

    if has_agreement and has_disagreement:
        pct = 100.0
    elif has_agreement or has_disagreement:
        pct = 50.0
    else:
        pct = 0.0

    suggestion = "" if pct == 100 else (
        "Add both agreement and disagreement phrases to Part 3 dialogue"
    )
    return CheckScore("Agreement/disagreement tracking", pct,
                      f"Agreement: {'found' if has_agreement else 'missing'}, "
                      f"Disagreement: {'found' if has_disagreement else 'missing'}",
                      suggestion)


# ---------------------------------------------------------------------------
# EXISTING FORMAT CHECK FUNCTIONS
# ---------------------------------------------------------------------------

def check_reading_format(text):
    issues = []
    if not re.search(r"^## READING PASSAGE \d", text, re.MULTILINE):
        issues.append("Missing or wrong heading level: use '## READING PASSAGE N'")
    if not re.search(r"^### Questions \d+[–-]\d+", text, re.MULTILINE):
        issues.append("Missing '### Questions N–M' headings")
    if not re.search(r"^### Answer Key.*Questions \d+[–-]\d+", text, re.MULTILINE):
        issues.append("Missing '### Answer Key — Questions N–M' headings")
    if not re.search(r"\| Q \| Answer \| Needle \|", text):
        issues.append("Answer tables missing '| Q | Answer | Needle |' header")
    return issues


def check_listening_format(text):
    issues = []
    if not re.search(r"^## LISTENING PART \d", text, re.MULTILINE):
        issues.append("Missing or wrong heading level: use '## LISTENING PART N'")
    if not re.search(r"^### Questions \d+[–-]\d+", text, re.MULTILINE):
        issues.append("Missing '### Questions N–M' headings")
    if not re.search(r"\| Q \| Answer \| Needle \|", text):
        issues.append("Answer tables missing '| Q | Answer | Needle |' header")
    return issues


def validate_reading(text, filepath):
    checks = []

    format_issues = check_reading_format(text)
    for issue in format_issues:
        checks.append({"check": "Format: " + issue, "status": "FAIL", "detail": ""})
    if not format_issues:
        checks.append({"check": "Format: heading structure", "status": "PASS", "detail": ""})

    passages = extract_passages(text)
    if not passages:
        p_sections = re.findall(r"### (.+?)\n(.*?)(?=###|\Z)", text, re.DOTALL)
        passages = [{"title": p[0], "content": p[1]} for p in p_sections
                    if p[0] and "Questions" not in p[0] and "Answer" not in p[0]
                    and "Reading Passage" not in p[0]]

    if passages:
        for i, p in enumerate(passages[:3]):
            wc = count_words(p["content"])
            if i == 0:
                spec_range, passed = "700-800", 700 <= wc <= 800
            elif i == 1:
                spec_range, passed = "800-850", 800 <= wc <= 850
            else:
                spec_range, passed = "900+", wc >= 900
            checks.append({
                "check": f"Passage {i+1} word count ({spec_range})",
                "status": "PASS" if passed else "FAIL",
                "detail": f"{wc} words"
            })

        # --- READABILITY CHECKS ---
        passage_texts = [p["content"] for p in passages[:3]]
        read_thresholds = [
            {"min_fre": 60, "label": "FRE > 60 (accessible)"},
            {"min_fre": 40, "max_fre": 70, "label": "FRE 40-70 (moderate)"},
            {"max_fre": 50, "label": "FRE < 50 (challenging academic)"},
        ]
        read_results = validate_readability(passage_texts, read_thresholds)
        for r in read_results:
            checks.append({
                "check": f"Passage {r['index']} readability {r['label']}",
                "status": "PASS" if r["passed"] else "FAIL",
                "detail": r["detail"],
            })

    q_sections = extract_question_sections(text)
    key_sections = extract_answer_key_sections(text)

    body_qs, declared_qs = [], []
    for section in q_sections:
        declared_qs.extend(range(section["start"], section["end"] + 1))
        body_qs.extend(extract_numbered_questions_from_section(section["content"]))

    table_qs = set()
    for t in find_answer_tables(text):
        for r in t:
            try:
                table_qs.add(int(r["q"]))
            except ValueError:
                pass

    all_qs = sorted(set(declared_qs + body_qs + list(table_qs)))
    total_questions = len([q for q in all_qs if 1 <= q <= 40])
    add_check(checks, "Total questions (40)", total_questions == 40,
              f"{total_questions} unique questions found")
    add_check(checks, "Exact question coverage (1-40)", all_qs == list(range(1, 41)),
              f"found {all_qs[:5]}...{all_qs[-5:] if all_qs else []}")
    add_check(checks, "Answer key rows (40)", sorted(table_qs) == list(range(1, 41)),
              f"{len(table_qs)} keyed answers")

    expected_start = 1
    continuous = bool(q_sections)
    range_details = []
    for section in q_sections:
        if section["start"] != expected_start or section["end"] < section["start"]:
            continuous = False
        range_details.append(f"{section['start']}-{section['end']}")
        expected_start = section["end"] + 1
    if expected_start != 41:
        continuous = False
    add_check(checks, "Question ranges continuous", continuous,
              ", ".join(range_details) if range_details else "no question sections found")

    immediate_keys = True
    immediate_details = []
    for i, section in enumerate(q_sections):
        next_key = key_sections[i] if i < len(key_sections) else None
        if not next_key or next_key["start"] != section["start"] or next_key["end"] != section["end"]:
            immediate_keys = False
            immediate_details.append(f"Q{section['start']}-{section['end']}")
        elif next_key["pos"] < section["pos"]:
            immediate_keys = False
            immediate_details.append(f"Q{section['start']}-{section['end']}")
    add_check(checks, "Answer key immediately follows each set",
              immediate_keys and len(q_sections) == len(key_sections),
              "mismatched: " + ", ".join(immediate_details) if immediate_details
              else f"{len(key_sections)} keys")

    passage_types = {1: set(), 2: set(), 3: set()}
    word_limits = {}

    for section in q_sections:
        start, end, content = section["start"], section["end"], section["content"]
        passage = 1 if start <= 13 else (2 if start <= 26 else 3)
        content_lower = content.lower()

        detected = _detect_q_type(content)

        if detected == "tfng":
            passage_types[passage].add("tfng")
        elif detected == "ynng":
            passage_types[passage].add("ynng")
        elif detected == "headings":
            passage_types[passage].add("headings")
        elif detected == "features":
            passage_types[passage].add("features")
        elif detected == "matching_sentence_endings":
            passage_types[passage].add("matching_sentence_endings")
        elif detected == "mcq_single":
            passage_types[passage].add("mcq_single")
        elif detected == "mcq_multiple":
            passage_types[passage].add("mcq_multiple")
        elif detected == "note_completion":
            passage_types[passage].add("note_completion")
        elif detected == "table_completion":
            passage_types[passage].add("table_completion")
        elif detected == "sentence_completion":
            passage_types[passage].add("sentence_completion")
        elif detected == "summary_completion_from_text":
            passage_types[passage].add("summary_completion_from_text")
        elif detected == "summary_completion_from_list":
            passage_types[passage].add("summary_completion_from_list")

        # Also add generic "completion" for any completion subtype (used by per-passage checks)
        if detected in ("note_completion", "table_completion", "sentence_completion",
                        "summary_completion_from_text", "summary_completion_from_list"):
            passage_types[passage].add("completion")

        if detected == "mcq_single" or detected == "mcq_multiple":
            passage_types[passage].add("mcq")

        # Detect word limits for completion questions
        if "complete the" in content_lower or "write no more than" in content_lower:
            limit_match = re.search(r"no more than (one|two|three|four) word", content_lower)
            if limit_match:
                num_map = {"one": 1, "two": 2, "three": 3, "four": 4}
                limit = num_map[limit_match.group(1)]
                if "and/or a number" in content_lower or "or a number" in content_lower:
                    limit += 1
                for q in range(start, end + 1):
                    word_limits[q] = limit
        if "match each statement" in content_lower or "list of people" in content_lower \
                or "list of experts" in content_lower:
            passage_types[passage].add("features")
        if "match each sentence" in content_lower or "sentence endings" in content_lower \
                or "correct ending" in content_lower:
            passage_types[passage].add("sentence_endings")
        if "choose the correct letter" in content_lower:
            passage_types[passage].add("mcq")

        if passage == 1 and "yes" in content_lower and "no" in content_lower \
                and "not given" in content_lower:
            checks.append({"check": "Y/N/NG not in Passage 1", "status": "FAIL",
                           "detail": f"Found in Q{start}-{end}"})
        if passage == 3 and "true" in content_lower and "false" in content_lower \
                and "not given" in content_lower:
            checks.append({"check": "T/F/NG not in Passage 3", "status": "FAIL",
                           "detail": f"Found in Q{start}-{end}"})

        # --- IMPROVED SYNONYM CHECK (v2) ---
        if passages and passage <= len(passages):
            p_content = passages[passage - 1]["content"]
            violations, o3, o4 = check_synonym_rule_v2(p_content, content)
            total_hits = len(o3) + len(o4)
            # Threshold: 0 four-gram hits allowed; up to 1 three-gram hit tolerated
            hard_fail = len(o4) > 0 or len(o3) > 1
            checks.append({
                "check": f"Passage {passage} (Q{start}-{end}) synonym rule",
                "status": "FAIL" if hard_fail else "PASS",
                "detail": " | ".join(violations) if violations else "No content-word overlaps"
            })

    add_check(checks, "Passage 1 required types",
              {"tfng", "completion"}.issubset(passage_types[1]),
              ", ".join(sorted(passage_types[1])))
    # P2: needs at least one matching type + MCQ Multiple + completion
    p2_has_matching = bool(passage_types[2] & {"headings", "features", "matching_sentence_endings"})
    p2_has_mcq_multi = "mcq_multiple" in passage_types[2]
    p2_has_completion = "completion" in passage_types[2]
    add_check(checks, "Passage 2 required types (matching + MCQ Multiple + completion)",
              p2_has_matching and p2_has_mcq_multi and p2_has_completion,
              ", ".join(sorted(passage_types[2])))
    add_check(checks, "Passage 3 required types",
              {"ynng", "mcq", "completion"}.issubset(passage_types[3]),
              ", ".join(sorted(passage_types[3])))

    # --- GLOBAL TYPE COVERAGE CHECK ---
    global_types = set()
    for p in passage_types:
        global_types.update(passage_types[p])
    required_global = {"tfng", "ynng", "mcq_single", "mcq_multiple",
                       "note_completion", "sentence_completion",
                       "summary_completion_from_text", "summary_completion_from_list",
                       "table_completion"}
    matching_used = global_types & {"headings", "features", "matching_sentence_endings"}
    missing_global = required_global - global_types
    if missing_global:
        add_check(checks, "Global type coverage (all 9 non-matching types + 1 matching)",
                  False, f"Missing: {', '.join(sorted(missing_global))}")
    elif len(matching_used) != 1:
        add_check(checks, "Global type coverage (all 9 non-matching types + 1 matching)",
                  False, f"Matching types used: {', '.join(matching_used)} (need exactly 1)")
    else:
        add_check(checks, "Global type coverage (all 9 non-matching types + 1 matching)",
                  True, f"All present | Matching: {', '.join(matching_used)}")

    # --- QUESTION DIFFICULTY PROGRESSION (Reading) ---
    _q_by_p = {}
    for p_idx in range(1, 4):
        p_sections = [s for s in q_sections if
                      (p_idx == 1 and s["start"] <= 13) or
                      (p_idx == 2 and 14 <= s["start"] <= 26) or
                      (p_idx == 3 and s["start"] >= 27)]
        _q_list = []
        for section in p_sections:
            section_text = _strip_q_boilerplate(section["content"])
            if len(section_text.split()) < 3:
                continue  # skip sections with only boilerplate
            sec_type = _detect_q_type(section["content"])
            _q_list.append({"text": section_text, "type": sec_type})
        _q_by_p[p_idx] = _q_list

    if any(_q_by_p.values()):
        _q_result = _check_q_diff(_q_by_p, "Reading")
        add_check(checks, "Progressive question difficulty (P1 < P2 < P3)",
                  _q_result["passed"], _q_result["detail"])

    tables = find_answer_tables(text)
    total_answers = sum(len(t) for t in tables)
    checks.append({
        "check": "Answer keys present with Needle column",
        "status": "PASS" if tables else "FAIL",
        "detail": f"{len(tables)} answer key tables found ({total_answers} total answers)"
    })

    if tables:
        no_needle = [r for t in tables for r in t if not r["needle"].strip()]
        checks.append({
            "check": "All answers have Needle entries",
            "status": "PASS" if not no_needle else "FAIL",
            "detail": f"{len(no_needle)} answers missing needle"
        })

        if passages:
            needles_missing = []
            for t in tables:
                for r in t:
                    if r["needle"].strip():
                        try:
                            q_num = int(r["q"])
                            # Skip NOT GIVEN needles — they contain absence notes, not passage quotes
                            if r["answer"].strip().upper() == "NOT GIVEN":
                                continue
                            # Try to extract the main quoted segment
                            quoted = re.findall(r'"([^"]+)"', r["needle"])
                            if quoted:
                                clean_needle = quoted[0]
                            else:
                                # Use text before any commentary (before —, –, ;, etc.)
                                clean_needle = re.split(r'\s*[—–;]\s*', r["needle"].strip())[0]
                            # Strip markdown bold markers and normalize whitespace
                            clean_needle = re.sub(r'\*\*', '', clean_needle)
                            clean_needle = re.sub(r'\s+', ' ', clean_needle).strip()
                            p_content = " ".join(
                                " ".join(p["content"].split()) for p in passages
                            ).lower()
                            # Strip bold markers from passage text too
                            p_content = re.sub(r'\*\*', '', p_content)
                            n_content = " ".join(clean_needle.split()).lower()
                            # Split on ellipsis or em-dash — take longest part (discard commentary)
                            n_parts = re.split(r'\.{3,}|\s*[—–]\s*', n_content)
                            best_part = max(n_parts, key=lambda s: len(s.strip())).strip()
                            if len(best_part) > 5 and best_part not in p_content:
                                needles_missing.append(f"Q{q_num}")
                        except ValueError:
                            pass
            checks.append({
                "check": "Needles found in passage text",
                "status": "PASS" if not needles_missing else "FAIL",
                "detail": f"{len(needles_missing)} needles not found: "
                          f"{', '.join(needles_missing[:5])}" if needles_missing else "All found"
            })

        if word_limits:
            violations = []
            for t in tables:
                for r in t:
                    try:
                        q_num = int(r["q"])
                        if q_num in word_limits:
                            ans_words = len([w for w in r["answer"].split() if w.strip()])
                            if ans_words > word_limits[q_num]:
                                violations.append(
                                    f"Q{q_num} (limit {word_limits[q_num]}, got {ans_words})"
                                )
                    except ValueError:
                        pass
            checks.append({
                "check": "Completion word limits respected",
                "status": "PASS" if not violations else "FAIL",
                "detail": f"{len(violations)} violations: {', '.join(violations[:5])}"
                if violations else "All within limits"
            })

        tfng_counts = {p: {"T": 0, "F": 0, "NG": 0} for p in [1, 2, 3]}
        ynng_counts = {p: {"Y": 0, "N": 0, "NG": 0} for p in [1, 2, 3]}
        for t in tables:
            for r in t:
                try:
                    q_num = int(r["q"])
                    p_idx = 1 if q_num <= 13 else (2 if q_num <= 26 else 3)
                    ans = r["answer"].strip().upper()
                    if ans == "TRUE":          tfng_counts[p_idx]["T"] += 1
                    elif ans == "FALSE":       tfng_counts[p_idx]["F"] += 1
                    elif ans == "YES":         ynng_counts[p_idx]["Y"] += 1
                    elif ans == "NO":          ynng_counts[p_idx]["N"] += 1
                    elif ans == "NOT GIVEN":
                        if "tfng" in passage_types[p_idx]:
                            tfng_counts[p_idx]["NG"] += 1
                        if "ynng" in passage_types[p_idx]:
                            ynng_counts[p_idx]["NG"] += 1
                except ValueError:
                    pass

        tfng_violations = []
        for p in [1, 2, 3]:
            if "tfng" in passage_types[p]:
                c = tfng_counts[p]
                if c["T"] < 2 or c["F"] < 2 or c["NG"] < 2:
                    tfng_violations.append(f"P{p} T/F/NG (need ≥2 each): {c}")
            if "ynng" in passage_types[p]:
                c = ynng_counts[p]
                if c["Y"] < 1 or c["N"] < 1 or c["NG"] < 1:
                    tfng_violations.append(f"P{p} Y/N/NG: {c}")
        checks.append({
            "check": "Boolean distribution (≥2 TRUE, 2 FALSE, 2 NG for T/F/NG)",
            "status": "PASS" if not tfng_violations else "FAIL",
            "detail": ", ".join(tfng_violations) if tfng_violations else "All distributions OK"
        })

        ng_without_absence_note = [
            r for t in tables for r in t
            if r["answer"].strip().upper() == "NOT GIVEN"
            and not re.search(
                r"\b(does not|not mention|not mentioned|not stated|not described"
                r"|no information|no statement|impossible to say|never discussed"
                r"|absent from|nowhere in)\b",
                r["needle"], re.IGNORECASE,
            )
        ]
        checks.append({
            "check": "NOT GIVEN uses absence note",
            "status": "PASS" if not ng_without_absence_note else "FAIL",
            "detail": f"{len(ng_without_absence_note)} weak NOT GIVEN needles"
        })

    return checks


def validate_listening(text, filepath):
    checks = []

    format_issues = check_listening_format(text)
    for issue in format_issues:
        checks.append({"check": "Format: " + issue, "status": "FAIL", "detail": ""})
    if not format_issues:
        checks.append({"check": "Format: heading structure", "status": "PASS", "detail": ""})

    scripts = extract_scripts(text)
    scripts_found = {s["part"]: s["content"] for s in scripts}

    # Extract question sections early (needed by Part 4 synonym check + difficulty check)
    q_sections = extract_question_sections(text)

    spec_ranges = {
        "Part 1": (250, 300), "Part 2": (350, 400),
        "Part 3": (400, 450), "Part 4": (800, 900)
    }
    for part, (lo, hi) in spec_ranges.items():
        if part in scripts_found:
            wc = count_words(scripts_found[part])
            checks.append({
                "check": f"{part} script length ({lo}-{hi} words)",
                "status": "PASS" if lo <= wc <= hi else "FAIL",
                "detail": f"{wc} words"
            })
        else:
            checks.append({
                "check": f"{part} script found",
                "status": "FAIL",
                "detail": "Not found in file"
            })

    # --- LISTENING READABILITY CHECKS ---
    listen_part_order = ["Part 1", "Part 2", "Part 3", "Part 4"]
    listen_thresholds = [
        {"min_fre": 65, "label": "FRE > 65 (conversational)"},
        {"min_fre": 50, "max_fre": 75, "label": "FRE 50-75 (moderate)"},
        {"min_fre": 40, "max_fre": 65, "label": "FRE 40-65 (academic discussion)"},
        {"max_fre": 50, "label": "FRE < 50 (academic lecture)"},
    ]
    for part_name, threshold in zip(listen_part_order, listen_thresholds):
        if part_name in scripts_found:
            script_text = scripts_found[part_name]
            fre = flesch_reading_ease(script_text)
            cli = coleman_liau_index(script_text)
            band = estimate_ielts_band(fre)
            min_fre = threshold.get("min_fre", 0)
            max_fre = threshold.get("max_fre", 100)
            passed = min_fre <= fre <= max_fre
            detail = f"FRE={fre:.1f}, CLI={cli:.1f}, est_band={band['band']}"
            if not passed:
                if fre < min_fre:
                    detail += f" (below min {min_fre})"
                if fre > max_fre:
                    detail += f" (above max {max_fre})"
            checks.append({
                "check": f"{part_name} readability {threshold['label']}",
                "status": "PASS" if passed else "FAIL",
                "detail": detail,
            })

    if "Part 1" in scripts_found:
        p1 = scripts_found["Part 1"]
        checks.append({"check": "Part 1: Spelling trap (e.g., M-U-R-R-A-Y)",
                       "status": "PASS" if check_spelling_trap(p1) else "FAIL",
                       "detail": "Found" if check_spelling_trap(p1) else "Not found"})
        checks.append({"check": "Part 1: Self-correction",
                       "status": "PASS" if check_self_correction(p1) else "FAIL",
                       "detail": "Found" if check_self_correction(p1) else "Not found"})
        checks.append({"check": "Part 1: Distractor (alternative rejected)",
                       "status": "PASS" if check_distractor(p1) else "FAIL",
                       "detail": "Found" if check_distractor(p1) else "Not found"})

    if "Part 3" in scripts_found:
        p3 = scripts_found["Part 3"]
        checks.append({"check": "Part 3: Opinion change",
                       "status": "PASS" if check_opinion_change(p3) else "FAIL",
                       "detail": "Found" if check_opinion_change(p3) else "Not found"})
        checks.append({"check": "Part 3: Hedged language",
                       "status": "PASS" if check_hedged_language(p3) else "FAIL",
                       "detail": "Found" if check_hedged_language(p3) else "Not found"})

    if "Part 4" in scripts_found:
        p4 = scripts_found["Part 4"]
        researchers = count_researcher_names(p4)
        checks.append({"check": "Part 4: Named researchers (≥3)",
                       "status": "PASS" if researchers >= 3 else "FAIL",
                       "detail": f"{researchers} found"})
        checks.append({"check": "Part 4: Signpost language",
                       "status": "PASS" if check_signpost_language(p4) else "FAIL",
                       "detail": "Found" if check_signpost_language(p4) else "Not found"})

        # --- IMPROVED SYNONYM CHECK for Listening Part 4 (lecture) ---
        # Extract corresponding questions (Q31-40)
        p4_q_text = " ".join(
            s["content"] for s in q_sections if s["start"] >= 31
        )
        if p4_q_text:
            violations, o3, o4 = check_synonym_rule_v2(p4, p4_q_text)
            hard_fail = len(o4) > 0 or len(o3) > 1
            checks.append({
                "check": "Part 4 lecture synonym rule (Q31-40)",
                "status": "FAIL" if hard_fail else "PASS",
                "detail": " | ".join(violations) if violations else "No overlaps"
            })

    numbered = extract_questions(text)
    gaps = count_gap_questions(text)
    table_qs = set()
    for t in find_answer_tables(text):
        for r in t:
            try:
                table_qs.add(int(r["q"]))
            except ValueError:
                pass
    all_qs = sorted(set(numbered + gaps + list(table_qs)))
    total = len([q for q in all_qs if 1 <= q <= 40])
    checks.append({
        "check": "Listening total questions (40)",
        "status": "PASS" if total == 40 else "FAIL",
        "detail": f"{total} found"
    })

    tables = find_answer_tables(text)
    total_answers = sum(len(t) for t in tables)
    checks.append({
        "check": "Answer keys present with Needle column",
        "status": "PASS" if tables else "FAIL",
        "detail": f"{len(tables)} answer key tables ({total_answers} answers)"
    })

    if tables:
        no_needle = [r for t in tables for r in t if not r["needle"].strip()]
        checks.append({
            "check": "All answers have Needle entries",
            "status": "PASS" if not no_needle else "FAIL",
            "detail": f"{len(no_needle)} answers missing needle"
        })

    # --- QUESTION DIFFICULTY PROGRESSION (Listening) ---
    _l_q_by_p = {}
    for p_idx in range(1, 5):
        if p_idx == 1:
            lo, hi = 1, 10
        elif p_idx == 2:
            lo, hi = 11, 20
        elif p_idx == 3:
            lo, hi = 21, 30
        else:
            lo, hi = 31, 40
        p_sections = [s for s in q_sections
                      if s["start"] >= lo and s["end"] <= hi]
        _q_list = []
        for section in p_sections:
            section_text = _strip_q_boilerplate(section["content"])
            if len(section_text.split()) < 3:
                continue
            sec_type = _detect_q_type(section["content"])
            _q_list.append({"text": section_text, "type": sec_type})
        _l_q_by_p[p_idx] = _q_list

    if any(_l_q_by_p.values()):
        _l_q_result = _check_q_diff(_l_q_by_p, "Listening")
        add_check(checks, "Progressive question difficulty (P1 < P2 < P3 < P4)",
                  _l_q_result["passed"], _l_q_result["detail"])

    return checks


# ---------------------------------------------------------------------------
# OFFICIAL STANDARD SCORE — orchestrator
# ---------------------------------------------------------------------------

def _score_existing_checks_by_category(checks, category_letter):
    """Convert existing PASS/FAIL checks mapped to a category into a 0-100 score."""
    relevant = [c for c in checks if _map_check_to_category(c["check"]) == category_letter]
    if not relevant:
        return 100.0, []   # no checks = assume OK
    passed = sum(1 for c in relevant if c["status"] == "PASS")
    pct = (passed / len(relevant)) * 100
    sub_scores = [
        CheckScore(c["check"], 100.0 if c["status"] == "PASS" else 0.0, c["detail"])
        for c in relevant
    ]
    return pct, sub_scores


def compute_official_score(text, checks, is_reading=True):
    """
    Compute the Official Standard Score (0-100%) from existing checks + new scoring checks.

    Args:
        text: full markdown text of the test
        checks: list of existing PASS/FAIL check dicts
        is_reading: True for Reading, False for Listening

    Returns:
        OfficialScore dataclass
    """
    weights = _CATEGORY_WEIGHTS_READING if is_reading else _CATEGORY_WEIGHTS_LISTENING
    categories = []

    # Extract shared data
    passages = extract_passages(text) if is_reading else []
    scripts = extract_scripts(text)
    scripts_found = {s["part"]: s["content"] for s in scripts}
    q_sections = extract_question_sections(text)
    tables = find_answer_tables(text)

    # ---- Category A: Structure & Format ----
    a_pct, a_subs = _score_existing_checks_by_category(checks, "A")
    a_new = _score_mcq_option_format(text, q_sections)
    a_subs.append(a_new)
    a_pct = sum(s.percentage for s in a_subs) / len(a_subs) if a_subs else 100.0
    categories.append(CategoryScore("Structure & Format", "A", weights.get("A", 15), a_pct, a_subs))

    # ---- Category B: Readability & Progression ----
    b_pct, b_subs = _score_existing_checks_by_category(checks, "B")
    # B1: within-passage QDS progression
    b_subs.append(_score_within_passage_qds(text, q_sections, passages if is_reading else [], is_reading))
    # B2: FRE gap between passages
    if is_reading:
        passage_texts = [p["content"] for p in passages[:3]] if passages else []
    else:
        passage_texts = [scripts_found.get(f"Part {i}", "") for i in range(1, 5)]
        passage_texts = [t for t in passage_texts if t]
    b_subs.append(_score_fre_gap(passage_texts, is_reading))
    # B3: CLI cross-check
    b_subs.append(_score_cli_crosscheck(passage_texts))
    b_pct = sum(s.percentage for s in b_subs) / len(b_subs) if b_subs else 100.0
    categories.append(CategoryScore("Readability & Progression", "B", weights.get("B", 12), b_pct, b_subs))

    # ---- Category C: Question Type Compliance ----
    c_pct, c_subs = _score_existing_checks_by_category(checks, "C")
    c_subs.append(_score_min_types_per_passage(q_sections, is_reading))
    c_subs.append(_score_matching_extra_options(text, q_sections))
    c_subs.append(_score_mcq_multi_consistency(text, q_sections, tables))
    c_pct = sum(s.percentage for s in c_subs) / len(c_subs) if c_subs else 100.0
    categories.append(CategoryScore("Question Type Compliance", "C", weights.get("C", 18), c_pct, c_subs))

    # ---- Category D: Synonym Rule ----
    d_pct, d_subs = _score_existing_checks_by_category(checks, "D")
    # D1 & D2: Additional overlap metrics for each passage/part
    if is_reading:
        for p_idx, p in enumerate(passages[:3], 1):
            p_q_text = " ".join(
                s["content"] for s in q_sections
                if (p_idx == 1 and s["start"] <= 13) or
                   (p_idx == 2 and 14 <= s["start"] <= 26) or
                   (p_idx == 3 and s["start"] >= 27)
            )
            if p_q_text and p["content"]:
                d_subs.append(_score_2gram_overlap(p["content"], p_q_text))
                d_subs.append(_score_unigram_overlap(p["content"], p_q_text))
    else:
        if "Part 4" in scripts_found:
            p4_q_text = " ".join(s["content"] for s in q_sections if s["start"] >= 31)
            if p4_q_text:
                d_subs.append(_score_2gram_overlap(scripts_found["Part 4"], p4_q_text))
                d_subs.append(_score_unigram_overlap(scripts_found["Part 4"], p4_q_text))
    d_pct = sum(s.percentage for s in d_subs) / len(d_subs) if d_subs else 100.0
    categories.append(CategoryScore("Synonym Rule", "D", weights.get("D", 15), d_pct, d_subs))

    # ---- Category E: Distractor & Trap Quality ----
    e_pct, e_subs = _score_existing_checks_by_category(checks, "E")
    e_subs.append(_score_mcq_distractor_vocab(text, q_sections, passages if is_reading else []))
    e_subs.append(_score_tfng_trap_density(text, q_sections, tables))
    e_pct = sum(s.percentage for s in e_subs) / len(e_subs) if e_subs else 100.0
    categories.append(CategoryScore("Distractor & Trap Quality", "E", weights.get("E", 12), e_pct, e_subs))

    # ---- Category F: Needle & Answer Quality ----
    f_pct, f_subs = _score_existing_checks_by_category(checks, "F")
    f_subs.append(_score_needle_precision(tables))
    if is_reading:
        f_subs.append(_score_completion_verbatim(text, q_sections, passages, tables))
    else:
        # For listening, use scripts as the source for verbatim check
        f_subs.append(_score_completion_verbatim(text, q_sections,
                                                  [{"title": f"Part {i}", "content": scripts_found.get(f"Part {i}", "")}
                                                   for i in range(1, 5)], tables))
    f_subs.append(_score_answer_uniqueness(tables))
    f_pct = sum(s.percentage for s in f_subs) / len(f_subs) if f_subs else 100.0
    categories.append(CategoryScore("Needle & Answer Quality", "F", weights.get("F", 12), f_pct, f_subs))

    # ---- Category G: Content & Tone Quality ----
    if is_reading and passages:
        g_subs = [
            _score_p1_factual_tone(passages),
            _score_p3_argumentative_tone(passages),
            _score_academic_vocab_density(passages, is_reading=True),
            _score_named_experts(passages),
        ]
    elif not is_reading and scripts_found:
        # For listening: check script tone (P1 conversational, P4 academic)
        listen_passages = [
            {"title": f"Part {i}", "content": scripts_found.get(f"Part {i}", "")}
            for i in range(1, 5)
        ]
        g_subs = [
            _score_p1_factual_tone(listen_passages),  # Part 1 should be simple/conversational
            _score_p3_argumentative_tone(listen_passages),  # Part 3 should be discursive
            _score_academic_vocab_density(listen_passages, is_reading=False),
            _score_named_experts(listen_passages),  # Part 4 needs researchers
        ]
    else:
        g_subs = [
            CheckScore("P1 factual tone", 0.0, "No passages found", "Add passage content"),
            CheckScore("P3 argumentative tone", 0.0, "No passages found", "Add passage content"),
            CheckScore("Academic vocab density", 0.0, "No passages found", ""),
            CheckScore("Named experts", 0.0, "No passages found", ""),
        ]
    g_pct = sum(s.percentage for s in g_subs) / len(g_subs) if g_subs else 100.0
    categories.append(CategoryScore("Content & Tone Quality", "G", weights.get("G", 8), g_pct, g_subs))

    # ---- Category H: Listening-Specific (only for Listening) ----
    if not is_reading:
        h_pct, h_subs = _score_existing_checks_by_category(checks, "E")  # reuse some E checks
        h_subs = [
            _score_speaker_differentiation(text, scripts_found),
            _score_chronological_answer_order(text, q_sections, scripts_found, tables),
            _score_agreement_tracking(text, scripts_found),
        ]
        h_pct = sum(s.percentage for s in h_subs) / len(h_subs) if h_subs else 100.0
        categories.append(CategoryScore("Listening-Specific", "H", weights.get("H", 8), h_pct, h_subs))

    # ---- Compute overall score ----
    total_weight = sum(c.weight for c in categories)
    overall = sum(c.weight * c.percentage for c in categories) / max(1, total_weight)

    # ---- Generate action items for weakest categories ----
    weak = [c for c in categories if c.percentage < 85]
    weak.sort(key=lambda c: c.percentage)
    action_items = []
    for c in weak[:3]:  # top 3 weakest
        # Find the worst sub-check with a suggestion
        worst = min(c.checks, key=lambda s: s.percentage)
        if worst.suggestion:
            action_items.append(f"{c.letter}: {c.name} ({c.percentage:.0f}%) — {worst.suggestion}")
        else:
            action_items.append(f"{c.letter}: {c.name} ({c.percentage:.0f}%) — review and improve")

    grade, grade_label = _grade_for_score(overall)
    return OfficialScore(overall, grade, grade_label, categories, action_items)


def _print_score_breakdown(score: OfficialScore):
    """Print a visual score breakdown after validation results."""
    width = 62
    print(f"\n{'═' * width}")
    print(f"  OFFICIAL STANDARD SCORE")
    print(f"{'═' * width}")

    for cat in score.categories:
        # Build bar: 20 chars wide, filled proportionally
        filled = int(cat.percentage / 100 * 20)
        bar = "█" * filled + "░" * (20 - filled)
        icon = "✓" if cat.percentage >= 85 else ("⚠" if cat.percentage >= 50 else "✗")
        print(f"  {cat.letter}  {cat.name:<24s} {bar} {cat.percentage:>5.1f}% {icon}")

    print(f"{'─' * width}")
    grade_color = {
        "A+": "★★★", "A": "★★", "B": "★", "C": "", "D": ""
    }.get(score.grade, "")
    print(f"  OVERALL: {score.overall_percentage:.1f}% — Grade {score.grade} {grade_color}")
    print(f"  {score.grade_label}")

    if score.action_items:
        print(f"\n  Action items:")
        for item in score.action_items:
            print(f"  • {item}")

    print(f"{'═' * width}\n")


def run_validation(filepath, json_output=False, score_only=False, no_score=False):
    text = read_file(filepath)
    name = Path(filepath).name

    is_reading = "READING PASSAGE" in text or "Reading Passage" in text
    is_listening = "LISTENING PART" in text or "Listening Part" in text

    if is_reading:
        checks = validate_reading(text, filepath)
    elif is_listening:
        checks = validate_listening(text, filepath)
    else:
        if json_output:
            return {"file": name, "error": "Could not determine test type", "passed": False}
        print("ERROR: Could not determine test type (Reading or Listening)")
        return False

    passed = failed = info = 0
    for c in checks:
        status = c["status"]
        if status == "PASS":
            passed += 1
        elif status == "FAIL":
            failed += 1
        else:
            info += 1

    # Compute Official Standard Score
    official_score = None
    if not no_score:
        official_score = compute_official_score(text, checks, is_reading)

    if json_output:
        result = {
            "file": name,
            "passed": failed == 0,
            "checks": checks,
            "summary": {"passed": passed, "failed": failed, "info": info},
        }
        if official_score:
            result["official_score"] = official_score.to_dict()
        return result

    # Human-readable output
    if not score_only:
        print(f"\n{'='*62}")
        print(f"  VALIDATING: {name}")
        print(f"{'='*62}")
        for c in checks:
            status = c["status"]
            icon = "✓" if status == "PASS" else ("✗" if status == "FAIL" else "~")
            print(f"  {icon} {c['check']:<48s} {status:<5s}  {c['detail']}")
        print(f"\n{'─'*62}")
        print(f"  RESULTS:  {passed} passed  |  {failed} failed  |  {info} info")
        print(f"{'─'*62}")

    # Print score breakdown
    if official_score:
        _print_score_breakdown(official_score)
    elif not score_only:
        print()

    return failed == 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/validate.py [--json] [--score-only] [--no-score] <file.md> [...]")
        sys.exit(1)

    json_output = "--json" in sys.argv
    score_only = "--score-only" in sys.argv
    no_score = "--no-score" in sys.argv
    args = [a for a in sys.argv[1:] if a not in ("--json", "--score-only", "--no-score")]

    if json_output:
        results = []
        for arg in args:
            path = Path(arg)
            if path.exists():
                results.append(run_validation(path, json_output=True,
                                              score_only=score_only, no_score=no_score))
            else:
                results.append({"file": arg, "error": "File not found", "passed": False})
        print(json.dumps(results, indent=2))
        sys.exit(0 if all(r.get("passed", False) for r in results) else 1)

    all_pass = True
    for arg in args:
        path = Path(arg)
        if path.exists():
            if not run_validation(path, score_only=score_only, no_score=no_score):
                all_pass = False
        else:
            print(f"File not found: {arg}")
            all_pass = False

    sys.exit(0 if all_pass else 1)
