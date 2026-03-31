# ACE Studio CLI Harness SOP

## Backend

This harness targets the official ACE Studio MCP server exposed by ACE Studio 2.x.

- Default endpoint: `http://localhost:21572/mcp`
- Transport: HTTP POST JSON-RPC with MCP session headers
- Initialization sequence:
  1. `initialize`
  2. capture `Mcp-Session-Id`
  3. `notifications/initialized`

## Scope for v1

This first pass intentionally focuses on read-only inspection and low-risk transport controls.

Implemented domains:

- Server health and tool discovery
- Project inspection
- Track inspection
- Clip inspection
- Sound source browsing
- Tempo/time conversion
- Playback, metronome, loop, and marker controls

Deferred domains:

- Destructive editing
- Project lifecycle control (new/open/save)
- Export/render automation
- `.acep` reverse engineering
- Internal binary integration

## Safety Notes

- Many ACE Studio MCP write tools are context-sensitive and may trim or delete content.
- This harness avoids those operations in v1.
- Commands should fail fast with explicit errors when MCP is unavailable or UI context is missing.
