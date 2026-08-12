# Security policy

## Reporting a vulnerability

Do not open a public issue for a vulnerability, credential exposure, or tenant
isolation concern. Email `hello@runstack.ai` with a concise description,
affected component, reproduction steps, and impact. Do not include live access
tokens or personal data.

## Security boundaries

- HyperMemory MCP authentication uses OAuth. The plugin contains no API key or
  bearer token.
- Non-managed plugin hooks require explicit trust in Claude Code.
- HyperMemory token telemetry parses counters only and must not upload chat or
  source content.
- The memory-writer sub-agent operates under a bounded role contract. It does
  not expand permissions beyond those of the parent agent.

## Supported versions

Security fixes target the latest version of the plugin on the default branch.
