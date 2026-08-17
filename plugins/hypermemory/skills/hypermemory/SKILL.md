---
name: hypermemory-software-development
version: 0.6.8
description: >-
  Mandatory every-turn HyperMemory protocol for AI coding tools and agents,
  including Claude Code, Codex, Cursor, and other MCP-capable development
  environments. Use in every session and project, including every user turn,
  to recall and store durable context, write a chronological timeline entry,
  and submit complete, accurately classified token telemetry. Preserve
  technical context, implementation decisions, codebase facts, debugging
  history, and deployment constraints.
enforcement: mandatory
trigger: every_turn
---

# HyperMemory Software Development Skill

Use this skill when helping with software engineering, code review, debugging,
architecture, deployment, or technical planning.

## MANDATORY: Memory-writer agent — every turn, no exceptions

YOU MUST launch the `hypermemory:memory-writer` background agent as your LAST
action on every single turn. Use:

```
Agent(subagent_type: "hypermemory:memory-writer", description: "Persist turn to HyperMemory", prompt: "<summary of this turn>")
```

**Do not substitute inline hm_store / hm_update / hm_forget / hm_tokens calls
for the memory-writer agent.** The memory-writer performs comprehensive
persistence — dedup checks, relationship wiring, orphan prevention, and token
reporting — that ad-hoc inline calls cannot replicate.

Do not ask the user. Do not mention it in your response. Do not skip it because
you already called some hm_* tools this turn. Just launch it silently in the
background as your final action.

## Start Of Work

1. Call `hm_get_overview`.
2. Call `hm_recall` for the repository, feature, bug, service, and tool names.
3. Use `hm_get_nodes(keys=[...])` for exact keys when you need full,
   untruncated records, structured data, assets, duplicates, or relationships.
4. Use recalled and hydrated constraints before proposing or changing anything.

## What To Remember

Store durable engineering context:

- Architecture decisions and the reason they were made.
- Production constraints, deployment topology, service ownership, and rollback or recovery requirements.
- Bugs, root causes, fixes, test evidence, and commands that verified the result.
- User preferences about coding style, release process, branching, commits, and documentation.
- Important file paths, APIs, schemas, queue names, model names, environment variables, and external services.

Update existing nodes when facts change. Do not create duplicates for the same
component, bug, project, or decision.

Use only canonical ontology classes for `node_type`. Common classes include
`user person organization component event decision concept artifact project
technology preference fact skill`. Do not invent new `node_type` values or
ontology classes. If uncertain, omit `node_type` or choose the closest
canonical class; HyperMemory resolves invalid or missing input internally
before persistence.

## Relationship Guidance

Always connect technical memories to the relevant project, service, component,
or decision.

Examples:

```json
{"to_key": "component_mcp_server", "relationship": "signup provisioning fix depends on Supabase OTP verification before account lifecycle creation"}
```

Use `hm_find_related` before touching complex systems so related constraints are
visible.

Use `hm_add_relationships` to connect nodes that already exist. Storing a
duplicate node just to carry an edge is the most common way a technical graph
degrades.

## Granularity and structure

Prefer many specific nodes over few summary nodes. When work produces a list
of discrete entities — people, tools, professions, components — each one is
its own node, not a line item in a parent's description. Key nodes by what
they are (`profession_yamabushi`, `person_manase_dosan`), not by how they
were discovered (`research_batch_item_3`).

Connect peers to peers. A relationship between two sibling nodes is worth more
than both of them pointing at a shared hub. Hub nodes are acceptable as entry
points but the real graph value is in the cross-links between the entities
themselves.

Don't conserve nodes. A graph with 200 well-connected nodes recalls better
than one with 5 summaries.

## Graph Hygiene

- `hm_forget` removes a memory that turned out to be wrong. Correcting the
  record matters more here than in most domains: a stale root cause or a
  retired deployment constraint will be recalled and acted on.
- `hm_list_orphans` finds nodes with no relationships. Connect the ones worth
  keeping and forget the rest; an orphan is invisible to `hm_find_related`
  and so is effectively unrecallable.
- `hm_get_chat_context` reloads prior conversation context for the current
  session when continuity has been lost.

## Timeline Reporting

This protocol is mandatory on every turn in every session and project. Call
`hm_timeline_write` exactly once on every turn before the final response. This
is required even when the turn is short, conversational, diagnostic, blocked,
or produces no file changes.

Write a concise chronological summary that records:

- What the user requested, decided, corrected, or clarified.
- What the agent actually did during the turn.
- The material result, decision, blocker, or next state.
- The session ID, project or workspace, and relevant memory node keys in
  `meta` when known.

Read the timeline with `hm_timeline` when you need what happened before —
which deployment broke a thing, what was already tried, when a decision was
taken. `hm_recall` answers what is true now; `hm_timeline` answers what
happened, and a debugging session usually needs both.

Timeline reporting is separate from graph memory and token reporting.
`hm_store`, `hm_update`, `hm_ingest`, and `hm_tokens` do not replace
`hm_timeline_write`. Do not limit timeline entries to notable debugging
milestones or deployments. Use additional timeline entries only for distinct
major milestones within a long-running turn; the required end-of-turn entry
must still summarize the complete turn.

## Token Reporting

This protocol is mandatory on every turn in every session and project. During
end-of-turn finalization, call `hm_tokens` exactly once with the same session ID
and a monotonically increasing turn sequence. Never treat token reporting as a
compliance checkbox or submit only the minimum fields accepted by the server.

### Codex exact-token helper

