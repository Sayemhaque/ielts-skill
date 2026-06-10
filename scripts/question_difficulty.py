#!/usr/bin/env python3
"""
Question Difficulty Scoring for IELTS test validation.

Heuristically estimates question difficulty to validate that
difficulty progression (easy → hard) holds across passages/parts.

Uses observable text features — no LLM calls, no external dependencies.
"""

import re
import math
from typing import Any

# ---------------------------------------------------------------------------
# Answer type → base difficulty (1-10 scale)
# ---------------------------------------------------------------------------

ANSWER_TYPE_DIFFICULTY = {
    # Completion types — lowest cognitive load (verbatim recall)
    "note_completion": 2,
    "table_completion": 2,
    "sentence_completion": 3,
    # Summary completion requires understanding whole paragraph
    "summary_completion": 4,
    "summary_completion_from_list": 4,
    "summary_completion_from_text": 4,
    # Matching types — requires identifying relationships
    "matching_features": 5,
    "matching_general": 5,
    "matching_headings": 6,
    "matching_sentence_endings": 6,
    # Multiple choice — requires discrimination among options
    "mcq_single": 7,
    "mcq_multiple": 8,
    # True/False/Not Given — requires careful scanning + judgment
    "tfng": 8,
    "ynng": 8,
}

# Type aliases from validate.py keyword detection
TYPE_ALIASES = {
    "completion": "note_completion",
    "tfng": "tfng",
    "ynng": "ynng",
    "headings": "matching_headings",
    "features": "matching_features",
    "mcq": "mcq_single",
    "matching": "matching_general",
}


def answer_type_difficulty(answer_type: str) -> float:
    """Map answer type keyword to base difficulty (1-10)."""
    resolved = TYPE_ALIASES.get(answer_type, answer_type)
    return ANSWER_TYPE_DIFFICULTY.get(resolved, 5.0)


# ---------------------------------------------------------------------------
# Common English words (head of ~200 academic/function words)
# Used by vocabulary_rarity() — words NOT in this list are "rare"
# ---------------------------------------------------------------------------

_COMMON = {
    "the", "be", "to", "of", "and", "a", "in", "that", "have", "i",
    "it", "for", "not", "on", "with", "he", "as", "you", "do", "at",
    "this", "but", "his", "by", "from", "they", "we", "say", "her", "she",
    "or", "an", "will", "my", "one", "all", "would", "there", "their", "what",
    "so", "up", "out", "if", "about", "who", "get", "which", "go", "me",
    "when", "make", "can", "like", "time", "no", "just", "him", "know", "take",
    "people", "into", "year", "your", "good", "some", "could", "them", "see", "other",
    "than", "then", "now", "look", "only", "come", "its", "over", "think", "also",
    "back", "after", "use", "two", "how", "our", "work", "first", "well", "way",
    "even", "new", "want", "because", "any", "these", "give", "day", "most", "us",
    "find", "here", "thing", "many", "being", "long", "down", "ask", "own", "much",
    "great", "old", "still", "mean", "such", "each", "right", "through", "too", "should",
    "need", "last", "place", "small", "under", "very", "why", "while", "may", "between",
    "high", "large", "often", "ever", "another", "must", "same", "big", "where", "call",
    "before", "different", "show", "around", "put", "off", "every", "still", "state",
    "world", "hand", "part", "place", "case", "week", "company", "system", "group",
    "number", "fact", "study", "research", "result", "example", "reason", "area",
    "process", "development", "effect", "change", "problem", "information", "question",
    "answer", "passage", "section", "following", "above", "below", "according",
    "complete", "choose", "write", "select", "match", "list", "statement",
}


def vocabulary_rarity(question_text: str) -> float:
    """
    Fraction of content words in the question that are uncommon (>8 letters
    or not in the built-in common-word list). Returns 0.0–1.0.
    """
    words = re.findall(r"[a-zA-Z]{3,}", question_text.lower())
    if not words:
        return 0.0
    rare = [w for w in words if w not in _COMMON and len(w) > 4]
    return len(rare) / len(words)


# ---------------------------------------------------------------------------
# Inference depth heuristic
# ---------------------------------------------------------------------------

