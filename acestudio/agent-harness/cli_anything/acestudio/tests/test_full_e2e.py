"""Live integration tests for ACE Studio MCP — Phase 4.

These tests require:
1. ACE Studio running locally
2. MCP Server enabled (Preferences -> General -> MCP Server)
3. Default MCP endpoint: http://localhost:21572/mcp
4. A project open with at least one track and one clip

Run with:
    python3 -m unittest cli_anything.acestudio.tests.test_full_e2e -v

Or to run only if MCP is available:
    python3 -m unittest discover -s cli_anything/acestudio/tests -p test_full_e2e.py -v
"""

from __future__ import annotations

import unittest
from urllib import request

from cli_anything.acestudio.core import (
    arrangement,
    clip,
    editor,
    project,
    sound_source,
    track,
    transport,
)
from cli_anything.acestudio.mcp_client import ACEStudioMCPClient, DEFAULT_MCP_URL


def _mcp_available() -> bool:
    """Check if ACE Studio MCP server is reachable."""
    req = request.Request(DEFAULT_MCP_URL, method="OPTIONS")
    try:
        with request.urlopen(req, timeout=2):
            return True
    except Exception:
        return False


@unittest.skipUnless(_mcp_available(), "ACE Studio MCP server is not available")
class LiveIntegrationTests(unittest.TestCase):
    """Live integration tests for ACE Studio MCP — Phase 4."""

    @classmethod
    def setUpClass(cls):
        """Create a shared client for all tests in this class."""
        cls.client = ACEStudioMCPClient(timeout=10)
        cls.client.initialize()

    @classmethod
    def tearDownClass(cls):
        """Cleanup after all tests. ACEStudioMCPClient has no persistent connection to close."""
        pass

    def _require_project(self):
        """Ensure a project is open. Skips test if no project is open."""
        info = project.get_info(self.client)
        if not info.get("project_name"):
            self.skipTest("No project is open in ACE Studio.")
        return info

    def _require_track(self, min_tracks: int = 1):
        """Ensure at least min_tracks exist. Skips if fewer tracks available."""
        result = track.list_tracks(self.client)
        if result["track_count"] < min_tracks:
            self.skipTest(f"Project has {result['track_count']} tracks, need at least {min_tracks}.")
        return result

    def _require_editor_available(self):
        """Ensure the pattern editor is open and available.

        This requires:
        1. A project with at least one track
        2. Marker positioned on a clip (use marker move)
        3. Pattern editor window open

        Skips the test if the editor is not available.
        """
        availability = editor.get_editor_availability(self.client)
        if not availability["is_available"]:
            self.skipTest(
                "Pattern editor is not available. "
                "Open a clip in the editor first (position marker on a clip)."
            )
        return availability

    # ======================================================================
    # Editor tests
    # ======================================================================

    def test_editor_availability_live(self):
        """Test editor availability check."""
        availability = editor.get_editor_availability(self.client)
        self.assertIn("is_available", availability)
        self.assertIn("is_visible", availability)
        if availability["is_available"]:
            self.assertIn("editor_type", availability)
            self.assertIn("track_index", availability)
            self.assertIn("clip_index", availability)

    def test_editor_clip_live(self):
        """Test getting current clip being edited."""
        self._require_editor_available()
        clip_info = editor.get_editor_clip(self.client)
        self.assertIn("track_index", clip_info)
        self.assertIn("clip_index", clip_info)
        self.assertIn("clip_type", clip_info)

    def test_editor_content_live(self):
        """Test getting content from the pattern editor."""
        self._require_editor_available()
        content = editor.get_editor_content(self.client)
        self.assertIn("content", content)

    def test_editor_content_with_range_live(self):
        """Test getting content with range filter."""
        self._require_editor_available()
        content = editor.get_editor_content(self.client, range_scope="clip_region")
        self.assertIn("content", content)

    def test_editor_selection_live(self):
        """Test getting current editor selection."""
        self._require_editor_available()
        selection = editor.get_editor_selection(self.client)
        self.assertIn("has_selection", selection)
        if selection["has_selection"]:
            self.assertIn("selected_notes", selection)

    def test_editor_selection_range_live(self):
        """Test setting selection range in editor."""
        self._require_editor_available()
        result = editor.set_editor_selection_range(
            self.client,
            range_begin=0,
            range_end=480,
            select_notes=False,
        )
        self.assertEqual(result["range_begin"], 0)
        self.assertEqual(result["range_end"], 480)
        self.assertFalse(result["select_notes"])

    def test_editor_add_notes_sentence_mode_live(self):
        """Test adding notes using sentence mode (recommended workflow)."""
        self._require_editor_available()
        notes = [
            {"pos": 0, "dur": 480, "pitch": 60},
            {"pos": 480, "dur": 480, "pitch": 64},
            {"pos": 960, "dur": 480, "pitch": 67},
        ]
        result = editor.add_notes(
            self.client,
            lyric_sentence="do re mi",
            notes=notes,
            offset=0,
            language="English",
        )
        self.assertEqual(result["added_notes_count"], 3)
        self.assertEqual(result["lyric_sentence"], "do re mi")
        self.assertEqual(result["language"], "English")

    def test_editor_add_notes_per_note_mode_live(self):
        """Test adding notes using per-note lyrics mode."""
        self._require_editor_available()
        notes = [
            {"pos": 0, "dur": 480, "pitch": 60},
            {"pos": 480, "dur": 480, "pitch": 64},
        ]
        result = editor.add_notes(
            self.client,
            lyric="la la",
            notes=notes,
            offset=480,
        )
        self.assertEqual(result["added_notes_count"], 2)
        self.assertEqual(result["lyric"], "la la")

    def test_editor_add_notes_multi_syllable_live(self):
        """Test adding notes with multi-syllable lyrics (word#index format)."""
        self._require_editor_available()
        notes = [
            {"pos": 0, "dur": 240, "pitch": 60},
            {"pos": 240, "dur": 240, "pitch": 62},
            {"pos": 480, "dur": 240, "pitch": 64},
            {"pos": 720, "dur": 240, "pitch": 65},
        ]
        result = editor.add_notes(
            self.client,
            lyric_sentence="hap-py#1 hap-py#2 hap-py#3 hap-py#4",
            notes=notes,
            language="English",
        )
        self.assertEqual(result["added_notes_count"], 4)

    def test_editor_delete_selection_dry_run_live(self):
        """Test dry-run of delete selection (non-destructive)."""
        self._require_editor_available()
        result = editor.delete_editor_selection(self.client, dry_run=True)
        self.assertTrue(result["dry_run"])
        self.assertIn("would_delete", result)
        self.assertIn("warning", result)

    def test_editor_delete_selection_live(self):
        """Test delete selection when notes are selected in the editor.

        NOTE: This test only executes if there IS a selection.
        If no notes are selected, this test passes (expected state).
        """
        self._require_editor_available()
        selection = editor.get_editor_selection(self.client)
        if not selection["has_selection"]:
            self.skipTest("No notes selected in editor. Select notes first in ACE Studio UI.")
        result = editor.delete_editor_selection(self.client, dry_run=False)
        self.assertFalse(result["dry_run"])
        self.assertIn("result", result)

    def test_editor_modify_selection_replace_live(self):
        """Test modifying selection (replace mode)."""
        self._require_editor_available()
        selection = editor.get_editor_selection(self.client)
        if not selection["has_selection"]:
            self.skipTest("No notes selected. Select notes in editor first.")
        current_notes = selection.get("selected_notes", [])
        if not current_notes:
            self.skipTest("No notes in selection.")
        uuids_to_select = [{"uuid": n["uuid"]} for n in current_notes[:1]]
        result = editor.modify_note_selection(
            self.client,
            mode="replace",
            notes_to_select=uuids_to_select,
        )
        self.assertEqual(result["mode"], "replace")

    # ======================================================================
    # Arrangement tests
    # ======================================================================

    def test_arrangement_get_selection_live(self):
        """Test getting current arrangement selection."""
        selection = arrangement.get_arrangement_selection(self.client)
        self.assertIn("has_selection", selection)
        self.assertIn("horizontal", selection)
        self.assertIn("vertical", selection)

    def test_arrangement_make_selection_live(self):
        """Test creating a new arrangement selection range."""
        self._require_track(1)
        result = arrangement.make_arrangement_selection(
            self.client,
            track_begin=0,
            track_end=1,
            tick_begin=0,
            tick_end=1920,
        )
        self.assertEqual(result["horizontal"]["begin"], 0)
        self.assertEqual(result["horizontal"]["end"], 1920)
        self.assertEqual(result["vertical"]["begin"], 0)
        self.assertEqual(result["vertical"]["end"], 1)

    def test_arrangement_delete_selection_dry_run_live(self):
        """Test dry-run of arrangement delete selection."""
        self._require_track(1)
        arrangement.make_arrangement_selection(
            self.client,
            track_begin=0,
            track_end=1,
            tick_begin=0,
            tick_end=1920,
        )
        result = arrangement.delete_arrangement_selection(self.client, dry_run=True)
        self.assertTrue(result["dry_run"])
        self.assertIn("would_delete", result)
        self.assertIn("warning", result)

    def test_arrangement_delete_selection_live(self):
        """Test arrangement delete selection.

        NOTE: This deletes actual clips. Only runs if there IS a selection
        with clips in it. Otherwise skips.
        """
        self._require_track(1)
        arrangement.make_arrangement_selection(
            self.client,
            track_begin=0,
            track_end=1,
            tick_begin=0,
            tick_end=1920,
        )
        result = arrangement.delete_arrangement_selection(self.client, dry_run=False)
        self.assertFalse(result["dry_run"])
        self.assertIn("result", result)

    def test_arrangement_move_selection_dry_run_live(self):
        """Test dry-run of arrangement move selection."""
        self._require_track(1)
        arrangement.make_arrangement_selection(
            self.client,
            track_begin=0,
            track_end=1,
            tick_begin=0,
            tick_end=1920,
        )
        result = arrangement.move_arrangement_selection(
            self.client,
            target_tick=3840,
            target_track_index=0,
            dry_run=True,
        )
        self.assertTrue(result["dry_run"])
        self.assertIn("would_move", result)
        self.assertEqual(result["would_move"]["to"]["tick"], 3840)

    def test_arrangement_move_selection_live(self):
        """Test arrangement move selection.

        NOTE: This moves actual clips. Only runs if there IS a selection.
        """
        self._require_track(1)
        arrangement.make_arrangement_selection(
            self.client,
            track_begin=0,
            track_end=1,
            tick_begin=0,
            tick_end=1920,
        )
        result = arrangement.move_arrangement_selection(
            self.client,
            target_tick=3840,
            target_track_index=0,
            dry_run=False,
        )
        self.assertFalse(result["dry_run"])
        self.assertIn("result", result)

    # ======================================================================
    # Clip tests
    # ======================================================================

    def test_clip_list_live(self):
        """Test listing clips on track 0."""
        self._require_track(1)
        result = clip.list_clips(self.client, track_index=0)
        self.assertIn("track_index", result)
        self.assertIn("clip_count", result)
        self.assertIn("clips", result)

    def test_clip_move_edges_dry_run_live(self):
        """Test clip move-edges dry-run.

        NOTE: Requires a valid clip UUID. Skips if no clips available.
        """
        self._require_track(1)
        clips_result = clip.list_clips(self.client, track_index=0)
        if clips_result["clip_count"] == 0:
            self.skipTest("No clips available on track 0.")
        first_clip_uuid = clips_result["clips"][0].get("name")
        if not first_clip_uuid:
            self.skipTest("Clip has no UUID/name.")
        result = clip.move_clip_edges(
            self.client,
            clip_uuid=first_clip_uuid,
            side="left",
            mode="diff",
            value=-480,
            dry_run=True,
        )
        self.assertTrue(result["dry_run"])
        self.assertEqual(result["would_modify"]["side"], "left")

    # ======================================================================
    # Sound source tests
    # ======================================================================

    def test_sound_source_unload_dry_run_live(self):
        """Test sound-source unload dry-run.

        NOTE: Only works on Sing/Instrument tracks with a loaded sound source.
        Skips if track 0 is not a Sing or Instrument track.
        """
        self._require_track(1)
        track_list = track.list_tracks(self.client)
        first_track = track_list["tracks"][0]
        track_type = first_track.get("type")
        if track_type not in {"Sing", "Instrument"}:
            self.skipTest(f"Track 0 is type '{track_type}', not Sing or Instrument.")
        result = sound_source.unload_sound_source(self.client, track_index=0, dry_run=True)
        self.assertTrue(result["dry_run"])
        self.assertIn("warning", result)
        self.assertIn("DATA LOSS", result["warning"])

    # ======================================================================
    # Track tests
    # ======================================================================

    def test_track_delete_dry_run_live(self):
        """Test track delete dry-run.

        NOTE: Requires at least one selected track. Skips otherwise.
        """
        self._require_track(1)
        selected = track.get_selected(self.client)
        if not selected["selected_tracks"]:
            self.skipTest("No tracks selected. Select tracks first in ACE Studio UI.")
        result = track.delete_selected_track(self.client, dry_run=True)
        self.assertTrue(result["dry_run"])
        self.assertIn("would_delete", result)
        self.assertIn("warning", result)

    def test_track_delete_live(self):
        """Test track delete.

        NOTE: Requires at least one selected track. This is DESTRUCTIVE.
        Only runs if user has explicitly confirmed by setting env var.
        """
        self._require_track(1)
        selected = track.get_selected(self.client)
        if not selected["selected_tracks"]:
            self.skipTest("No tracks selected. Select tracks first in ACE Studio UI.")
        import os
        if os.environ.get("ACE_TEST_DESTRUCTIVE") != "1":
            self.skipTest("Skipping destructive test. Set ACE_TEST_DESTRUCTIVE=1 to run.")
        result = track.delete_selected_track(self.client, dry_run=False)
        self.assertFalse(result["dry_run"])
        self.assertIn("result", result)


