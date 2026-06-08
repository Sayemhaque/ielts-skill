#!/usr/bin/env python3
"""
IELTS Test Validator
Validates generated Reading and Listening tests against spec rules.
Usage:  python3 scripts/validate.py <file.md>
"""

import re
import sys
from pathlib import Path


def read_file(path):
    with open(path) as f:
        return f.read()


def extract_sections(text, level="###"):
    """Split markdown into sections by heading level."""
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
    """Find markdown answer key tables and return list of question->answer mappings."""
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
    for line in lines[2:]:  # skip header and separator
        line = line.strip()
        if line.startswith("|") and line.endswith("|"):
            cells = [c.strip() for c in line.split("|")[1:-1]]
            if len(cells) >= 3:
                rows.append({"q": cells[0], "answer": cells[1], "needle": cells[2]})
    return rows


def find_matching_word_list(text):
    """Find 'Word list' or 'List of' sections to count options."""
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
    """Count numbered questions in form X. content"""
    questions = re.findall(r"^(\d+)\.", text, re.MULTILINE)
    return [int(q) for q in questions]


def count_gap_questions(text):
    """Count gap questions in note/summary completion ( (N) ___ )."""
    gaps = re.findall(r"\((\d+)\)\s*_{3,}", text)
    return [int(g) for g in gaps]


def extract_passages(text):
    """Extract passage content for reading tests.
    
    Uses ## READING PASSAGE N headings as passage boundaries.
    Collects all text between consecutive passage headings, stopping
    before the next ## READING PASSAGE or before ### Questions/Answer.
    """
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
                # If this was also a new passage start, handle it on next iteration
                continue
            # Skip ## and # lines (passage/script headings)
            if content_filter.match(stripped):
                # But include ### paragraph labels (like ### A, ### B in P2)
                # that are inside the passage and followed by text
                next_in_passage = False  # We don't know, just include them
                if stripped and len(stripped) > 3:  # non-empty heading
                    current.append(line)
            elif stripped and (len(stripped) > 20 or stripped.startswith("**")):
                current.append(line)
    if in_passage and current:
        passages.append({"title": title, "content": "\n".join(current)})
    return passages


def extract_scripts(text):
    """Extract listening script sections."""
    scripts = []
    for m in re.finditer(r"### Script: (Part \d+)\s*\n(.*?)(?=---|\Z)", text, re.DOTALL):
        scripts.append({"part": m.group(1), "content": m.group(2).strip()})
    return scripts


def check_spelling_trap(text):
    """Check for hyphenated spelling patterns like M-U-R-R-A-Y."""
    return bool(re.search(r"[A-Z](?:-[A-Z]){2,}", text))


def check_self_correction(text):
    """Check for self-correction patterns."""
    patterns = [
        r"no\s*[,!]?\s*(wait|sorry|actually|correction|let me)",
        r"sorry[,!]\s",
        r"that['']s\s+\w+,\s+not\s+",
        r"actually.*?\d+.*?no",
        r"\d+\s*\.{3,}\s*no\s+wait",
    ]
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)


def check_distractor(text):
    """Check for alternative options mentioned then rejected."""
    patterns = [
        r"also.*?(?:popular|many|other).*?(?:but|however|actually)",
        r"(?:instead of|rather than)",
        r"you could also.*?(?:but|however)",
    ]
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)


def check_opinion_change(text):
    """Check for opinion change patterns in Part 3."""
    patterns = [
        r"you['']?ve convinced me",
        r"you know what.*?actually",
        r"I think you['']?re right",
        r"that['']?s a (?:fair|good) point",
        r"actually.*?I (?:think|agree)",
    ]
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)


def check_hedged_language(text):
    """Check for hedged/academic language."""
    patterns = [
        r"I['']m not entirely convinced",
        r"that['']?s a fair point",
        r"I['']d argue",
        r"that['']?s possible",
        r"I see what you mean",
    ]
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)


