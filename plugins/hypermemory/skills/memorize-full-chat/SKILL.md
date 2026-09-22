---
name: memorize-full-chat
description: >-
  Commit an entire conversation to HyperMemory at full fidelity — every
  entity, fact, figure, decision, source, and correction from the first turn
  to the last, as specific, cross-linked nodes rather than a handful of
  summaries. Use when the user says "commit this chat to memory", "save
  everything from this conversation", "go back to the beginning and store it
  all", "memorize this whole chat", "memorize full chat", or invokes
  /memorize-full-chat.
---

# Memorize Full Chat

The user wants the **whole conversation** in the graph. The failure mode this
skill exists to prevent: reading the chat from a compressed impression, writing
10–15 summary nodes, and calling it done. A 25-turn research chat typically
contains 100–300 distinct memorable things. Summaries are not memories.

Do this work **in the main agent**. Do not hand it to the memory-writer
sub-agent — it only receives a bounded summary, which is exactly how content
gets lost.

Work in four phases. Do not start writing nodes until the ledger exists.

---

## The core rule: decompose, never enumerate

**A node's description must never contain a list of things that could each be
a node.** When the chat names a set of things — trades, people, competitors,
services, ingredients, clauses, species, features, bugs, sources — every
member becomes its own node. The set becomes a category node that the members
point to. The category's description says what the set *is* and how it is
organized, not who is in it.

The test for any noun in a description: *could the user ever ask about this
thing by name?* If yes, it is a node, not a word in someone else's
description.

| Chat talks about | Wrong (one node) | Right |
|---|---|---|
| trades in feudal Japan | `concept_japanese_trades` listing "cobbler, woodworker, farmer, samurai…" | one node per trade; `concept_japanese_trades` as the category |
| a microservice architecture | `project_backend` listing "auth, billing, search, notifications" | one `component_*` per service; project links to each |
| competitors in a market | `concept_crm_market` listing "Salesforce, HubSpot, Pipedrive" | one `organization_*` per competitor |
| a recipe | `artifact_ramen_recipe` listing ingredients | one node per notable ingredient/technique |
| a contract review | `artifact_msa_review` listing flagged clauses | one node per clause issue |

Nest when the chat nests: set → subgroups → members, each level a node.
A member mentioned only by name still gets a node; describe it from
everything the chat says or implies about it (its category, period, domain,
role), so it stands alone.

### Connect the members to each other

Membership edges (`woodworker is a trade in Sengoku Japan`) are the minimum,
not the goal. For every member, look for how it relates to its **siblings**
and to members of **other** sets in the chat:

- supplies, depends on, feeds into (`charcoal burner supplies fuel to swordsmith`)
- ranks above/below, governs, serves (`samurai class held authority over farmers`)
- competes with, substitutes for, contrasts with
- precedes, evolved into, replaced
- same location, same guild/team, same era, same author
- contradicts, corrects

Add an edge only when the chat supports it or it is definitional; never
invent relationships to hit a count. When the chat genuinely gives no
connection between two siblings, the shared category edge is enough.

---

## Phase 1 — Get the full source

Your context may be compacted; earlier turns may only survive as a summary.
Never work from that summary when the raw transcript is available.

**Claude Code:** the transcript is a JSONL file that keeps every turn even
after compaction. Export it to a readable file:

```bash
dir="$HOME/.claude/projects/$(pwd | sed 's/[^A-Za-z0-9]/-/g')"
f="$dir/$(ls -t "$dir" | grep '\.jsonl$' | head -1)"
jq -r 'select(.type=="user" or .type=="assistant") | select(.isSidechain!=true)
  | .message as $m
  | ($m.content | if type=="string" then [{type:"text",text:.}] else . end)[]
  | if .type=="text" then "\n### \($m.role|ascii_upcase)\n\(.text)"
    elif .type=="tool_use" then "\n[tool_use \(.name)] \(.input|tostring|.[0:400])"
    elif .type=="tool_result" then "\n[tool_result] \((.content|if type=="string" then . else (map(.text? // "")|join(" ")) end)|.[0:6000])"
    else empty end' "$f" > transcript.md
wc -l transcript.md
```

Write `transcript.md` to the scratchpad directory if one exists. The newest
`.jsonl` in the project directory is the current session. Tool results matter:
in research chats, most of the facts live in fetched pages and search results,
not in the assistant's prose.

