---
name: acestudio
description: Inspect the current ACE Studio project, browse tracks and clips, query lyrics and notes, control playback, and edit notes in the pattern editor through the local ACE Studio MCP server.
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
- Inspecting the pattern editor and adding notes with lyrics
- Managing editor selection and deleting selected notes

## Key Commands

```bash
cli-anything-acestudio server ping
cli-anything-acestudio project info
cli-anything-acestudio track list --json
cli-anything-acestudio clip lyrics 0 0 --json
cli-anything-acestudio sound-source list --type voice --json
cli-anything-acestudio transport play
cli-anything-acestudio editor availability
cli-anything-acestudio editor clip
cli-anything-acestudio editor add-notes --lyric-sentence "hello world" --notes-json '[{"pos":0,"dur":480,"pitch":60}]' --language English
cli-anything-acestudio editor delete-selection --dry-run
cli-anything-acestudio arrangement get-selection
cli-anything-acestudio arrangement make-selection --track-begin 0 --track-end 2 --tick-begin 0 --tick-end 1920
cli-anything-acestudio arrangement delete-selection --dry-run
cli-anything-acestudio sound-source unload 0 --dry-run
cli-anything-acestudio track delete --dry-run
cli-anything-acestudio workflow song-skeleton --dry-run --spec-json '{"tempo":[{"pos":0,"value":120}],"timesig":[{"barPos":0,"numerator":4,"denominator":4}],"sections":[{"name":"Intro","bars":4},{"name":"Verse 1","bars":8}],"tracks":[{"role":"lead","track_index":0,"clip_type":"sing","prefix":"Lead"}]}' --json
```

## Editor Workflow

The pattern editor must be open and focused on the target clip before using editor write commands. Use `marker move` to position the marker on the desired clip, then use `editor availability` to verify the editor is ready.

### Adding Notes

**Sentence mode (recommended):**
```bash
cli-anything-acestudio editor add-notes \
  --lyric-sentence "sing a song" \
  --notes-json '[{"pos":0,"dur":480,"pitch":60},{"pos":480,"dur":480,"pitch":64},{"pos":960,"dur":480,"pitch":67}]' \
  --language English
```

**Lyric formats:**
- Multi-syllable words: `happy#1` (first syllable), `happy#2` (second syllable)
- Tenuto (extend syllable): `la - - -` extends "la" across 4 notes
- Mixed: `hello#1 - hello#2 day` (first syllable, tenuto, second syllable, then "day")

### Deleting Notes

1. Select notes in the editor UI, or use `editor selection-range`
2. Preview with `--dry-run`
3. Execute without `--dry-run` to delete

```bash
cli-anything-acestudio editor delete-selection --dry-run
```

## Arrangement Workflow

Use `arrangement` commands to select and manipulate clips in the timeline.

### Selecting and Deleting Clips

```bash
# Create a selection range (track 0-1, tick 0-1920)
cli-anything-acestudio arrangement make-selection --track-begin 0 --track-end 2 --tick-begin 0 --tick-end 1920

# Verify the selection
cli-anything-acestudio arrangement get-selection

# Preview what would be deleted
cli-anything-acestudio arrangement delete-selection --dry-run

# Execute deletion
cli-anything-acestudio arrangement delete-selection
```

### Moving Clips

```bash
# Preview move to tick 3840, track 1
cli-anything-acestudio arrangement move-selection --target-tick 3840 --target-track-index 1 --dry-run

# Execute move
cli-anything-acestudio arrangement move-selection --target-tick 3840 --target-track-index 1
```

**Guard rails:**
- All destructive operations (delete-selection, move-selection) support `--dry-run` for preview.
- Selection ranges support negative track indices for special tracks (tempo, time signature).

## Sound Source Workflow

Use `sound-source unload` to downgrade a Sing or Instrument track to Generic MIDI. This is typically used when:
- Switching between incompatible voice/instrument types
- Removing a sound source entirely

**WARNING — DATA LOSS:** This operation permanently removes lyrics, vocal controls, articulations, and other track-specific features. Only basic MIDI note data is preserved.

```bash
# Preview what will be unloaded
cli-anything-acestudio sound-source unload 0 --dry-run

# Execute (data loss cannot be recovered automatically)
cli-anything-acestudio sound-source unload 0
```

**Guard rails:**
- Always use `--dry-run` first to verify the target track.
- Only Sing and Instrument tracks can be unloaded; GenericMidi and Audio tracks will be rejected.
- The operation is undoable from ACE Studio's undo system, but lost data (lyrics, vocal controls) cannot be recovered automatically.

## Track Workflow

Use `track delete` to remove selected tracks from the project.

```bash
# Select tracks to delete (can select multiple)
cli-anything-acestudio track select --track-index 0 --track-index 1

# Preview what will be deleted
cli-anything-acestudio track delete --dry-run

# Execute deletion
cli-anything-acestudio track delete
```

**Guard rails:**
- Tracks must be selected first using `track select`.
- `--dry-run` is required by default to prevent accidental deletion.
- The operation is undoable from ACE Studio's undo system, but all track content (clips, notes) is lost.

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
- Editor commands require the pattern editor to be open and visible.
- `editor delete-selection` is destructive; use `--dry-run` first.

## Notes

- If ACE Studio is closed or MCP is disabled, commands will fail fast with a clear error.
- Editor write commands require the pattern editor to be open (use `marker move` to position the marker on a clip, then verify with `editor availability`).
- Destructive operations should always be previewed with `--dry-run` before execution.
- `sound-source unload` causes irreversible data loss for track-specific features.