def check_signpost_language(text):
    """Check for lecture signpost language."""
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
    """Count named researchers in Part 4 script."""
    # Match titled researchers
    titled = r"(?:Dr|Professor|Sir)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?"
    names = set(re.findall(titled, text))
    # Match full names without titles (e.g., "Daniel Kahneman")
    full_names = r"[A-Z][a-z]+\s+[A-Z][a-z]+"
    all_names = re.findall(full_names, text)
    # Filter out non-researcher names (locations, generic terms)
    researcher_keywords = {"Kahneman", "Tversky", "Thaler", "Sunstein", "Tononi",
                          "Blackmore", "Dennett", "Marchetti", "Tanaka", "Santos",
                          "Rahman", "Cross"}
    for name in all_names:
        parts = name.split()
        if parts[-1] in researcher_keywords or any(kw in name for kw in [" researcher", " scientist", " professor"]):
            names.add(name)
    return len(names)


def check_synonym_rule(source_text, questions_text):
    """Basic synonym check - find exact multi-word overlaps between source and questions."""
    source_words = set(re.findall(r"\b[a-z]{4,}\b", source_text.lower()))
    question_words = set(re.findall(r"\b[a-z]{4,}\b", questions_text.lower()))
    # Remove common function words
    common = {"this", "that", "with", "from", "which", "what", "when", "where", "there",
              "their", "they", "have", "been", "were", "would", "could", "should", "about",
              "between", "through", "after", "before", "other", "than", "more", "some"}
    source_words -= common
    question_words -= common
    overlap = source_words & question_words
    return len(overlap), overlap


def check_reading_format(text):
    """Check structural format of reading test."""
    issues = []
    lines = text.split("\n")
    # Check for ## READING PASSAGE N (not ###)
    if not re.search(r"^## READING PASSAGE \d", text, re.MULTILINE):
        issues.append("Missing or wrong heading level: use '## READING PASSAGE N'")
    # Check for ### Questions with en-dash
    if not re.search(r"^### Questions \d+[–-]\d+", text, re.MULTILINE):
        issues.append("Missing '### Questions N–M' headings")
    # Check for ### Answer Key with en-dash
    if not re.search(r"^### Answer Key.*Questions \d+[–-]\d+", text, re.MULTILINE):
        issues.append("Missing '### Answer Key — Questions N–M' headings")
    # Check answer tables have proper format
    if not re.search(r"\| Q \| Answer \| Needle \|", text):
        issues.append("Answer tables missing '| Q | Answer | Needle |' header")
    return issues


def check_listening_format(text):
    """Check structural format of listening test."""
    issues = []
    # Check for ## LISTENING PART N (not ###)
    if not re.search(r"^## LISTENING PART \d", text, re.MULTILINE):
        issues.append("Missing or wrong heading level: use '## LISTENING PART N'")
    # Check for ### Questions with en-dash
    if not re.search(r"^### Questions \d+[–-]\d+", text, re.MULTILINE):
        issues.append("Missing '### Questions N–M' headings")
    # Check answer tables
    if not re.search(r"\| Q \| Answer \| Needle \|", text):
        issues.append("Answer tables missing '| Q | Answer | Needle |' header")
    return issues


