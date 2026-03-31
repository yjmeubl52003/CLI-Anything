---
name: acestudio
description: Inspect the current ACE Studio project, browse tracks and clips, query lyrics and notes, and control playback through the local ACE Studio MCP server.
---

# ACE Studio Skill

Use this skill when ACE Studio is already running locally and its MCP server is enabled.

## Best for

- Checking the current project status
- Listing tracks and clip structure
- Reading note or lyric content from clips
- Browsing available voices and instruments
- Converting between ticks, time, and measure positions
- Controlling playback, metronome, loop, and marker position

## Key Commands

```bash
cli-anything-acestudio server ping
cli-anything-acestudio project info
cli-anything-acestudio track list --json
cli-anything-acestudio clip lyrics 0 0 --json
cli-anything-acestudio sound-source list --type voice --json
cli-anything-acestudio transport play
```

## Notes

- This first version is intentionally conservative.
- It does not expose destructive editing commands.
- If ACE Studio is closed or MCP is disabled, commands will fail fast with a clear error.
