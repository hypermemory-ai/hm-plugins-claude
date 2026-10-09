---
name: hypermemory
version: 0.9.0
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
3. **After your main response text**: dispatch the `hypermemory:memory-writer` agent with a bounded turn summary and the TOKENS block (see Memory-writer dispatch).
4. **After dispatching**: write your closing line of text. The agent dispatch must never be the final action in your response.

Lightweight skip: only when the prompt is at most 80 characters and consists solely of a greeting or acknowledgement (hey, hello, hi, howdy, thanks, thank you, okay, ok, got it). If uncertain, treat as substantive.

## Memory-writer dispatch

- Spawn exactly one fresh `hypermemory:memory-writer` agent per turn.
- Fire and forget — never wait for, poll, inspect, or read the writer.
- Dispatch BEFORE your final line of text, not after. This prevents a platform bug where agent dispatch as the last action causes response duplication.

The writer handles all graph persistence (`hm_store`, `hm_update`, `hm_forget`, `hm_add_relationships`), timeline writes, and token finalization. The main agent must not duplicate those writes — never call `hm_tokens`, `hm_timeline_write`, or any graph write yourself.

### Dispatch prompt: SUMMARY + TOKENS

The writer cannot see your turn. It reports tokens only from what you hand it, so every dispatch prompt MUST contain both parts below. A dispatch without the TOKENS block is a protocol failure, the same as skipping the dispatch.

```
SUMMARY:
<what the user asked, what you did, what you found or decided>

TOKENS:
session_id: <this session's id>
turn_sequence: <user-turn number in this session, starting at 1>
ai_tool: claude_code
provider: anthropic
model: <your exact model id>
measurement_quality: self_estimated
input_tokens: <estimate>
output_tokens: <estimate>
total_tokens: <input + output>
estimation_bias: low | neutral | high
segments: <category weight, ...>   (e.g. coding 70, memory 20, context 10; unique categories, total exactly 100)
size_facts: tool_calls=<n>; large_outputs=<what, roughly how big>; reply_words=<n>
```

You never see exact token counts, so estimate from what you observed this turn:

- `input_tokens`: every model call re-reads the whole context. Take the context size (system instructions, tool definitions, CLAUDE.md, conversation so far, roughly 40,000+ before any history) and add each tool result as it arrives; the turn's input is about (number of model calls) × (context size at each call). A turn with tool use is typically 50,000–200,000.
- `output_tokens`: reply words × 1.3, plus tool-call arguments. Typically 500–10,000.
- `estimation_bias`: `high` when large tool outputs or many calls make undercounting likely, `low` only for a minimal turn, otherwise `neutral`.
- `segments`: make the turn's real work the largest share. Use only these categories: `reasoning`, `memory`, `context`, `doc_processing`, `automation`, `personal`, `chatting`, `research`, `design`, `calculations`, `coding`, `planning`, `productivity`, `writing`, `unmatched` (deployment, testing and debugging count as `coding`). Use `memory` only for HyperMemory overhead and `context` only for reading.
- `size_facts`: the observations your estimate rests on, so the writer and the user can check it.

Do not send `cost_usd` or `uncertainty_percentage`; the server computes both.

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
| `hm_update` | Update a node (`key`) or edge (`edge_id`). Edge endpoints/type are immutable |
| `hm_forget` | Delete a node (`key`) or single edge (`edge_id`). Edge delete preserves nodes |
| `hm_timeline` | Temporal lookup when history matters |
| `hm_skill` | Retrieve or update HyperMemory agent skills |

**Edge editing:** `hm_update` and `hm_forget` accept an optional `edge_id` (from read responses) to target a single edge. Pass `edge_version` for optimistic concurrency. To change edge endpoints or type, delete and recreate.

**Naming traps:** There is no `hm_related` or `hm_relate`. Use `hm_find_related` to traverse, `hm_add_relationships` to create edges.

**Recall vs hydrate:** Use `hm_recall` to search. Use `hm_get_nodes(keys=[...])` when you know exact keys and need full details.

**Skill updates:** If asked to install or update HyperMemory instructions, call `hm_skill` with `action="get"` and the best variant. Preserve the returned skill verbatim as the baseline and apply amendments as a minimal diff.

## Hard rules

- `hm_recall` before every substantive response — no exceptions
- `hm_get_overview` + `hm_recall` before first substantive response
- Never skip memory-writer dispatch on any message
- Every memory-writer dispatch carries the SUMMARY and the TOKENS block — no TOKENS block, no valid dispatch
- Never call `hm_tokens` from the main agent; the writer reports the TOKENS block
- Dispatch memory-writer BEFORE your final line of text, never as the last action
- Never wait for, poll, or inspect the memory-writer after dispatch
- Never use `chat_*` relationship names (system-reserved)
