#!/usr/bin/env python3
"""
IELTS Topic Tracker
Logs used topics from generated tests so Claude never repeats them across sessions.

Also manages category rotation for Passage 3 (Reading) and Part 4 (Listening)
to ensure topic diversity at the hardest proficiency level.

Usage:
  python3 scripts/topic_tracker.py log   <file.md>        # log topics from a new test
  python3 scripts/topic_tracker.py check <topic_phrase>   # check if a topic is too similar to used ones
  python3 scripts/topic_tracker.py list                   # list all used topics
  python3 scripts/topic_tracker.py reset                  # clear all history (use carefully)

  # Category rotation (Passage 3 / Part 4 diversity):
  python3 scripts/topic_tracker.py get_reading_p3_category   # print the recommended Passage 3 category
  python3 scripts/topic_tracker.py log_reading_p3_category   # increment the Passage 3 cycle counter
  python3 scripts/topic_tracker.py get_listening_p4_category # print the recommended Listening Part 4 category
  python3 scripts/topic_tracker.py log_listening_p4_category # increment the Listening Part 4 cycle counter

Topic log is stored in: references/used-topics.json
Category rotation state: references/usage-state.json
"""

import json
import re
import sys
from pathlib import Path
from difflib import SequenceMatcher

TOPIC_LOG = Path(__file__).parent.parent / "references" / "used-topics.json"
USAGE_STATE = Path(__file__).parent.parent / "references" / "usage-state.json"

# Category rotation definitions — cycle through these to ensure topic diversity.
READING_P3_CATEGORIES = [
    "Psychology",
    "Cognitive Science",
    "Philosophy of Science",
    "Sociology",
]

LISTENING_P4_CATEGORIES = [
    "Science",
    "History",
    "Social Science",
    "Health",
]

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


def load_usage_state():
    """Load or create usage-state.json for category rotation tracking."""
    default = {"reading_p3_cycle": 0, "listening_p4_cycle": 0}
    if USAGE_STATE.exists():
        with open(USAGE_STATE) as f:
            return json.load(f)
    return default


def save_usage_state(state):
    USAGE_STATE.parent.mkdir(parents=True, exist_ok=True)
    with open(USAGE_STATE, "w") as f:
        json.dump(state, f, indent=2)


def get_next_category(categories, cycle_key, label):
    """
    Get the next category in the rotation cycle.
    Returns (category_name, cycle_counter_before).
    """
    state = load_usage_state()
    cycle = state.get(cycle_key, 0)
    cat = categories[cycle % len(categories)]
    return cat, cycle


def log_category(cycle_key):
    """Increment the cycle counter for a given key. Returns the new counter."""
    state = load_usage_state()
    state[cycle_key] = state.get(cycle_key, 0) + 1
    save_usage_state(state)
    return state[cycle_key]


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


# ---------------------------------------------------------------------------
# Category rotation commands
# ---------------------------------------------------------------------------


def cmd_get_reading_p3_category():
    cat, cycle = get_next_category(READING_P3_CATEGORIES, "reading_p3_cycle", "Reading P3")
    print(f"\n  → Recommended Passage 3 category: {cat} (cycle position {cycle % len(READING_P3_CATEGORIES)})\n")


def cmd_log_reading_p3_category():
    state = load_usage_state()
    old_cycle = state.get("reading_p3_cycle", 0)
    old_cat = READING_P3_CATEGORIES[old_cycle % len(READING_P3_CATEGORIES)]
    new_cycle = log_category("reading_p3_cycle")
    new_cat = READING_P3_CATEGORIES[new_cycle % len(READING_P3_CATEGORIES)]
    print(f"\n  ✓ Reading P3 category logged: {old_cat}")
    print(f"    Next cycle → {new_cat}\n")


def cmd_get_listening_p4_category():
    cat, cycle = get_next_category(LISTENING_P4_CATEGORIES, "listening_p4_cycle", "Listening P4")
    print(f"\n  → Recommended Listening Part 4 category: {cat} (cycle position {cycle % len(LISTENING_P4_CATEGORIES)})\n")


def cmd_log_listening_p4_category():
    state = load_usage_state()
    old_cycle = state.get("listening_p4_cycle", 0)
    old_cat = LISTENING_P4_CATEGORIES[old_cycle % len(LISTENING_P4_CATEGORIES)]
    new_cycle = log_category("listening_p4_cycle")
    new_cat = LISTENING_P4_CATEGORIES[new_cycle % len(LISTENING_P4_CATEGORIES)]
    print(f"\n  ✓ Listening P4 category logged: {old_cat}")
    print(f"    Next cycle → {new_cat}\n")


# ---------------------------------------------------------------------------
# CLI dispatch
# ---------------------------------------------------------------------------

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
    elif cmd == "get_reading_p3_category":
        cmd_get_reading_p3_category()
    elif cmd == "log_reading_p3_category":
        cmd_log_reading_p3_category()
    elif cmd == "get_listening_p4_category":
        cmd_get_listening_p4_category()
    elif cmd == "log_listening_p4_category":
        cmd_log_listening_p4_category()
    else:
        print(__doc__)
        sys.exit(1)
