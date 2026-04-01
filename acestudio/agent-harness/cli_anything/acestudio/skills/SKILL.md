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
- Generating a song skeleton on existing ACE Studio tracks

## Key Commands

```bash
cli-anything-acestudio server ping
cli-anything-acestudio project info
cli-anything-acestudio track list --json
cli-anything-acestudio clip lyrics 0 0 --json
cli-anything-acestudio sound-source list --type voice --json
cli-anything-acestudio transport play
cli-anything-acestudio workflow song-skeleton --dry-run --spec-json '{"tempo":[{"pos":0,"value":120}],"timesig":[{"barPos":0,"numerator":4,"denominator":4}],"sections":[{"name":"Intro","bars":4},{"name":"Verse 1","bars":8}],"tracks":[{"role":"lead","track_index":0,"clip_type":"sing","prefix":"Lead"}]}' --json
```

## Song Skeleton Workflow

Use `workflow song-skeleton` when the project already has usable target tracks and you want to lay down a song structure quickly.

### Required spec fields

- `tempo`: full tempo map array
- `timesig`: full time signature map array
- `sections`: ordered array of `{name, bars}` entries
- `tracks`: ordered array of track targets

### Track spec shape

```json
{
  "role": "lead",
  "track_index": 0,
  "clip_type": "sing",
  "prefix": "Lead",
  "sound_source": {
    "kind": "singer",
    "id": 12345,
    "group": "official"
  }
}
```

### What it does

1. Validates that the referenced tracks already exist.
2. Replaces the current tempo map.
3. Replaces the current time signature map.
4. Converts cumulative bar counts into tick ranges.
5. Creates one clip per section per target track.
6. Optionally loads one sound source per target track.

### Guard rails

- It does not create tracks from scratch.
- `--dry-run` is recommended before the first real execution.
- Section `target_roles` can limit which tracks receive clips.
- Clip overlap warnings are surfaced through the underlying `clip add` precheck.

## Notes

- This first version is intentionally conservative.
- It does not expose destructive editing commands.
- If ACE Studio is closed or MCP is disabled, commands will fail fast with a clear error.
