#!/usr/bin/env bash
# Ensure CLAUDE.md exists and contains HyperMemory instructions.
# Runs on SessionStart — idempotent, skips if already configured.

set -euo pipefail

MARKER="# HyperMemory"
BLOCK='# HyperMemory

Before every response, load and apply /hypermemory. This applies to every single message.

## HyperMemory Usage

At the start of every conversation:
1. Call `hm_get_overview` to see what exists
2. Call `hm_recall` with relevant queries to load context
3. Use recalled info to personalize responses

During every conversation:
- Store new information automatically using `hm_store`
- Never ask "should I remember this?" - just store it
- Use `hm_update` to modify existing memories
- Use `hm_upload_file` when the user asks to store a file (Pro+ plans)
- Use `hm_list_files` to query uploaded files'

# Find the git root, or fall back to cwd
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
TARGET="$ROOT/CLAUDE.md"

if [ -f "$TARGET" ]; then
  # Already has HyperMemory section — nothing to do
  if grep -qF "$MARKER" "$TARGET" 2>/dev/null; then
    exit 0
  fi
  # Append to existing file
  printf '\n\n%s\n' "$BLOCK" >> "$TARGET"
else
  # Create new file
  printf '%s\n' "$BLOCK" > "$TARGET"
fi
