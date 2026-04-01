# TEST.md

## Phase 4 Results

### Live Integration Test Coverage

**28 live integration tests** written in `test_full_e2e.py` covering:

#### LiveIntegrationTests (23 tests)
- **Editor** (12 tests): availability, clip, content (with/without range), selection, selection-range, add-notes (sentence mode, per-note mode, multi-syllable), delete-selection (dry-run + live), modify-selection
- **Arrangement** (6 tests): get-selection, make-selection, delete-selection (dry-run + live), move-selection (dry-run + live)
- **Clip** (2 tests): list, move-edges dry-run
- **Sound Source** (1 test): unload dry-run
- **Track** (2 tests): delete dry-run, delete live (requires `ACE_TEST_DESTRUCTIVE=1`)

#### LiveIntegrationTests_ProjectBasics (5 tests)
- Session initialization
- Project info, tempo list, track list
- Transport play/stop

### Test Results (Current Environment)

```
Ran 28 tests in 0.083s
OK (skipped=22)
```

**22 tests skipped** — preconditions not met:
- No project open with tracks (ACE Studio not running with a loaded project)
- Pattern editor not available (requires marker on clip + editor window open)
- No tempo points in project

**6 tests passed** — basic MCP connectivity:
- `test_initialize_live_session` ✅
- `test_project_info_live` ✅
- `test_track_list_live` ✅
- `test_transport_play_stop_live` ✅
- `test_editor_availability_live` ✅
- `test_arrangement_get_selection_live` ✅

### Running Live Tests

**Prerequisites:**
1. ACE Studio running locally
2. MCP Server enabled (`Preferences -> General -> MCP Server`)
3. Default MCP endpoint: `http://localhost:21572/mcp`
4. A project open with at least one track

**Run all e2e tests:**
```bash
cd agent-harness
python3 -m unittest cli_anything.acestudio.tests.test_full_e2e -v
```

**Run only if MCP is available (auto-skip otherwise):**
```bash
python3 -m unittest discover -s cli_anything/acestudio/tests -p test_full_e2e.py -v
```

**Run destructive tests (track delete live):**
```bash
ACE_TEST_DESTRUCTIVE=1 python3 -m unittest cli_anything.acestudio.tests.test_full_e2e.LiveIntegrationTests.test_track_delete_live -v
```

**Run editor tests only:**
```bash
python3 -m unittest cli_anything.acestudio.tests.test_full_e2e.LiveIntegrationTests.test_editor_add_notes_sentence_mode_live -v
```

### Unit Tests

**90 unit tests** in `test_core.py` — all passing ✅

```bash
cd agent-harness
python3 -m unittest cli_anything.acestudio.tests.test_core -v
```

### Test Design Principles

1. **Preconditions checked first** — Tests call `_require_*` helpers that skip (not fail) when preconditions aren't met
2. **Destructive tests gated** — `test_track_delete_live` requires `ACE_TEST_DESTRUCTIVE=1` env var
3. **Shared client** — `LiveIntegrationTests` uses a single initialized client for all tests (performance)
4. **Auto-skip on unavailable** — All live tests check `_mcp_available()` at class load time