def inference_depth(question_text: str, needle_sentence: str) -> int:
    """
    Estimate how many inference steps are needed to answer the question.

    1 = Direct match (keyword overlap > 80%)
    2 = Synonym substitution (some overlap but no verbatim quotes)
    3 = Multi-sentence synthesis (question mentions concepts spread apart)
    4 = Global / abstract (writer's purpose, main idea, evaluation)
    """
    q_words = set(re.findall(r"[a-zA-Z]{4,}", question_text.lower()))
    n_words = set(re.findall(r"[a-zA-Z]{4,}", needle_sentence.lower()))

    # Remove question-type boilerplate
    boilerplate = {
        "choose", "correct", "letter", "complete", "summary", "sentence",
        "write", "more", "than", "words", "answer", "select", "match",
        "according", "passage", "from", "list", "below",
    }
    q_words -= boilerplate

    if not q_words or not n_words:
        return 2  # default

    overlap = len(q_words & n_words)
    union = len(q_words | n_words)
    jaccard = overlap / max(union, 1)

    # Check for inference-triggering patterns
    has_opinion = any(p in question_text.lower() for p in [
        "writer", "author", "purpose", "belief", "attitude", "view",
        "imply", "suggest", "conclude", "infer", "likely",
    ])
    has_synthesis = any(p in question_text.lower() for p in [
        "both", "together", "compar", "contrast", "difference",
        "similar", "relationship", "between",
    ])

    if has_opinion:
        return 4
    if has_synthesis:
        return 3
    if jaccard > 0.5:
        return 1
    if jaccard > 0.2:
        return 2
    return 3


# ---------------------------------------------------------------------------
# Question stem length (proxy for syntactic complexity)
# ---------------------------------------------------------------------------

def stem_length_score(question_text: str) -> float:
    """
    Score based on question length. Longer stems tend to be harder.
    Normalised to ~1-10 range.
    """
    wc = len(question_text.split())
    # Most IELTS question stems are 5-30 words
    return min(10, max(1, wc / 3))


# ---------------------------------------------------------------------------
# Combined QDS
# ---------------------------------------------------------------------------

def compute_qds(
    question_text: str,
    answer_type: str,
    needle_sentence: str = "",
) -> float:
    """
    Question Difficulty Score (QDS) — weighted combination of factors.

    Returns a score on ~1-10 scale.
    """
    base = answer_type_difficulty(answer_type)
    depth = inference_depth(question_text, needle_sentence)
    rare = vocabulary_rarity(question_text)
    length = stem_length_score(question_text)

    # Weights: type knowledge + inference depth dominate
    qds = (
        0.30 * base
        + 0.30 * min(10, depth * 2.5)    # inference depth 1-4 → 2.5-10
        + 0.20 * min(10, rare * 15)      # rare fraction 0-1 → 0-10 (cap at full rare)
        + 0.20 * length
    )
    return round(qds, 1)


# ---------------------------------------------------------------------------
# Progressive difficulty validation
# ---------------------------------------------------------------------------

