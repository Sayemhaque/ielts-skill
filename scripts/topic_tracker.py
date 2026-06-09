#!/usr/bin/env python3
"""
IELTS Topic Tracker
Logs used topics from generated tests so Claude never repeats them across sessions.

Usage:
  python3 scripts/topic_tracker.py log   <file.md>        # log topics from a new test
  python3 scripts/topic_tracker.py check <topic_phrase>   # check if a topic is too similar to used ones
  python3 scripts/topic_tracker.py list                   # list all used topics
  python3 scripts/topic_tracker.py reset                  # clear all history (use carefully)

Topic log is stored in: references/used-topics.json
"""

import json
import re
import sys
from pathlib import Path
from difflib import SequenceMatcher

TOPIC_LOG = Path(__file__).parent.parent / "references" / "used-topics.json"

# ---------------------------------------------------------------------------
# Similarity threshold — topics scoring above this are considered "too close"
# 0.65 catches paraphrases ("monarch butterfly migration" vs "butterfly migration patterns")
# while allowing genuinely different topics on the same broad theme.
# ---------------------------------------------------------------------------
SIMILARITY_THRESHOLD = 0.65


def load_log():
    if TOPIC_LOG.exists():
        with open(TOPIC_LOG) as f:
            return json.load(f)
    return {"reading": [], "listening": [], "all": []}


def save_log(data):
    TOPIC_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(TOPIC_LOG, "w") as f:
        json.dump(data, f, indent=2)


def similarity(a, b):
    """Normalised string similarity (0–1). Uses SequenceMatcher."""
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def is_too_similar(new_topic, existing_topics):
    """
    Returns (True, matched_topic) if new_topic is too similar to any existing topic.
    """
    for t in existing_topics:
        score = similarity(new_topic, t)
        if score >= SIMILARITY_THRESHOLD:
            return True, t
    return False, None


def extract_topics_from_file(text):
    """
    Extract passage/part titles from a generated test file.
    Reading: looks for '### The ...' passage titles.
    Listening: looks for context descriptions in Part headers.
    """
    topics = {"reading": [], "listening": []}

    # Reading passage titles (### Title Here — under ## READING PASSAGE N)
    reading_titles = re.findall(
        r"## READING PASSAGE \d.*?### ([^\n#]+)", text, re.DOTALL
    )
    for t in reading_titles:
        clean = t.strip()
        if clean and len(clean) > 5 and "Questions" not in clean and "Answer" not in clean:
            topics["reading"].append(clean)

    # Listening — extract context from "You will hear a ..." lines
    listening_contexts = re.findall(
        r"\*You will hear[^\*\n]+\*", text
    )
    for ctx in listening_contexts:
        # Strip markdown italics and "You will hear"
        clean = re.sub(r"[\*_]", "", ctx).strip()
        clean = re.sub(r"^You will hear\s+(a|an|two|three)?\s*", "", clean, flags=re.IGNORECASE).strip()
        if clean and len(clean) > 5:
            topics["listening"].append(clean)

    return topics


def cmd_log(filepath):
    text = Path(filepath).read_text()
    extracted = extract_topics_from_file(text)
    log = load_log()

    added = []
    warnings = []

    for module in ["reading", "listening"]:
        for topic in extracted[module]:
            # Check similarity against ALL logged topics (cross-module)
            too_close, matched = is_too_similar(topic, log["all"])
            if too_close:
                warnings.append(f"  ⚠  '{topic}' is too similar to already-used topic: '{matched}'")
            else:
                log[module].append(topic)
                log["all"].append(topic)
                added.append(f"  +  [{module}] {topic}")

    save_log(log)

    print(f"\nTopic Tracker — logging: {Path(filepath).name}")
    if added:
        print("Added:")
        for a in added:
            print(a)
    if warnings:
        print("Warnings (not logged — too similar to existing topic):")
        for w in warnings:
            print(w)
    if not added and not warnings:
        print("  No extractable topics found.")
    print()


def cmd_check(topic_phrase):
    log = load_log()
    too_close, matched = is_too_similar(topic_phrase, log["all"])
    if too_close:
        print(f"\n  ✗  BLOCKED — '{topic_phrase}' is too similar to: '{matched}'")
        print("     Choose a different topic.\n")
        sys.exit(1)
    else:
        print(f"\n  ✓  OK — '{topic_phrase}' has not been used before.\n")
        sys.exit(0)


def cmd_list():
    log = load_log()
    print("\nUsed Topics")
    print("=" * 50)
    for module in ["reading", "listening"]:
        items = log.get(module, [])
        print(f"\n  {module.capitalize()} ({len(items)}):")
        if items:
            for t in items:
                print(f"    - {t}")
        else:
            print("    (none yet)")
    print()


def cmd_reset():
    confirm = input("Reset all topic history? Type YES to confirm: ").strip()
    if confirm == "YES":
        save_log({"reading": [], "listening": [], "all": []})
        print("Topic log cleared.")
    else:
        print("Cancelled.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1].lower()

    if cmd == "log" and len(sys.argv) >= 3:
        cmd_log(sys.argv[2])
    elif cmd == "check" and len(sys.argv) >= 3:
        cmd_check(" ".join(sys.argv[2:]))
    elif cmd == "list":
        cmd_list()
    elif cmd == "reset":
        cmd_reset()
    else:
        print(__doc__)
        sys.exit(1)
