#!/usr/bin/env python3
"""
Readability metrics for IELTS test generation.

Pure Python — no external dependencies. Provides:
  - Flesch Reading Ease (FRE)
  - Coleman-Liau Index (CLI)
  - IELTS band estimation from FRE
  - Per-passage readability validation

Usage:
  from readability import flesch_reading_ease, validate_readability

  score = flesch_reading_ease(passage_text)
  results = validate_readability([passage_1, passage_2, passage_3])
"""

import re
import math

# ---------------------------------------------------------------------------
# Syllable counting — rule-based for English
# ---------------------------------------------------------------------------

# Common word → syllable overrides (words the rule-based counter gets wrong)
EXCEPTIONS = {
    "area": 3, "every": 3, "evening": 3, "general": 3, "minutes": 2,
    "natural": 3, "average": 3, "language": 2, "interesting": 4,
    "temperature": 4, "different": 3, "business": 2, "beautiful": 3,
    "probably": 3, "education": 4, "environment": 4, "technology": 4,
    "literature": 4, "science": 2, "society": 3, "history": 3,
    "several": 3, "influence": 3, "significant": 4, "experience": 4,
    "especially": 4, "actually": 4, "university": 5, "community": 4,
    "opportunity": 5, "traditional": 4, "development": 4,
}

# Suffix patterns that add a syllable
_SUFFIX_SYLLABIC = re.compile(
    r"(cial|tial|cion|sion|tion|uou|gion|gious|geous|"
    r"cious|cean|tian|rian|cian|sius|tius|guous|chian)$",
    re.IGNORECASE,
)


def count_syllables(word: str) -> int:
    """Estimate syllable count for an English word."""
    word = word.strip().lower()
    if not word or not word.isalpha():
        return 1

    if word in EXCEPTIONS:
        return EXCEPTIONS[word]

    # Remove punctuation, apostrophes
    word = word.strip(".,!?:;\"'()[]-")

    # Special: -le ending (e.g., "table", "people") — adds a syllable
    # unless preceded by a vowel (e.g., "bottle", "cattle" — still adds one)
    le_bonus = 0
    if len(word) > 2 and word[-2:] == "le" and word[-3] not in "aeiou":
        le_bonus = 1

    # Remove final silent e (but not -le words)
    if len(word) > 2 and word[-1] == "e" and not (
        len(word) > 2 and word[-2:] == "le" and word[-3] not in "aeiou"
    ):
        word = word[:-1]

    # Remove final es (silent)
    if len(word) > 2 and word[-2:] == "es":
        word = word[:-2]

    # Remove final ed (often silent) — but not if it ends in -ted or -ded
    if len(word) > 3 and word[-2:] == "ed" and word[-3] not in "td":
        word = word[:-2]

    # Count vowel groups
    vowel_group_count = 0
    prev_is_vowel = False
    for ch in word:
        is_vowel = ch in "aeiouy"
        if is_vowel and not prev_is_vowel:
            vowel_group_count += 1
        prev_is_vowel = is_vowel

    # Apply suffix bonus
    suffix_bonus = 1 if _SUFFIX_SYLLABIC.search(word) else 0

    total = vowel_group_count + le_bonus + suffix_bonus
    return max(1, total)


# ---------------------------------------------------------------------------
# Sentence splitting
# ---------------------------------------------------------------------------

_SENTENCE_SPLIT = re.compile(r"[.!?]+(?:\s|$)")


def _count_sentences(text: str) -> int:
    """Count sentences in text by splitting on sentence-ending punctuation."""
    text = text.strip()
    if not text:
        return 0
    sentences = _SENTENCE_SPLIT.split(text)
    return len([s for s in sentences if s.strip()])


# ---------------------------------------------------------------------------
# Flesch Reading Ease
# ---------------------------------------------------------------------------

def flesch_reading_ease(text: str) -> float:
    """
    Flesch Reading Ease score (0–100).

    Higher scores = easier to read.
      > 90  — Very easy (Band 4.0–5.0)
      60–90 — Easy / Plain English (Band 5.5–6.5)
      40–60 — Fairly difficult (Band 6.5–7.5)
      < 40  — Difficult / Academic (Band 7.5–8.5+)

    Formula:
      FRE = 206.835 - 1.015 × (words / sentences) - 84.6 × (syllables / words)
    """
    total_words = max(1, len(text.split()))
    total_sentences = max(1, _count_sentences(text))
    total_syllables = sum(count_syllables(w) for w in text.split() if w.strip())

    score = (
        206.835
        - 1.015 * (total_words / total_sentences)
        - 84.6 * (total_syllables / total_words)
    )
    return round(score, 1)


# ---------------------------------------------------------------------------
# Coleman-Liau Index
# ---------------------------------------------------------------------------