def validate_reading(text, filepath):
    checks = []
    total_questions = 0

    # Structural format checks
    format_issues = check_reading_format(text)
    for issue in format_issues:
        checks.append({"check": "Format: " + issue, "status": "FAIL", "detail": ""})
    if not format_issues:
        checks.append({"check": "Format: heading structure", "status": "PASS", "detail": ""})

    # Extract passages
    passages = extract_passages(text)
    if not passages:
        # Try more lenient extraction
        p_sections = re.findall(r"### (.+?)\n(.*?)(?=###|\Z)", text, re.DOTALL)
        passages = [{"title": p[0], "content": p[1]} for p in p_sections if p[0] and "Questions" not in p[0] and "Answer" not in p[0] and "Reading Passage" not in p[0]]

    # Word counts per passage
    if passages:
        for i, p in enumerate(passages[:3]):
            wc = count_words(p["content"])
            if i == 0:
                spec_range = "700-800"
                passed = 700 <= wc <= 800
            elif i == 1:
                spec_range = "800-850"
                passed = 800 <= wc <= 850
            else:
                spec_range = "900+"
                passed = wc >= 900
            checks.append({
                "check": f"Passage {i+1} word count ({spec_range})",
                "status": "PASS" if passed else "FAIL",
                "detail": f"{wc} words"
            })

    # Count total questions - find ALL question numbers across formats
    numbered = extract_questions(text)
    gaps = count_gap_questions(text)
    # Also find questions in answer key tables
    table_qs = set()
    for t in find_answer_tables(text):
        for r in t:
            try:
                table_qs.add(int(r["q"]))
            except ValueError:
                pass
    all_qs = sorted(set(numbered + gaps + list(table_qs)))
    total_questions = len([q for q in all_qs if 1 <= q <= 40])
    checks.append({
        "check": "Total questions (40)",
        "status": "PASS" if total_questions == 40 else "FAIL",
        "detail": f"{total_questions} found (from {len(numbered)} numbered + {len(gaps)} gaps + {len(table_qs)} in answer keys)"
    })

    # Check question type variety per passage
    q_sections = re.findall(r"### Questions (\d+)[–-](\d+)(.*?)(?=###|\Z)", text, re.DOTALL)
    for start, end, content in q_sections:
        start, end = int(start), int(end)
        if start <= 13:
            passage = 1
        elif start <= 27:
            passage = 2
        else:
            passage = 3
        # Check for T/F/NG in P3 or Y/N/NG in P1
        content_lower = content.lower()
        if passage == 1 and "yes / no / not given" in content_lower:
            checks.append({"check": "Y/N/NG not in Passage 1", "status": "FAIL", "detail": f"Found in Q{start}-{end}"})
        elif passage == 1 and "yes/no/not given" in content_lower:
            checks.append({"check": "Y/N/NG not in Passage 1", "status": "FAIL", "detail": f"Found in Q{start}-{end}"})
        if passage == 3 and ("true / false / not given" in content_lower or "true/false/not given" in content_lower):
            checks.append({"check": "T/F/NG not in Passage 3", "status": "FAIL", "detail": f"Found in Q{start}-{end}"})

    # Check answer key format
    tables = find_answer_tables(text)
    total_answers = sum(len(t) for t in tables)
    checks.append({
        "check": "Answer keys present with Needle column",
        "status": "PASS" if tables else "FAIL",
        "detail": f"{len(tables)} answer key tables found ({total_answers} total answers)"
    })

    if tables:
        # Check every answer has a needle
        no_needle = [r for t in tables for r in t if not r["needle"].strip()]
        checks.append({
            "check": "All answers have Needle entries",
            "status": "PASS" if not no_needle else "FAIL",
            "detail": f"{len(no_needle)} answers missing needle"
        })

    # Matching Features word list check
    options = find_matching_word_list(text)
    if options:
        checks.append({
            "check": "Matching options found",
            "status": "INFO",
            "detail": f"{len(options)} options: {', '.join(options[:8])}"
        })

    return checks


