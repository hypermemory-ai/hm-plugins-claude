#!/usr/bin/env bash
# SessionStart + UserPromptSubmit: print the full HyperMemory skill so it is in
# context at every session start, after every compaction and on every prompt,
# instead of relying on the agent to choose to load it.
skill="${1:-${CLAUDE_PLUGIN_ROOT:-}}/skills/hypermemory/SKILL.md"
if [ ! -f "$skill" ]; then
  echo "HYPERMEMORY SKILL MISSING at $skill. Tell the user the HyperMemory skill could not be loaded."
  exit 0
fi
echo "MANDATORY: Call hm_recall NOW, before generating any response text. On first message also call hm_get_overview."
echo "=== /hypermemory SKILL (auto-loaded by the HyperMemory plugin hook; this IS the skill — follow every rule in it this turn) ==="
cat "$skill"
echo "=== end /hypermemory SKILL ==="
