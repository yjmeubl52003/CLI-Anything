# ACE Studio CLI

A stateful command-line interface for inspecting and lightly controlling ACE Studio through its official local MCP server.

## Prerequisites

- Python 3.10+
- ACE Studio 2.x installed and running
- ACE Studio MCP Server enabled in `Preferences -> General -> MCP Server`

Default MCP endpoint:

```text
http://localhost:21572/mcp
```

## Install

From the `agent-harness/` directory:

```bash
pip install -e .
```

If the command is not found after installation, your user script directory may not be on `PATH`.
On this machine it was installed to:

```text
/Users/chelsea/Library/Python/3.10/bin/cli-anything-acestudio
```

Optional richer REPL experience:

```bash
pip install "cli-anything-acestudio[repl]"
```

## Quick Check

```bash
cli-anything-acestudio server ping
cli-anything-acestudio server capabilities --json
```

## Core Commands

### Project

```bash
cli-anything-acestudio project info
cli-anything-acestudio project playback-status
cli-anything-acestudio project synthesis-status
cli-anything-acestudio project tempo-list --json
cli-anything-acestudio project timesig-list --json
cli-anything-acestudio project set-tempo --points-json '[{"pos":0,"value":120},{"pos":1920,"value":128,"bend":0}]' --replace-all --json
cli-anything-acestudio project set-timesig --signatures-json '[{"barPos":0,"numerator":4,"denominator":4},{"barPos":8,"numerator":3,"denominator":4}]' --replace-all --json
```

### Track

```bash
cli-anything-acestudio track list
cli-anything-acestudio track meta 0 --json
cli-anything-acestudio track selected
cli-anything-acestudio track rename 0 --name "Lead Vox"
cli-anything-acestudio track set-color 0 --color "#4FC3F7"
cli-anything-acestudio track select --track-index 0 --track-index 1
cli-anything-acestudio track clear-selection
cli-anything-acestudio track set-mute 0 on
cli-anything-acestudio track set-solo 0 off
cli-anything-acestudio track set-pan 0 --pan -0.25
cli-anything-acestudio track set-gain 0 --gain 0.9
cli-anything-acestudio track set-record 0 --listen on --midi-source custom --midi-device "Keyboard" --midi-channel 1
cli-anything-acestudio track delete --dry-run
```

**Delete warning:** `track delete` permanently removes selected tracks and all their content (clips, notes, etc.). Use `track select` to select tracks first, then `--dry-run` to preview.

### Clip

```bash
cli-anything-acestudio clip list 0
cli-anything-acestudio clip meta 0 0 --time-unit tick --json
cli-anything-acestudio clip notes 0 0 --range-scope project --json
cli-anything-acestudio clip lyrics 0 0 --json
cli-anything-acestudio clip audio-info 1 0 --json
cli-anything-acestudio clip add 0 --pos 0 --dur 1920 --type sing --name "Verse Lead"
cli-anything-acestudio clip move-edges --uuid "clip-uuid" --side left --mode diff --value -480 --dry-run
```

### Sound Source

```bash
cli-anything-acestudio sound-source list --type voice --language en --json
cli-anything-acestudio sound-source tags --type voice
cli-anything-acestudio sound-source community-list --page 0 --json
cli-anything-acestudio sound-source collect-community --id 12345
cli-anything-acestudio sound-source load 0 --kind singer --id 12345 --group official
cli-anything-acestudio sound-source unload 0 --dry-run
```

**Unload warning:** `sound-source unload` causes DATA LOSS — it downgrades Sing/Instrument tracks to Generic MIDI, losing lyrics, vocal controls, and articulations. Always use `--dry-run` first.

### Conversion

```bash
cli-anything-acestudio convert tick-to-time 4800
cli-anything-acestudio convert time-to-tick 3.5
cli-anything-acestudio convert tick-to-measure 9600 --consider-beat-mode
cli-anything-acestudio convert measure-to-tick 4 120 --consider-beat-mode --beat-pos 2
```

### Transport and Navigation

```bash
cli-anything-acestudio transport play
cli-anything-acestudio transport stop
cli-anything-acestudio metronome get
cli-anything-acestudio metronome set on
cli-anything-acestudio loop get
cli-anything-acestudio loop set-range --start 0 --end 1920
cli-anything-acestudio marker get --scope global
cli-anything-acestudio marker seek --seconds 12.5
cli-anything-acestudio ui mixer hide
cli-anything-acestudio ui special-track chord show
```

### Workflow

```bash
cli-anything-acestudio workflow song-skeleton --dry-run --spec-json '{
  "tempo": [{"pos":0,"value":120}],
  "timesig": [{"barPos":0,"numerator":4,"denominator":4}],
  "sections": [
    {"name":"Intro","bars":4},
    {"name":"Verse 1","bars":8},
    {"name":"Chorus 1","bars":8}
  ],
  "tracks": [
    {"role":"lead","track_index":0,"clip_type":"sing","prefix":"Lead"},
    {"role":"guide","track_index":1,"clip_type":"genericmidi","prefix":"Guide"}
  ]
}' --json
```