def validate_progressive_difficulty(
    questions_by_passage: dict[int, list[dict]],
    module_name: str = "Reading",
) -> dict:
    """
    Validate that mean QDS increases across passages/parts.

    Args:
        questions_by_passage: dict mapping passage index (1,2,3 or 1,2,3,4)
            to list of question dicts with keys:
                - 'text': question stem text
                - 'type': answer type keyword (e.g. "tfng", "ynng", "mcq", ...)
                - 'needle': (optional) answer needle / source sentence
        module_name: "Reading" or "Listening" (for reporting)

    Returns:
        dict with keys:
            - 'passed': bool
            - 'passage_scores': list of (passage_index, mean_qds) tuples
            - 'detail': human-readable detail string
            - 'errors': list of issues found
    """
    scores = {}
    details = {}

    for p_idx in sorted(questions_by_passage.keys()):
        questions = questions_by_passage[p_idx]
        if not questions:
            scores[p_idx] = 0.0
            details[p_idx] = "no questions"
            continue

        qds_values = []
        for q in questions:
            text = q.get("text", "")
            q_type = q.get("type", "completion")
            needle = q.get("needle", "")
            if text.strip():
                qds_values.append(compute_qds(text, q_type, needle))

        if qds_values:
            scores[p_idx] = round(sum(qds_values) / len(qds_values), 1)
        else:
            scores[p_idx] = 0.0
        details[p_idx] = f"n={len(qds_values)}, mean={scores[p_idx]}"

    # Check progression
    sorted_idxs = sorted(scores.keys())
    errors = []
    for i in range(len(sorted_idxs) - 1):
        curr = sorted_idxs[i]
        nxt = sorted_idxs[i + 1]
        if scores[curr] >= scores[nxt]:
            errors.append(
                f"{module_name} {curr} ({scores[curr]}) >= "
                f"{module_name} {nxt} ({scores[nxt]})"
            )

    # Tolerate small violations within 1.0 QDS (warning territory)
    hard_errors = []
    if errors:
        for err in errors:
            # Extract scores from error string
            score_match = re.findall(r"\(([\d.]+)\)", err)
            if len(score_match) >= 2:
                a, b = float(score_match[0]), float(score_match[1])
                if b - a > 1.0:  # next is more than 1.0 harder than previous — should still work
                    pass
                if a - b > 1.0:  # previous more than 1.0 harder than next — FAIL
                    hard_errors.append(err)
    # Actually let me simplify: if the mean of a later passage is LOWER than an earlier one, that's a failure
    # because it means the later passage is easier. The 1.0 tolerance is for small noise.
    hard_errors = errors  # all failures for now

    passed = len(hard_errors) == 0

    score_str = ", ".join(
        f"{module_name[:3]} {idx}={scores[idx]}" for idx in sorted_idxs
    )

    return {
        "passed": passed,
        "passage_scores": [(idx, scores[idx]) for idx in sorted_idxs],
        "detail": score_str + ("; errors: " + "; ".join(hard_errors) if hard_errors else ""),
        "errors": hard_errors,
    }


# ---------------------------------------------------------------------------
# CLI convenience
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] in ("--help", "-h"):
        print("Usage: python3 scripts/question_difficulty.py")
        print("  Runs a self-test with sample questions.")
        sys.exit(0)

    # ---- Self-test ----
    print("Question Difficulty Module — Self-Test")
    print("=" * 55)

    # Sample Passage 1 questions (completions, direct recall)
    p1_qs = [
        {"text": "The Silk Road was a network of trade routes.", "type": "tfng", "needle": "The Silk Road was not a single road but a network of trade routes"},
        {"text": "The Roman government encouraged silk imports.", "type": "tfng", "needle": "Roman writers complained that silk was draining the empire's gold reserves"},
        {"text": "Write NO MORE THAN TWO WORDS for each answer.", "type": "note_completion", "needle": "the Han court opened formal trade routes"},
    ]

    # Sample Passage 3 questions (YNNG, inference, global understanding)
    p3_qs = [
        {"text": "The writer believes that forgetting is primarily a failure of memory storage.", "type": "ynng", "needle": "forgetting serves an adaptive function rather than representing a failure of the memory system"},
        {"text": "According to the passage, what is the main purpose of adaptive forgetting?", "type": "mcq_single", "needle": "forgetting irrelevant information enhances the brain's ability to retain important memories"},
        {"text": "Complete the summary using the list of words below.", "type": "summary_completion_from_list", "needle": "the spindle mechanism actively weakens certain neural connections during sleep"},
    ]

    result = validate_progressive_difficulty({1: p1_qs, 2: p1_qs, 3: p3_qs})
    print(f"\nProgressive difficulty: {'✓ PASS' if result['passed'] else '✗ FAIL'}")
    print(f"  Scores: {result['detail']}")

    for q in p1_qs:
        qds = compute_qds(q["text"], q["type"], q.get("needle", ""))
        depth = inference_depth(q["text"], q.get("needle", ""))
        rare = vocabulary_rarity(q["text"])
        print(f"\n  QDS={qds:.1f} (depth={depth}, rare={rare:.2f}) | {q['type']:<15s} | {q['text'][:50]}")

    for q in p3_qs:
        qds = compute_qds(q["text"], q["type"], q.get("needle", ""))
        depth = inference_depth(q["text"], q.get("needle", ""))
        rare = vocabulary_rarity(q["text"])
        print(f"\n  QDS={qds:.1f} (depth={depth}, rare={rare:.2f}) | {q['type']:<15s} | {q['text'][:50]}")

    print(f"\n{'='*55}")
    print("Self-test complete.")