def coleman_liau_index(text: str) -> float:
    """
    Coleman-Liau Index (US grade level).

    Uses characters, not syllables — good cross-check against FRE.
    Formula:
      CLI = 0.0588 × L - 0.296 × S - 15.8
    where L = average letters per 100 words, S = average sentences per 100 words.
    """
    words = text.split()
    total_words = max(1, len(words))
    total_sentences = max(1, _count_sentences(text))
    total_letters = sum(len(w) for w in words if w.strip())

    l_per_100 = (total_letters / total_words) * 100
    s_per_100 = (total_sentences / total_words) * 100

    cli = 0.0588 * l_per_100 - 0.296 * s_per_100 - 15.8
    return round(cli, 1)


# ---------------------------------------------------------------------------
# IELTS band estimation
# ---------------------------------------------------------------------------

BAND_THRESHOLDS = [
    (90, "4.0–5.0", "Very accessible"),
    (75, "5.0–5.5", "Plain English"),
    (60, "5.5–6.5", "Moderate"),
    (45, "6.5–7.0", "Moderate–Academic"),
    (30, "7.0–7.5", "Academic"),
    (0,  "7.5–8.5+", "Advanced Academic"),
]


def estimate_ielts_band(fre_score: float) -> dict:
    """
    Estimate IELTS band range from Flesch Reading Ease score.

    Returns dict with 'band' (string range) and 'label' (description).
    """
    for threshold, band, label in BAND_THRESHOLDS:
        if fre_score >= threshold:
            return {"band": band, "label": label}
    return {"band": "8.0+", "label": "Very Advanced Academic"}


# ---------------------------------------------------------------------------
# Validation against spec thresholds
# ---------------------------------------------------------------------------

def validate_readability(
    passages: list[str],
    thresholds: list[dict],
) -> list[dict]:
    """
    Validate readability of each passage against expected thresholds.

    Args:
        passages: List of passage/part texts (in order, e.g. [P1, P2, P3]).
        thresholds: List of dicts with:
            - 'min_fre' (float, optional): minimum FRE score
            - 'max_fre' (float, optional): maximum FRE score
            - 'label' (str): description for the check name

    Returns:
        List of result dicts:
            {'index', 'label', 'fre', 'cli', 'estimated_band', 'passed', 'detail'}
    """
    results = []
    for i, (text, threshold) in enumerate(zip(passages, thresholds)):
        fre = flesch_reading_ease(text)
        cli = coleman_liau_index(text)
        band = estimate_ielts_band(fre)

        min_fre = threshold.get("min_fre", 0)
        max_fre = threshold.get("max_fre", 100)

        in_range = min_fre <= fre <= max_fre
        passed = in_range

        detail_parts = [f"FRE={fre:.1f}, CLI={cli:.1f}, est_band={band['band']}"]
        if not passed:
            if fre < min_fre:
                detail_parts.append(f"below min ({min_fre})")
            if fre > max_fre:
                detail_parts.append(f"above max ({max_fre})")

        results.append({
            "index": i + 1,
            "label": threshold.get("label", f"Passage {i+1}"),
            "fre": fre,
            "cli": cli,
            "estimated_band": band["band"],
            "passed": passed,
            "detail": "; ".join(detail_parts),
        })

    return results


# ---------------------------------------------------------------------------
# CLI convenience
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] in ("--help", "-h"):
        print("Usage: python3 scripts/readability.py [<file.md>]")
        print("  Without arg: runs unit self-test")
        print("  With arg:    computes readability for each passage in the file")
        sys.exit(0)

    if len(sys.argv) > 1:
        # Validate passages in a markdown file
        text = open(sys.argv[1]).read()
        # Try to extract passages (same regex pattern as validate.py)
        passages = re.findall(
            r"## (?:READING PASSAGE|LISTENING PART) \d.*?^### (?:Questions|Script|Answer)",
            text,
            re.MULTILINE | re.DOTALL,
        )
        if not passages:
            # Fallback: just use the whole text
            passages = [text]

        for i, p in enumerate(passages):
            fre = flesch_reading_ease(p.split("###")[0])
            print(f"Section {i+1}: FRE={fre:.1f}")
        sys.exit(0)

    # ---- Self-test ----
    print("Readability Module — Self-Test")
    print("=" * 50)

    tests = [
        ("Simple sentence", "The cat sat on the mat.", 90, 100),
        ("Moderate text", "The study examined the effects of sleep deprivation on cognitive performance in adolescents.", 30, 60),
        ("Academic text", "The aforementioned paradigm shift necessitates a comprehensive re-evaluation of the epistemological foundations upon which contemporary research methodologies are predicated.", 0, 40),
    ]

    for label, sample, lo, hi in tests:
        fre = flesch_reading_ease(sample)
        cli = coleman_liau_index(sample)
        band = estimate_ielts_band(fre)
        status = "✓" if lo <= fre <= hi else "✗"
        print(f"\n{status} {label}: FRE={fre:.1f}, CLI={cli:.1f}, band={band['band']}")
        print(f"   Text: {sample[:70]}...")
        print(f"   Expected: {lo}–{hi}, Got: {fre:.1f}")

    print("\n" + "=" * 50)
    print("Done. Note: FRE is approximate; use Coleman-Liau as cross-check.")
