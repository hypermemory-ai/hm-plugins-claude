# HyperMemory Plugin for Claude

Persistent memory graph for Claude Code and Claude Desktop. Automatically
recalls relevant context at the start of every turn and persists new knowledge
in the background after every response.

## Claude Code (full plugin)

Claude Code gets the complete experience: automatic recall, background
persistence via a sub-agent, and the full protocol skill.

### Install

```
/install hypermemory-ai/hm-plugins-claude
```

Or step by step:

```
/plugin marketplace add hypermemory-ai/hm-plugins-claude
/plugin install hypermemory
```

The MCP server authenticates via OAuth — you'll be prompted to sign in on
first use.

### What gets installed

| Component | Purpose |
|-----------|---------|
| **MCP Server** | HyperMemory API with OAuth authentication |
| **Skill** | `/hypermemory` — v0.6.6 software-development protocol |
| **Agent** | `memory-writer` — background sub-agent for store/update/token ops |
| **Hooks** | `UserPromptSubmit` forces recall; `Stop` spawns persistence agent |

### How it works

1. **User sends a message** — the `UserPromptSubmit` hook fires, instructing
   Claude to call `hm_get_overview` (first message only) and `hm_recall` with
   keywords from the message. This happens synchronously before the response.

2. **Claude responds normally**, informed by recalled context.

3. **Response finishes** — the `Stop` hook fires, instructing Claude to spawn
   the `memory-writer` agent in the background with a summary of the turn. The
   agent handles `hm_store`, `hm_update`, `hm_forget`, and `hm_tokens` without
   blocking the user's next interaction.

### Direct interaction

Memory operations are automatic, but you can also:

- Ask Claude to "remember" something — forces immediate store
- Ask "what do you know about X" — deep recall + graph traversal
- Ask to "forget X" — removes from graph
- Use `/hypermemory` to load the full protocol reference

---

## Claude Desktop (MCP only)

Claude Desktop does not support plugins, hooks, or agents. You can still
connect to HyperMemory via MCP, but the automatic recall/write lifecycle
requires a project-level instruction file.

### Step 1: Add the MCP server

Open Claude Desktop settings and add this MCP server configuration:

```json
{
  "mcpServers": {
    "hypermemory": {
      "type": "http",
      "url": "https://stage.hypermemory.io/mcp"
    }
  }
}
```

You'll be prompted to authenticate via OAuth on first use.

### Step 2: Add project instructions (recommended)

To get automatic recall/write behavior similar to the Claude Code plugin,
create a `CLAUDE.md` file in your project directory:

```markdown
# HyperMemory Instructions

Before every response, silently perform HyperMemory recall:
1. If this is the first message, call `hm_get_overview`
2. Call `hm_recall` with keywords from the user's message
3. Use recalled context to inform your response

After every response, silently persist new knowledge:
1. Call `hm_recall` to check for duplicates
2. New facts → `hm_store` with key, description, node_type, relationships
3. Existing facts that changed → `hm_update`
4. Wrong facts → `hm_forget`
5. Call `hm_tokens` once with segmentation estimates

Never ask permission to save. Never announce memory operations.
```

Note: Without hooks, Claude Desktop cannot guarantee memory runs on every turn.
The `CLAUDE.md` instructions are best-effort.

---

## Platform comparison

| Feature | Claude Code | Claude Desktop |
|---------|:-----------:|:--------------:|
| MCP server (hm tools) | automatic | manual config |
| Recall on every turn | guaranteed (hook) | best-effort (CLAUDE.md) |
| Background persistence | guaranteed (hook + agent) | best-effort (CLAUDE.md) |
| Non-blocking writes | yes (sub-agent) | no |
| Skill reference | `/hypermemory` | not available |
| Install method | `/plugin install` | manual MCP config |

---

## Development

This plugin points to the HyperMemory staging server
(`stage.hypermemory.io`).
