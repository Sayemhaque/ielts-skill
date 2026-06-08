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


def extract_question_sections(text):
    """Return question sections with ranges, body text, and position."""
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
    """Return answer key sections with ranges, body text, and position."""
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
    """Find question numbers stated as numbered items or table gaps inside one section."""
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
    title_pattern = r"\b(?:Dr|Professor|Sir)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?"
    names = set(re.findall(title_pattern, text))
    role_pattern = r"\b[A-Z][a-z]+\s+[A-Z][a-z]+,\s+(?:a|an)\s+[a-z]+(?:\s+[a-z]+){0,3}"
    for match in re.findall(role_pattern, text):
        names.add(match.split(",")[0])
    return len(names)


def check_synonym_rule(source_text, questions_text):
    """Find exact 3+ word phrase overlaps between source and questions."""
    import string
    def get_clean_words(text):
        text = text.translate(str.maketrans('', '', string.punctuation))
        return [w.lower() for w in text.split() if w.strip()]
    
    source_words = get_clean_words(source_text)
    question_words = get_clean_words(questions_text)
    
    source_4grams = set(" ".join(source_words[i:i+4]) for i in range(len(source_words)-3))
    question_4grams = set(" ".join(question_words[i:i+4]) for i in range(len(question_words)-3))
    
    common_phrases = {"complete the summary below", "choose the correct letter", "write no more than", "choose no more than", "more than two words", "do the following statements", "agree with the information", "choose the correct heading", "read passage 1", "reading passage 2", "reading passage 3", "in boxes on your", "boxes on your answer", "on your answer sheet", "write the correct letter", "write the correct number"}
    
    overlap = {g for g in (source_4grams & question_4grams) if not any(c in g for c in common_phrases)}
    
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

    q_sections = extract_question_sections(text)
    key_sections = extract_answer_key_sections(text)

    # Count total questions from declared ranges, question bodies, and answer keys.
    body_qs = []
    declared_qs = []
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
    add_check(
        checks,
        "Total questions (40)",
        total_questions == 40,
        f"{total_questions} unique questions found; {len(table_qs)} answer-key rows",
    )
    add_check(
        checks,
        "Exact question coverage (1-40)",
        all_qs == list(range(1, 41)),
        f"found {all_qs[:5]}...{all_qs[-5:] if all_qs else []}",
    )
    add_check(
        checks,
        "Answer key rows (40)",
        sorted(table_qs) == list(range(1, 41)),
        f"{len(table_qs)} keyed answers",
    )

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
    add_check(
        checks,
        "Question ranges continuous",
        continuous,
        ", ".join(range_details) if range_details else "no question sections found",
    )

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
    add_check(
        checks,
        "Answer key immediately follows each set",
        immediate_keys and len(q_sections) == len(key_sections),
        "mismatched: " + ", ".join(immediate_details) if immediate_details else f"{len(key_sections)} keys",
    )
    # Check question type placement per passage and extract word limits.
    passage_types = {1: set(), 2: set(), 3: set()}
    word_limits = {}  # Map Q num to word limit
    
    for section in q_sections:
        start, end, content = section["start"], section["end"], section["content"]
        if start <= 13:
            passage = 1
        elif start <= 26:
            passage = 2
        else:
            passage = 3
        content_lower = content.lower()
        if "true" in content_lower and "false" in content_lower and "not given" in content_lower:
            passage_types[passage].add("tfng")
        if "yes" in content_lower and "no" in content_lower and "not given" in content_lower:
            passage_types[passage].add("ynng")
        if "choose the correct heading" in content_lower or "list of headings" in content_lower:
            passage_types[passage].add("headings")
        if "complete the" in content_lower or "write no more than" in content_lower:
            passage_types[passage].add("completion")
            # Extract word limit
            limit_match = re.search(r"no more than (one|two|three|four) word", content_lower)
            if limit_match:
                num_map = {"one": 1, "two": 2, "three": 3, "four": 4}
                limit = num_map[limit_match.group(1)]
                # "AND/OR A NUMBER" usually means they can add a number, so effectively limit + 1
                if "and/or a number" in content_lower or "or a number" in content_lower:
                    limit += 1
                for q in range(start, end + 1):
                    word_limits[q] = limit
        if "match each statement" in content_lower or "list of people" in content_lower or "list of experts" in content_lower:
            passage_types[passage].add("features")
        if "choose the correct letter" in content_lower:
            passage_types[passage].add("mcq")

        if passage == 1 and "yes" in content_lower and "no" in content_lower and "not given" in content_lower:
            checks.append({"check": "Y/N/NG not in Passage 1", "status": "FAIL", "detail": f"Found in Q{start}-{end}"})
        if passage == 3 and "true" in content_lower and "false" in content_lower and "not given" in content_lower:
            checks.append({"check": "T/F/NG not in Passage 3", "status": "FAIL", "detail": f"Found in Q{start}-{end}"})

        if passages and passage <= len(passages):
            p_content = passages[passage-1]["content"]
            overlap_count, overlap_words = check_synonym_rule(p_content, content)
            threshold = 2  # If they share more than 2 distinct 4-grams, flag it
            add_check(
                checks,
                f"Passage {passage} (Q{start}-{end}) synonym overlap",
                overlap_count <= threshold,
                f"{overlap_count} shared 4-grams: {', '.join(list(overlap_words)[:5])}" if overlap_count > 0 else "No 4-gram overlaps found",
            )

    add_check(
        checks,
        "Passage 1 required types",
        {"tfng", "completion"}.issubset(passage_types[1]),
        ", ".join(sorted(passage_types[1])),
    )
    add_check(
        checks,
        "Passage 2 required types",
        {"headings", "features", "completion"}.issubset(passage_types[2]),
        ", ".join(sorted(passage_types[2])),
    )
    add_check(
        checks,
        "Passage 3 required types",
        {"ynng", "mcq", "completion"}.issubset(passage_types[3]),
        ", ".join(sorted(passage_types[3])),
    )

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

        # Check needle in passage
        if passages:
            needles_missing_from_passage = []
            for t in tables:
                for r in t:
                    if r["needle"].strip():
                        # Figure out passage number roughly based on Q num
                        try:
                            q_num = int(r["q"])
                            # If there's a quoted string, extract it
                            match = re.search(r'"([^"]+)"', r["needle"])
                            if match:
                                clean_needle = match.group(1)
                            else:
                                clean_needle = re.sub(r'^Paragraph [A-Z]:\s*', '', r["needle"].strip())
                                clean_needle = clean_needle.strip('"\'')
                            
                            # Normalize whitespace across all passages to avoid question boundary issues
                            p_content = " ".join(" ".join(p["content"].split()) for p in passages).lower()
                            n_content = " ".join(clean_needle.split()).lower()
                            
                            # Handle ellipses
                            parts = [p.strip() for p in re.split(r'\.{2,}', n_content)]
                            missing = False
                            for part in parts:
                                if len(part) > 5 and part not in p_content:
                                    missing = True
                                    
                            if missing and len(n_content) > 10:
                                # Ignore NOT GIVEN where they might say "The passage discusses X but not Y"
                                if r["answer"].strip().upper() != "NOT GIVEN":
                                    needles_missing_from_passage.append(f"Q{q_num}")
                        except ValueError:
                            pass
            
            checks.append({
                "check": "Needles found in passage text",
                "status": "PASS" if not needles_missing_from_passage else "FAIL",
                "detail": f"{len(needles_missing_from_passage)} needles not in passage: {', '.join(needles_missing_from_passage[:5])}"
            })

        # Check completion word limits
        if word_limits:
            completion_limit_violations = []
            for t in tables:
                for r in t:
                    try:
                        q_num = int(r["q"])
                        if q_num in word_limits:
                            ans_words = len([w for w in r["answer"].split() if w.strip()])
                            if ans_words > word_limits[q_num]:
                                completion_limit_violations.append(f"Q{q_num} (limit {word_limits[q_num]}, got {ans_words})")
                    except ValueError:
                        pass
            
            checks.append({
                "check": "Completion word limits respected",
                "status": "PASS" if not completion_limit_violations else "FAIL",
                "detail": f"{len(completion_limit_violations)} violations: {', '.join(completion_limit_violations[:5])}" if completion_limit_violations else "All limits respected"
            })

        # Check T/F/NG distribution
        tfng_counts = {1: {"T": 0, "F": 0, "NG": 0}, 2: {"T": 0, "F": 0, "NG": 0}, 3: {"T": 0, "F": 0, "NG": 0}}
        ynng_counts = {1: {"Y": 0, "N": 0, "NG": 0}, 2: {"Y": 0, "N": 0, "NG": 0}, 3: {"Y": 0, "N": 0, "NG": 0}}
        for t in tables:
            for r in t:
                try:
                    q_num = int(r["q"])
                    p_idx = 0 if q_num <= 13 else (1 if q_num <= 26 else 2)
                    ans = r["answer"].strip().upper()
                    if ans == "TRUE": tfng_counts[p_idx+1]["T"] += 1
                    if ans == "FALSE": tfng_counts[p_idx+1]["F"] += 1
                    if ans == "NOT GIVEN": 
                        tfng_counts[p_idx+1]["NG"] += 1
                        ynng_counts[p_idx+1]["NG"] += 1
                    if ans == "YES": ynng_counts[p_idx+1]["Y"] += 1
                    if ans == "NO": ynng_counts[p_idx+1]["N"] += 1
                except ValueError:
                    pass
        
        tfng_violations = []
        for p in [1, 2, 3]:
            if "tfng" in passage_types[p]:
                counts = tfng_counts[p]
                if counts["T"] < 1 or counts["F"] < 1 or counts["NG"] < 1:
                    tfng_violations.append(f"P{p} T/F/NG: {counts}")
            if "ynng" in passage_types[p]:
                counts = ynng_counts[p]
                if counts["Y"] < 1 or counts["N"] < 1 or counts["NG"] < 1:
                    tfng_violations.append(f"P{p} Y/N/NG: {counts}")
                    
        checks.append({
            "check": "Boolean questions have all 3 types",
            "status": "PASS" if not tfng_violations else "FAIL",
            "detail": ", ".join(tfng_violations) if tfng_violations else "All required boolean types have at least 1 of each answer"
        })

        ng_without_absence_note = [
            r for t in tables for r in t
            if r["answer"].strip().upper() == "NOT GIVEN"
            and not re.search(
                r"\b(does not|not mention|not mentioned|not stated|not described|no information|no statement|impossible to say)\b",
                r["needle"],
                re.IGNORECASE,
            )
        ]
        checks.append({
            "check": "NOT GIVEN uses absence note",
            "status": "PASS" if not ng_without_absence_note else "FAIL",
            "detail": f"{len(ng_without_absence_note)} weak NOT GIVEN needles"
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
