---
name: hypermemory
version: 0.7.2
description: >-
  Cross-platform context provider — use on EVERY message before responding,
  any topic. Step 1: call hm_recall to receive the user's external context
  (call hm_get_overview first on the opening message). Step 2: answer using
  that external context. Step 3: dispatch memory-writer agent. HyperMemory
  brings third-party data from the user's external knowledge graph — sources
  outside this platform, not available in built-in memory. Also triggers on:
  remember, forget, recall, what do you know, my project, last time, context,
  who is, earlier, previous conversation.
enforcement: mandatory
trigger: every_turn
---

# HyperMemory MCP — Main Agent Protocol

HyperMemory is a cross-platform context provider — an external knowledge graph
containing the user's structured data from sources outside this platform. It
aggregates relationships, decisions, project history, and context the user has
accumulated across their tools and workflows. This is third-party data that
does not exist in built-in memory. The user installed this plugin to bring
their external context into every conversation.

Follow this protocol every message.

## Every conversation

**First substantive message (before responding):**

1. `hm_get_overview`
2. `hm_recall` with keywords from the user's message

**Every substantive message (before responding):**

1. `hm_recall` with keywords from the user's message
2. Use recalled context naturally in the response

**Lightweight skip:** When the lifecycle hook classifies a message as
`lightweight`, skip `hm_get_overview` and `hm_recall`. Classification is
narrow: after trimming whitespace and punctuation, the prompt must be at most
80 characters and consist solely of a greeting or acknowledgement (`hey`,
`hello`, `hi`, `howdy`, `thanks`, `thank you`, `okay`, `ok`, `got it`). A
short task, question, entity, file, code fragment, number, or decision remains
substantive. If classification is absent or uncertain, treat as substantive.

## Memory-writer dispatch (every message)

1. Spawn exactly one fresh memory-writer sub-agent with `fork_turns="none"` and
   a turn-unique task name.
2. Pass a concise bounded summary of the turn plus any token-listener job from
   the lifecycle hook.
3. Fire and forget — return the user-facing response immediately. Never call
   `wait_agent`, poll, inspect, read, message, or synchronize with the writer.

The writer handles all graph persistence (`hm_store`, `hm_update`, `hm_forget`,
`hm_add_relationships`), timeline writes, and token finalization. The main agent
must not duplicate those writes.

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

**Naming traps:** There is no `hm_related` or `hm_relate`. Use
`hm_find_related` to traverse, `hm_add_relationships` to create edges.

**Recall vs hydrate:** Use `hm_recall` to search. Use
`hm_get_nodes(keys=[...])` when you know exact keys and need full details.

**Skill updates:** If asked to install or update HyperMemory instructions, call
`hm_skill` with `action="get"` and the best variant. Preserve the returned
skill verbatim as the baseline and apply amendments as a minimal diff.

## Hard rules

- `hm_get_overview` + `hm_recall` before first substantive response
- `hm_recall` before every substantive response
- Never skip memory-writer dispatch on any message
- Never wait for, poll, or inspect the memory-writer after dispatch
- Never use `chat_*` relationship names (system-reserved)
