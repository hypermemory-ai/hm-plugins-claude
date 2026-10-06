#!/usr/bin/env python3
"""Stop hook: refuse to end a turn until HyperMemory's memory writer has been dispatched.

A turn starts at the last prompt Ken typed (slash commands included). Automated
background-task notifications and compaction summaries are not turns. The turn
may end only when it contains an Agent call with subagent_type
hypermemory:memory-writer, and that call is followed by assistant text (the
dispatch must never be the last action).
"""
import json
import re
import sys

WRITER = "hypermemory:memory-writer"
# The skill's lightweight skip: a prompt of at most 80 characters that is only a greeting or acknowledgement.
ACKNOWLEDGEMENTS = {"hey", "hello", "hi", "howdy", "thanks", "thank you", "okay", "ok", "got it"}


def is_lightweight(text):
    words = re.sub(r"[^a-z ]+", " ", text.lower()).split()
    return len(text.strip()) <= 80 and bool(words) and " ".join(words) in ACKNOWLEDGEMENTS


def user_text(message):
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        if any(part.get("type") == "tool_result" for part in content):
            return None
        return " ".join(part.get("text", "") for part in content if part.get("type") == "text")
    return None


def is_turn_start(entry):
    if entry.get("type") != "user" or entry.get("isMeta") or entry.get("isCompactSummary"):
        return False
    text = user_text(entry.get("message") or {})
    if not text or not text.strip():
        return False
    return not text.lstrip().startswith("<task-notification>")


def main():
    hook_input = json.load(sys.stdin)
    entries = []
    with open(hook_input["transcript_path"], encoding="utf-8") as transcript:
        for line in transcript:
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    start = None
    for index, entry in enumerate(entries):
        if is_turn_start(entry):
            start = index
    if start is None or is_lightweight(user_text(entries[start]["message"])):
        return

    dispatched = False
    text_after_dispatch = False
    for entry in entries[start + 1:]:
        if entry.get("type") != "assistant":
            continue
        for part in (entry.get("message") or {}).get("content") or []:
            if part.get("type") == "tool_use" and part.get("name") == "Agent" \
                    and (part.get("input") or {}).get("subagent_type") == WRITER:
                dispatched = True
                text_after_dispatch = False
            elif part.get("type") == "text" and part.get("text", "").strip() and dispatched:
                text_after_dispatch = True

    if not dispatched:
        reason = (
            "BLOCKED by the HyperMemory Stop hook: this turn has no hypermemory:memory-writer dispatch. "
            "Dispatch it now with durable knowledge from this turn (decisions, facts, lessons in plain "
            "language, 50-300 character descriptions, hashes only in data) plus the TOKENS block, "
            "then write a closing line."
        )
    elif not text_after_dispatch:
        reason = (
            "BLOCKED by the HyperMemory Stop hook: the memory-writer dispatch was the last action. "
            "Write a closing line after it."
        )
    else:
        return
    print(json.dumps({"decision": "block", "reason": reason}))


if __name__ == "__main__":
    main()
