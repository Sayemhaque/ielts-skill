#!/usr/bin/env python3
"""
IELTS Test Validator
Validates generated Reading and Listening tests against spec rules.
Usage:  python3 scripts/validate.py <file.md>
"""

import json
import re
import sys
from pathlib import Path

# Allow local imports from scripts/
sys.path.insert(0, str(Path(__file__).resolve().parent))
from readability import flesch_reading_ease, coleman_liau_index, estimate_ielts_band, validate_readability
from question_difficulty import validate_progressive_difficulty as _check_q_diff

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


def run_validation(filepath, json_output=False):
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

    if json_output:
        return {
            "file": name,
            "passed": failed == 0,
            "checks": checks,
            "summary": {"passed": passed, "failed": failed, "info": info},
        }

    # Human-readable output
    print(f"\n{'='*62}")
    print(f"  VALIDATING: {name}")
    print(f"{'='*62}")
    for c in checks:
        status = c["status"]
        icon = "✓" if status == "PASS" else ("✗" if status == "FAIL" else "~")
        print(f"  {icon} {c['check']:<48s} {status:<5s}  {c['detail']}")
    print(f"\n{'─'*62}")
    print(f"  RESULTS:  {passed} passed  |  {failed} failed  |  {info} info")
    print(f"{'─'*62}\n")
    return failed == 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/validate.py [--json] <file1.md> [file2.md ...]")
        sys.exit(1)

    json_output = "--json" in sys.argv
    args = [a for a in sys.argv[1:] if a != "--json"]

    if json_output:
        results = []
        for arg in args:
            path = Path(arg)
            if path.exists():
                results.append(run_validation(path, json_output=True))
            else:
                results.append({"file": arg, "error": "File not found", "passed": False})
        print(json.dumps(results, indent=2))
        sys.exit(0 if all(r.get("passed", False) for r in results) else 1)

    all_pass = True
    for arg in args:
        path = Path(arg)
        if path.exists():
            if not run_validation(path):
                all_pass = False
        else:
            print(f"File not found: {arg}")
            all_pass = False

    sys.exit(0 if all_pass else 1)
