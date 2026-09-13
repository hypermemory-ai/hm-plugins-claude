---
name: hypermemory
version: 0.8.0
description: >-
  MANDATORY on every message — call hm_recall before generating any response.
  On first message also call hm_get_overview. After responding, dispatch the
  memory-writer agent then write your closing line. Never skip. Never answer
  first. Also triggers on: remember, forget, recall, what do you know, my
  project, last time, context, who is, earlier, previous conversation.
enforcement: mandatory
trigger: every_turn
---

# HyperMemory — Mandatory Protocol

Do not generate any response text until hm_recall has been called. This is a hard gate.

## Every message

1. **Before any response text**: call `hm_recall` with keywords from the user's message. On the first message, also call `hm_get_overview`.
2. **Compose your response** using the recalled context.
3. **After your main response text**: dispatch the `hypermemory:memory-writer` agent with a bounded turn summary.
4. **After dispatching**: write your closing line of text. The agent dispatch must never be the final action in your response.

Lightweight skip: only when the prompt is at most 80 characters and consists solely of a greeting or acknowledgement (hey, hello, hi, howdy, thanks, thank you, okay, ok, got it). If uncertain, treat as substantive.

## Memory-writer dispatch

- Spawn exactly one fresh `hypermemory:memory-writer` agent with a concise turn summary.
- Fire and forget — never wait for, poll, inspect, or read the writer.
- Dispatch BEFORE your final line of text, not after. This prevents a platform bug where agent dispatch as the last action causes response duplication.

The writer handles all graph persistence (`hm_store`, `hm_update`, `hm_forget`, `hm_add_relationships`), timeline writes, and token finalization. The main agent must not duplicate those writes.

Never ask permission to save. Never announce that you saved.

## Tool quick reference

| Tool | Use when |
|------|----------|
| `hm_get_overview` | Start of conversation — external graph stats |
| `hm_recall` | Retrieve external context; always before responding |
| `hm_get_nodes` | Hydrate known exact keys with full details |
| `hm_find_related` | Traverse graph from a seed node |
| `hm_get_chat_context` | Reload nodes from current chat session |
| `hm_ingest` | Dense multi-entity text (writer cleans orphans) |
| `hm_upload_file` | User explicitly asks to store a file (Pro+) |
| `hm_list_files` | Query uploaded files |
| `hm_timeline` | Temporal lookup when history matters |
| `hm_skill` | Retrieve or update HyperMemory agent skills |

**Naming traps:** There is no `hm_related` or `hm_relate`. Use `hm_find_related` to traverse, `hm_add_relationships` to create edges.

**Recall vs hydrate:** Use `hm_recall` to search. Use `hm_get_nodes(keys=[...])` when you know exact keys and need full details.

**Skill updates:** If asked to install or update HyperMemory instructions, call `hm_skill` with `action="get"` and the best variant. Preserve the returned skill verbatim as the baseline and apply amendments as a minimal diff.

## Hard rules

- `hm_recall` before every substantive response — no exceptions
- `hm_get_overview` + `hm_recall` before first substantive response
- Never skip memory-writer dispatch on any message
- Dispatch memory-writer BEFORE your final line of text, never as the last action
- Never wait for, poll, or inspect the memory-writer after dispatch
- Never use `chat_*` relationship names (system-reserved)