def validate_listening(text, filepath):
    checks = []

    # Structural format checks
    format_issues = check_listening_format(text)
    for issue in format_issues:
        checks.append({"check": "Format: " + issue, "status": "FAIL", "detail": ""})
    if not format_issues:
        checks.append({"check": "Format: heading structure", "status": "PASS", "detail": ""})

    # Extract scripts
    scripts = extract_scripts(text)
    scripts_found = {s["part"]: s["content"] for s in scripts}

    # Word counts per part
    spec_ranges = {"Part 1": (250, 300), "Part 2": (350, 400), "Part 3": (400, 450), "Part 4": (800, 900)}
    for part, (lo, hi) in spec_ranges.items():
        if part in scripts_found:
            wc = count_words(scripts_found[part])
            passed = lo <= wc <= hi
            checks.append({
                "check": f"{part} script length ({lo}-{hi} words)",
                "status": "PASS" if passed else "FAIL",
                "detail": f"{wc} words"
            })
        else:
            checks.append({
                "check": f"{part} script found",
                "status": "FAIL",
                "detail": "Not found in file"
            })

    # Check Part 1 mandatory features
    if "Part 1" in scripts_found:
        p1 = scripts_found["Part 1"]
        has_spelling = check_spelling_trap(p1)
        has_correction = check_self_correction(p1)
        has_distractor = check_distractor(p1)
        checks.append({
            "check": "Part 1: Spelling trap (e.g., M-U-R-R-A-Y)",
            "status": "PASS" if has_spelling else "FAIL",
            "detail": "Found" if has_spelling else "Not found"
        })
        checks.append({
            "check": "Part 1: Self-correction (e.g., '14th... no wait')",
            "status": "PASS" if has_correction else "FAIL",
            "detail": "Found" if has_correction else "Not found"
        })
        checks.append({
            "check": "Part 1: Distractor (alternative rejected)",
            "status": "PASS" if has_distractor else "FAIL",
            "detail": "Found" if has_distractor else "Not found"
        })

    # Check Part 3 features
    if "Part 3" in scripts_found:
        p3 = scripts_found["Part 3"]
        has_opinion_change = check_opinion_change(p3)
        has_hedged = check_hedged_language(p3)
        checks.append({
            "check": "Part 3: Opinion change",
            "status": "PASS" if has_opinion_change else "FAIL",
            "detail": "Found" if has_opinion_change else "Not found"
        })
        checks.append({
            "check": "Part 3: Hedged language",
            "status": "PASS" if has_hedged else "FAIL",
            "detail": "Found" if has_hedged else "Not found"
        })

    # Check Part 4 features
    if "Part 4" in scripts_found:
        p4 = scripts_found["Part 4"]
        researchers = count_researcher_names(p4)
        has_signpost = check_signpost_language(p4)
        checks.append({
            "check": "Part 4: Named researchers (≥3)",
            "status": "PASS" if researchers >= 3 else "FAIL",
            "detail": f"{researchers} found"
        })
        checks.append({
            "check": "Part 4: Signpost language",
            "status": "PASS" if has_signpost else "FAIL",
            "detail": "Found" if has_signpost else "Not found"
        })

    # Count questions - find ALL question numbers
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
        "detail": f"{total} found (from {len(numbered)} numbered + {len(gaps)} gaps + {len(table_qs)} in answer keys)"
    })

    # Answer key format
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

    return checks


def run_validation(filepath):
    text = read_file(filepath)
    name = Path(filepath).name
    print(f"\n{'='*60}")
    print(f" VALIDATING: {name}")
    print(f"{'='*60}")

    # Determine if reading or listening
    is_reading = "READING PASSAGE" in text or "Reading Passage" in text
    is_listening = "LISTENING PART" in text or "Listening Part" in text

    if is_reading:
        checks = validate_reading(text, filepath)
    elif is_listening:
        checks = validate_listening(text, filepath)
    else:
        print("ERROR: Could not determine test type (Reading or Listening)")
        return

    # Print results
    passed = 0
    failed = 0
    for c in checks:
        status = c["status"]
        if status == "PASS":
            passed += 1
            icon = "✓"
        elif status == "FAIL":
            failed += 1
            icon = "✗"
        else:
            icon = "~"
        print(f"  {icon} {c['check']:45s} {status:5s}  {c['detail']}")

    print(f"\n{'─'*60}")
    print(f"  RESULTS:  {passed} passed  |  {failed} failed  |  {len(checks) - passed - failed} info")
    print(f"{'─'*60}\n")
    return failed == 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/validate.py <file1.md> [file2.md ...]")
        sys.exit(1)

    all_pass = True
    for arg in sys.argv[1:]:
        path = Path(arg)
        if path.exists():
            if not run_validation(path):
                all_pass = False
        else:
            print(f"File not found: {arg}")
            all_pass = False

    sys.exit(0 if all_pass else 1)