**No transcript file (Claude Desktop, claude.ai, other clients):** work from
the conversation in context. If any part of it has been compacted or
summarized, tell the user which range you can no longer see verbatim.

Read the source in order, in chunks (roughly 5 turns or 400 lines at a
time). Do not skim.

---

## Phase 2 — Build the ledger

For each chunk, extract every item worth remembering into a ledger file
(`ledger.md` in the scratchpad). One line per item:

```
T07 | person   | person_manase_dosan   | physician 1507–1594, founded Keiteki-in, 3000+ students | -> concept_ri_zhu_medicine, place_kyoto
```

Fields: source turn, node type, proposed key, the specifics, and the peers it
should link to.

Extract all of these, not only the headline:

- **Entities** — every person, organization, place, product, tool, work,
  profession, component, species, term. Each list item the chat produced is
  its own ledger line, and the list itself is one more line (the category).
  A table with 20 rows is 20 ledger lines plus one.
- **Facts with specifics** — numbers, dates, measurements, prices, versions,
  quotes, names. Keep the figure; "large" is not a fact, "7,720 households" is.
- **Decisions** — what was chosen, what was rejected, and why.
- **Corrections** — anything the user or a source corrected ("komoso, not
  komuso"). These are high value; they prevent the same mistake later.
- **Preferences and constraints** the user expressed.
- **Sources** — URLs, papers, books, files consulted, as artifact nodes
  linked to the facts they support.
- **Open questions and next steps** the chat left unresolved.
- **Relationships between items** — causes, contrasts, parts, sequences,
  dependencies, contradictions.

Skip conversation mechanics (greetings, "let me check", tool-call chatter).

**Density check before moving on:** count ledger lines per substantive turn.
Fewer than ~4 on a content-heavy turn means you are summarizing — reread that
turn. Tell the user the total ledger count before writing.

---

## Phase 3 — Write

1. `hm_recall` for each cluster of the ledger (not every line — group by
   topic) to find existing nodes. Existing node → `hm_update` it with the new
   specifics. Never create a duplicate.
2. `hm_store` **one node per ledger line** with a specific `node_type`. Do not
   use `hm_ingest` for this — it collapses entities and leaves orphans.
   Independent stores can be issued in parallel batches.
3. Every node gets:
   - a **self-contained description**: someone reading only this node, cold,
     understands what it is and why it matters, with the chat's specifics
     (names, numbers, dates) intact;
   - a **data payload** matching the type conventions in the main
     `hypermemory` skill (or a recalled node of the same type);
   - **at least one relationship to a peer**, not just to a hub. Use the peer
     column from the ledger. The relationship says *why* they connect.
4. Create one topic/project hub node for the conversation's subject, if none
   exists, as an entry point. Hubs are entry points; cross-links are the graph.
5. After all nodes exist, a second pass with `hm_add_relationships` for
   cross-links whose targets didn't exist yet when their source was stored.
6. When a sustained topic produced 5+ nodes, one hyperedge naming the higher
   concept (e.g. `{topic}_research_corpus`), following the hyperedge policy.
   Never create `chat_*` relationships.

Keys describe what a thing is (`person_manase_dosan`), never how it was found
(`research_item_12`, `chat_topic_3`).

---

## Phase 4 — Verify and report

1. Reconcile: every ledger line maps to a stored or updated key. List any
   that failed and retry them.
2. **List scan:** reread every description you wrote. Any description that
   names three or more things that pass the "could the user ask about it by
   name" test fails. Split those things into their own nodes, link them, and
   rewrite the parent as a category description.
3. `hm_list_orphans` — connect or delete every orphan you created.
4. Spot-check recall: run 3–5 `hm_recall` queries on specific facts from
   early, middle, and late in the chat. If a fact doesn't come back, fix the
   node's description or `search_text`.
5. Report to the user:
   - turns covered (and any range lost to compaction),
   - ledger items → nodes created / nodes updated / edges added / hyperedges,
   - the hub key(s) to start from,
   - anything deliberately skipped and why.

Keep the report short. The graph is the deliverable.

---

## Scale

For chats too large to finish in one pass, process the ledger in batches of
~40 items, report progress between batches, and keep going until the ledger
is exhausted. Do not stop early and call the result complete.

At the end of the turn, the memory-writer dispatch still happens, but its
summary should only record that a memorize-full-chat run occurred and its counts —
not re-store the content.
