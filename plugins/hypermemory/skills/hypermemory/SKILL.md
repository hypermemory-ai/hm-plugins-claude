---
name: hypermemory
version: 0.13.4
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

## Organization memory

Members of a HyperMemory organization get the organization's memory with their own on every `hm_recall`, searched in parallel, under `organization_memory` (labelled with the organization's `name`). Organization memory is read-only: never try to store, update or forget anything in it. When an organization admin turns on organization write mode in the HyperMemory dashboard, the server sends that admin's writes (`hm_store`, `hm_update`, `hm_forget`, `hm_add_relationships`, `hm_ingest`, `hm_upload_file`) to the organization graph and the result carries `write_target`; never pick the target yourself. To read what was written there, send that organization's `organization_id` to `hm_get_nodes`, `hm_find_related`, `hm_get_overview` or `hm_list_orphans` (the result carries `read_target`); without it they read your own graph. A key or relationship endpoint "not found" during write mode means it is missing from the organization graph: create it there first.

- `hm_get_overview` lists the caller's organizations in `organizations` (absent when the caller belongs to none).
- One organization: nothing to do; it is always searched.
- Several organizations: each project is bound to one of them, or to none, in `~/.config/hypermemory/projects.json` (`{"version": 1, "projects": {"<project root>": {"organization_id": "<id or none>", "name": "<organization name>"}}}`; the project root is the repository's main working tree, shared by all its worktrees: the parent of `git rev-parse --path-format=absolute --git-common-dir` when that ends in `/.git`, else that directory; outside git, the working directory). At session start, read the binding for this project. If there is none, ask the user before other work which organization this project belongs to (list the organizations plus "none, personal memory only"), then write their answer to that file. Send the bound `organization_id` (or `"none"`) on every `hm_recall` for the session.
- `organization_memory.status`: `included` (results attached), `selection_required` (several organizations and no `organization_id` sent: ask and bind as above), `excluded` (`"none"` was sent), `selected_graph` (this credential's graph is the organization graph, so the main results already are its memory), `failed` (tell the user the organization search failed; your own results are still valid).


## Memory-writer dispatch

- Spawn exactly one fresh `hypermemory:memory-writer` agent per turn.
- Fire and forget — never wait for, poll, inspect, or read the writer.
- Dispatch BEFORE your final line of text, not after. This prevents a platform bug where agent dispatch as the last action causes response duplication.

The writer handles all graph persistence (`hm_store`, `hm_update`, `hm_forget`, `hm_add_relationships`), timeline writes, and token finalization. The main agent must not duplicate those writes — never call `hm_tokens`, `hm_timeline_write`, or any graph write yourself.

### Dispatch prompt: SUMMARY + TOKENS

The writer cannot see your turn. It reports tokens only from what you hand it, so every dispatch prompt MUST contain both parts below, with every TOKENS field filled in. The writer never guesses a missing field: when one is missing, or still a placeholder, it sends no token report and says which field was missing, so that turn's usage is lost. A dispatch without the TOKENS block is a protocol failure, the same as skipping the dispatch.

```
SUMMARY:
Request: <what the user asked, in their words>
Rules the user stated: <each standing rule or preference, close to verbatim, with its scope; "none">
Decisions: <each one: chosen / rejected / why>
Findings and open risks: <one per line, each something a later session must know; a problem says what the user saw, in their words>
Done: <what changed, where, and how to undo it>
Changed: <each status or value that changed this turn, old → new, e.g. "rerank cutoff 0.60 → 0.50", "per-account limits: proposed → deployed", "usage rollups: proposed → declined by the user"; "none">
Corrections: <anything earlier memory got wrong, with the evidence; "none">
Details: <commit hashes, IDs, paths, hosts, ports — only here, never in the lines above>

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
segments: <category weight, ...>   (e.g. doc_processing 60, research 25, memory 15; unique categories, total exactly 100)
size_facts: tool_calls=<n>; large_outputs=<what, roughly how big>; reply_words=<n>
```

The writer turns each SUMMARY line into its own memory, so keep the lines apart. A rule the user stated goes under "Rules the user stated", even when you mention it while telling what you did. A risk you found goes under "Findings and open risks", not inside the story of the fix. When this turn proved an earlier memory wrong, say so under "Corrections". When a status or a value changed (approved, deployed, declined, superseded; a cutoff, a limit), name the old and the new one under "Changed": the writer searches for every memory still saying the old one and rewrites it.

You never see exact token counts, so estimate from what you observed this turn:

- `input_tokens`: every model call re-reads the whole context. Take the context size (system instructions, tool definitions, CLAUDE.md, conversation so far, roughly 40,000+ before any history) and add each tool result as it arrives; the turn's input is about (number of model calls) × (context size at each call). A turn with tool use is typically 50,000–200,000.
- `output_tokens`: reply words × 1.3, plus tool-call arguments. Typically 500–10,000.
- `estimation_bias`: `high` when large tool outputs or many calls make undercounting likely, `low` only for a minimal turn, otherwise `neutral`.
- `segments`: make the turn's real work the largest share. Use only these categories: `reasoning`, `memory`, `doc_processing`, `automation`, `personal`, `chatting`, `research`, `design`, `calculations`, `coding`, `planning`, `productivity`, `writing`, `unmatched` (deployment, testing and debugging count as `coding`). Use `memory` only for HyperMemory overhead. There is no `context` category (the server refuses it): reading files and the conversation belongs to the work it served. Never send a fixed split such as memory 10 / context 90.
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