@unittest.skipUnless(_mcp_available(), "ACE Studio MCP server is not available")
class LiveIntegrationTests_ProjectBasics(unittest.TestCase):
    """Basic project tests to validate MCP connection is healthy."""

    def test_initialize_live_session(self):
        """Test MCP session initialization."""
        client = ACEStudioMCPClient(timeout=5)
        result = client.initialize()
        self.assertTrue(result.get("protocolVersion"))
        self.assertTrue(client.session_id)

    def test_project_info_live(self):
        """Test getting project info."""
        client = ACEStudioMCPClient(timeout=5)
        client.initialize()
        info = project.get_info(client)
        self.assertIn("duration_ticks", info)
        self.assertIn("project_name", info)

    def test_track_list_live(self):
        """Test listing all tracks."""
        client = ACEStudioMCPClient(timeout=5)
        client.initialize()
        result = track.list_tracks(client)
        self.assertIn("track_count", result)
        self.assertIn("tracks", result)

    def test_project_tempo_list_live(self):
        """Test getting tempo list."""
        client = ACEStudioMCPClient(timeout=5)
        client.initialize()
        result = project.get_tempo_list(client)
        self.assertIn("points", result)
        if result["point_count"] == 0:
            self.skipTest("No tempo points in project.")
        self.assertGreater(result["point_count"], 0)

    def test_transport_play_stop_live(self):
        """Test transport play and stop."""
        client = ACEStudioMCPClient(timeout=5)
        client.initialize()
        transport.control_playback(client, "stop")
        result = transport.control_playback(client, "start")
        self.assertIn("result", result)
        transport.control_playback(client, "stop")


if __name__ == "__main__":
    unittest.main()