This workflow expects existing tracks in the current ACE Studio project. It will:

- replace the current tempo map
- replace the current time signature map
- calculate section boundaries by bar count
- create section clips on the specified existing tracks
- optionally load sound sources when `sound_source` is present in a track spec

### Editor

Pattern editor commands operate on the currently open editor (determined by marker-line position). The editor must be open and visible before using write commands.

```bash
cli-anything-acestudio editor availability
cli-anything-acestudio editor clip
cli-anything-acestudio editor content
cli-anything-acestudio editor selection
cli-anything-acestudio editor selection-range --range-begin 0 --range-end 1920 --select-notes
cli-anything-acestudio editor modify-selection --mode replace --notes-to-select-json '[{"uuid":"abc123"}]'
cli-anything-acestudio editor add-notes --lyric-sentence "hello world" --notes-json '[{"pos":0,"dur":480,"pitch":60}]' --offset 0 --language English
cli-anything-acestudio editor delete-selection --dry-run
```

**Add notes modes:**
- Sentence mode (recommended): `--lyric-sentence "sing a song"` with `--notes-json` for automatic syllable distribution
- Per-note mode: `--lyric "la la la"` with `--notes-json`

**Lyric formats for Sing clips:**
- Syllable: `word#index` for multi-syllable words (e.g., `happy#1`, `happy#2`)
- Tenuto: `-` to extend a syllable across multiple notes (e.g., `la - - -` extends "la" across 4 notes)

**Delete selection guard:**
- `--dry-run` previews what would be deleted without actually deleting

### Arrangement

Arrangement view commands operate on the track view (timeline + tracks).

```bash
cli-anything-acestudio arrangement get-selection
cli-anything-acestudio arrangement make-selection --track-begin 0 --track-end 2 --tick-begin 0 --tick-end 1920
cli-anything-acestudio arrangement delete-selection --dry-run
cli-anything-acestudio arrangement move-selection --target-tick 3840 --target-track-index 1 --dry-run
```

**Workflow for deleting clips:**
1. `arrangement make-selection` to create a selection range
2. `arrangement get-selection` to verify the selection
3. `arrangement delete-selection --dry-run` to preview
4. `arrangement delete-selection` to execute

**Workflow for moving clips:**
1. `arrangement make-selection` to create a selection range
2. `arrangement move-selection --target-tick 3840 --target-track-index 1 --dry-run` to preview
3. `arrangement move-selection --target-tick 3840 --target-track-index 1` to execute

**Note:** Track indices can be negative for special tracks (tempo track, time signature track).

## JSON Output

Add `--json` to any command for machine-readable output:

```bash
cli-anything-acestudio --json track list
```

## Interactive REPL

Run without a subcommand:

```bash
cli-anything-acestudio
```

Inside the REPL, type `help` for a summary or `quit` to exit.

## Scope

Current scope includes:

- Project, track, and clip inspection
- Sound source browsing
- Tempo and position conversion
- Playback, metronome, loop, and marker control
- Low-risk track write operations
- Clip creation
- Community voice collection and sound source loading
- ACE Studio UI visibility toggles
- Editor inspection (availability, clip, content, selection)
- Editor note insertion (sentence and per-note modes)
- Editor selection range and modification
- Editor delete selection (with --dry-run guard)
- Arrangement selection (make/get) for timeline operations
- Arrangement delete/move selection (with --dry-run guard)
- Clip edge trimming/moving (move-edges with --dry-run guard)
- Sound source unload (with --dry-run guard, data loss warning)
- Track deletion for selected tracks (with --dry-run guard)

Not yet implemented:

- Project open/save automation
- Export/render control
- `.acep` parsing

## Write Command Rules

- `track set-record` is intentionally strict: invalid parameter combinations fail fast.
- `--midi-device` and `--midi-channel` require `--midi-source custom`.
- `clip add` reports overlap warnings in `precheck`, but does not block creation.
- `sound-source load` requires `--group` for `singer` and `choir`.
- `project set-tempo` and `project set-timesig` are full-map replacements and require `--replace-all`.
- Tempo points must be strictly increasing by `pos`; time signatures must be strictly increasing by `barPos`.
- `workflow song-skeleton` also replaces tempo and time signatures as part of the workflow.
- `workflow song-skeleton --dry-run` previews the plan without writing clips or loading sound sources.

## Running Tests

```bash
cd agent-harness
python3 -m unittest cli_anything.acestudio.tests.test_core -v
python3 -m unittest cli_anything.acestudio.tests.test_full_e2e -v
```