When `hm-codex-tokens` is installed, use it instead of manually estimating or
calling the MCP `hm_tokens` tool. The helper reads only Codex `token_count`
counters from local rollout JSONL files and invokes the canonical `hm_tokens`
endpoint once. Do not also call MCP `hm_tokens` on the same turn.

Run it after `hm_timeline_write`, as the last tool action before the final
response:

```bash
hm-codex-tokens submit \
  --session-id "<codex-session-uuid>" \
  --turn-sequence <n> \
  --model "<model>" \
  --segments-json '[{"category":"coding","weight":80},{"category":"context","weight":15},{"category":"memory","weight":5}]'
```

Treat the returned counters as `client_exact`. The helper advances its durable
checkpoint only after HyperMemory accepts the report. A later turn picks up
model calls that occur after the prior turn's submission. If the helper is
missing or fails, fall back to `self_estimated`, include uncertainty, and state
the fallback honestly; never invent exact counts.

### Consumer ChatGPT estimation

Consumer ChatGPT does not expose Codex rollout counters. Estimate the complete
model workload, not only the latest user message or visible final answer:

1. Estimate the input context for every model invocation, including system and
   skill instructions, conversation context, tool definitions, retrieved
   documents, and tool results.
2. Add the output and reasoning produced by every invocation.
3. Count continuations after tool results as additional model invocations.
4. Sanity-check long or tool-heavy turns. A report must scale with both context
   size and invocation count; do not submit a small fixed estimate after a
   large multi-tool workflow.
5. Report `measurement_quality: self_estimated`,
   `uncertainty_percentage: 40`, and an honest `estimation_bias`. Prefer
   `high` when missing context or hidden tool loops could cause undercounting.

The target is a useful estimate within roughly plus or minus 40 percent, not
false precision. Severe systematic under-reporting is unacceptable.

Submit the fullest truthful telemetry available:

- `input_tokens`, `output_tokens`, and `total_tokens`.
- `reasoning_tokens` and `cache_tokens` when exposed by the AI tool, or when a
  defensible estimate is possible.
- Exact client counts with `measurement_quality: client_exact` when available.
- Otherwise, carefully reasoned `self_estimated` values, an uncertainty
  percentage appropriate to the tool (normally 40 for consumer chat clients),
  and an honest estimation bias.
- `cost_usd` only when its provenance is legitimate; never invent cost.

Omit a field only when it is unavailable and cannot be defensibly estimated.
Never label an estimate as exact or provider-verified.

Every report must use one or more weighted activity categories totaling exactly
100:
`reasoning`, `memory`, `context`, `doc_processing`, `automation`,
`personal`, `chatting`, `research`, `design`, `calculations`, `coding`,
`planning`, `productivity`, `writing`, or `unmatched`.

Each category may appear at most once in a report. If multiple activities map
to the same category, combine them into one segment and add their weights; do
not submit duplicate category entries.

Classify the work performed on the turn, not the conversational wording of the
request:

1. For software-development agents and software work, use `coding` as the
   default substantive activity. This includes implementation, debugging,
   testing, code review, repository inspection, architecture work tied to a
   codebase, deployment work, and technical configuration.
2. Use `planning` only when the AI tool is explicitly operating in a planning
   mode or the requested deliverable is a plan rather than implementation.
3. Ballpark `memory` and `context` as overhead based on the actual turn. Do not
   let either replace the substantive activity.
4. Normally assign zero to `design`, `productivity`, `chatting`,
   `calculations`, `doc_processing`, `research`, `writing`, `personal`, and
   `automation`. Include one only when that activity was genuinely performed
   as a material part of the turn.
5. Before submission, verify that the activity weights total exactly 100 and
   that the largest share represents the turn's real work.

Typical software implementation report:

```json
[
  {"category": "coding", "weight": 80},
  {"category": "context", "weight": 15},
  {"category": "memory", "weight": 5}
]
```

Typical planning-only report:

```json
[
  {"category": "planning", "weight": 75},
  {"category": "context", "weight": 20},
  {"category": "memory", "weight": 5}
]
```

Do not use a fixed `memory: 10` and `context: 90` split for software work; that
destroys activity attribution. Do not use the removed `mem_ingest` or
`mem_retrieve` categories.

When reporting `cost_usd`, also set `cost_quality`: `provider_actual` only for a
provider-billed amount, `price_calculated` for exact tokens multiplied by known
model pricing, or `self_estimated` for an approximate amount. Use `unavailable`
when no cost is supplied. Token measurement quality and cost quality are separate.

For OpenRouter responses, submit client-visible token fields and weighted
segments. HyperMemory treats them as provisional attribution and reconciles
them with management analytics for the OpenRouter key mapped to the user. Never
invent provider-actual values. Claude Desktop uses `self_estimated`, includes
uncertainty, and does not report API-equivalent dollar cost.

Use `hm_recall` to discover candidate nodes. Use `hm_get_nodes` only for exact
known keys that need inspection/debugging or full fidelity context.

## Files And Structured Data

- `hm_upload_file` stores a file only when the user explicitly asks for it.
  Source code belongs in git, not in the graph.
- `hm_list_files` reports what is already stored, so a re-upload does not
  create a second copy of the same document.
- `hm_tabular` queries stored structured data — CSVs, exports, spreadsheets —
  as rows rather than prose. Reach for it instead of recalling a whole
  document and reading numbers out of it by eye.

## Do Not Store

- Full secrets, API keys, passwords, or private tokens.
- Large code blobs that should stay in git.
- Unverified guesses; store root causes only after evidence supports them.

## Skill Updates

When asked to install or update HyperMemory behavior, call `hm_skill` with
`variant="software-development"`.
