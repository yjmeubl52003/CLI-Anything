"""Unit tests for ACE Studio CLI core modules and MCP client."""

from __future__ import annotations

import unittest

from cli_anything.acestudio.acestudio_cli import build_parser, normalize_global_args
from cli_anything.acestudio.core import arrangement, clip, convert, editor, project, sound_source, track, transport, ui, workflow
from cli_anything.acestudio.mcp_client import InvalidContextError, ValidationError
from cli_anything.acestudio.mcp_client import ACEStudioMCPClient


class DummyClient:
    def __init__(self, mapping):
        self.mapping = mapping
        self.calls = []

    def call_tool(self, name, arguments=None):
        self.calls.append((name, arguments or {}))
        value = self.mapping[name]
        return value(arguments or {}) if callable(value) else value


class CoreModuleTests(unittest.TestCase):
    def _track_mapping(self):
        return {
            "get_content_track_basic_info_list": {
                "tracks": [
                    {
                        "trackIndex": 0,
                        "trackType": "Sing",
                        "trackName": "Lead",
                        "clipCount": 2,
                        "soundSourceName": "Voice A",
                    }
                ]
            }
        }

    def test_project_info_normalization(self):
        client = DummyClient(
            {
                "get_project_status_info": {
                    "projectName": "demo",
                    "isTempProject": False,
                    "isNewProject": True,
                    "duration": 9600,
                }
            }
        )
        result = project.get_info(client)
        self.assertEqual(result["project_name"], "demo")
        self.assertEqual(result["duration_ticks"], 9600)

    def test_set_tempo_requires_replace_all(self):
        client = DummyClient({"get_tempo_automation": {"points": [{"pos": 0, "value": 120}], "pointCount": 1}})
        with self.assertRaises(ValidationError):
            project.set_tempo_automation(client, [{"pos": 0, "value": 120}], False)

    def test_set_tempo_rejects_unsorted_points(self):
        client = DummyClient({"get_tempo_automation": {"points": [{"pos": 0, "value": 120}], "pointCount": 1}})
        with self.assertRaises(ValidationError):
            project.set_tempo_automation(client, [{"pos": 10, "value": 120}, {"pos": 0, "value": 128}], True)

    def test_set_tempo_rejects_duplicate_positions(self):
        client = DummyClient({"get_tempo_automation": {"points": [{"pos": 0, "value": 120}], "pointCount": 1}})
        with self.assertRaises(ValidationError):
            project.set_tempo_automation(client, [{"pos": 0, "value": 120}, {"pos": 0, "value": 128}], True)

    def test_set_tempo_rejects_out_of_range_bpm(self):
        client = DummyClient({"get_tempo_automation": {"points": [{"pos": 0, "value": 120}], "pointCount": 1}})
        with self.assertRaises(ValidationError):
            project.set_tempo_automation(client, [{"pos": 0, "value": 0}], True)

    def test_set_tempo_payload(self):
        client = DummyClient(
            {
                "get_tempo_automation": {"points": [{"pos": 0, "value": 120}], "pointCount": 1},
                "set_tempo_automation": {"ok": True},
            }
        )
        result = project.set_tempo_automation(client, [{"pos": 0, "value": 128, "bend": 0}], True)
        self.assertEqual(result["point_count_after"], 1)
        self.assertEqual(client.calls[-1], ("set_tempo_automation", {"points": [{"pos": 0, "value": 128, "bend": 0}]}))

    def test_set_timesig_requires_replace_all(self):
        client = DummyClient({"get_timesignature_list": {"signatures": [{"barPos": 0, "numerator": 4, "denominator": 4}], "signatureCount": 1}})
        with self.assertRaises(ValidationError):
            project.set_timesignature_list(client, [{"barPos": 0, "numerator": 4, "denominator": 4}], False)

    def test_set_timesig_rejects_invalid_denominator(self):
        client = DummyClient({"get_timesignature_list": {"signatures": [{"barPos": 0, "numerator": 4, "denominator": 4}], "signatureCount": 1}})
        with self.assertRaises(ValidationError):
            project.set_timesignature_list(client, [{"barPos": 0, "numerator": 4, "denominator": 3}], True)

    def test_set_timesig_rejects_unsorted(self):
        client = DummyClient({"get_timesignature_list": {"signatures": [{"barPos": 0, "numerator": 4, "denominator": 4}], "signatureCount": 1}})
        with self.assertRaises(ValidationError):
            project.set_timesignature_list(
                client,
                [{"barPos": 8, "numerator": 4, "denominator": 4}, {"barPos": 0, "numerator": 3, "denominator": 4}],
                True,
            )

    def test_set_timesig_rejects_duplicate_bar_positions(self):
        client = DummyClient({"get_timesignature_list": {"signatures": [{"barPos": 0, "numerator": 4, "denominator": 4}], "signatureCount": 1}})
        with self.assertRaises(ValidationError):
            project.set_timesignature_list(
                client,
                [{"barPos": 0, "numerator": 4, "denominator": 4}, {"barPos": 0, "numerator": 3, "denominator": 4}],
                True,
            )

    def test_set_timesig_payload(self):
        client = DummyClient(
            {
                "get_timesignature_list": {"signatures": [{"barPos": 0, "numerator": 4, "denominator": 4}], "signatureCount": 1},
                "set_timesignature_list": {"ok": True},
            }
        )
        result = project.set_timesignature_list(client, [{"barPos": 0, "numerator": 3, "denominator": 4}], True)
        self.assertEqual(result["signature_count_after"], 1)
        self.assertEqual(
            client.calls[-1],
            ("set_timesignature_list", {"signatures": [{"barPos": 0, "numerator": 3, "denominator": 4}]}),
        )

    def test_track_list_normalization(self):
        client = DummyClient(self._track_mapping())
        result = track.list_tracks(client)
        self.assertEqual(result["track_count"], 1)
        self.assertEqual(result["tracks"][0]["name"], "Lead")

    def test_clip_list_assigns_indexes(self):
        client = DummyClient(
            {
                "get_content_track_basic_info_list": {
                    "tracks": [
                        {
                            "trackIndex": 3,
                            "trackType": "Sing",
                            "trackName": "Lead",
                            "clipCount": 2,
                            "soundSourceName": "Voice A",
                        }
                    ]
                },
                "get_content_track_clip_basic_info_list": {
                    "clipCount": 2,
                    "clips": [
                        {"clipType": "Sing", "clipName": "A", "clipColor": "#fff", "clipBegin": 0, "clipEnd": 100},
                        {"clipType": "Sing", "clipName": "B", "clipColor": "#000", "clipBegin": 100, "clipEnd": 200},
                    ],
                }
            }
        )
        result = clip.list_clips(client, 3)
        self.assertEqual(result["track_index"], 3)
        self.assertEqual(result["clips"][1]["index"], 1)

    def test_convert_measure_to_tick_passes_beat_pos_only_when_provided(self):
        client = DummyClient({"measure_pos_to_tick": {"tick": 1234}})
        result = convert.measure_to_tick(client, 2, 120, False)
        self.assertEqual(result["tick"], 1234)
        self.assertEqual(
            client.calls[0][1],
            {"barPos": 2, "tickOffset": 120, "considerBeatMode": False},
        )

    def test_transport_move_marker_argument_mapping(self):
        client = DummyClient({"change_marker_line_position": {"ok": True}})
        transport.move_marker(
            client,
            tick=480,
            force_seek=True,
            is_global_tick=False,
            scope="editor",
            set_to_line_selection=False,
            track_index=1,
        )
        self.assertEqual(client.calls[0][0], "change_marker_line_position")
        self.assertTrue(client.calls[0][1]["forceSeek"])
        self.assertFalse(client.calls[0][1]["is_global_tick"])
        self.assertEqual(client.calls[0][1]["scope"], "editor")

    def test_parse_content_prefers_json_text(self):
        parsed = ACEStudioMCPClient._parse_content(
            [
                {"type": "text", "text": "summary"},
                {"type": "text", "text": '{"answer": 42}'},
            ]
        )
        self.assertEqual(parsed, {"answer": 42})

    def test_rename_track_payload(self):
        mapping = self._track_mapping()
        mapping["rename_content_track"] = {"ok": True}
        client = DummyClient(mapping)
        result = track.rename_track(client, 0, "Lead Vox")
        self.assertEqual(result["new_name"], "Lead Vox")
        self.assertEqual(client.calls[-1], ("rename_content_track", {"trackIndex": 0, "newName": "Lead Vox"}))

    def test_set_track_color_requires_palette_match(self):
        mapping = self._track_mapping()
        mapping["get_color_palette"] = {"colors": ["#111111", "#222222"]}
        client = DummyClient(mapping)
        with self.assertRaises(ValidationError):
            track.set_track_color(client, 0, "#333333")

    def test_set_track_pan_rejects_out_of_range(self):
        client = DummyClient(self._track_mapping())
        with self.assertRaises(ValidationError):
            track.set_track_pan(client, 0, 1.5)

    def test_set_track_gain_rejects_negative(self):
        client = DummyClient(self._track_mapping())
        with self.assertRaises(ValidationError):
            track.set_track_gain(client, 0, -0.1)

    def test_set_track_record_requires_updates(self):
        client = DummyClient(self._track_mapping())
        with self.assertRaises(ValidationError):
            track.set_track_record_settings(client, 0)

    def test_set_track_record_rejects_invalid_custom_combo(self):
        client = DummyClient(self._track_mapping())
        with self.assertRaises(ValidationError):
            track.set_track_record_settings(client, 0, midi_source="all", midi_device="Keyboard 1")

    def test_set_track_record_payload_contains_only_requested_fields(self):
        mapping = self._track_mapping()
        mapping["set_content_track_record_setting"] = {"ok": True}
        client = DummyClient(mapping)
        track.set_track_record_settings(client, 0, listen=True, midi_source="custom", midi_device="Keyboard 1", midi_channel=3)
        self.assertEqual(
            client.calls[-1],
            (
                "set_content_track_record_setting",
                {
                    "trackIndex": 0,
                    "listen": True,
                    "midiInputSourceType": "custom",
                    "midiInputDeviceName": "Keyboard 1",
                    "midiInputChannel": 3,
                },
            ),
        )

    def test_clip_add_reports_overlap(self):
        mapping = self._track_mapping()
        mapping["get_content_track_clip_basic_info_list"] = {
            "clipCount": 1,
            "clips": [{"clipType": "Sing", "clipName": "A", "clipColor": "#fff", "clipBegin": 0, "clipEnd": 100}],
        }
        mapping["add_new_clip"] = {"clipName": "B", "clipBegin": 50, "clipEnd": 150}
        client = DummyClient(mapping)
        result = clip.add_clip(client, 0, 50, 100, "sing", "B")
        self.assertTrue(result["precheck"]["overlaps_existing_clips"])
        self.assertEqual(client.calls[-1][0], "add_new_clip")

    def test_move_clip_edges_requires_valid_side(self):
        client = DummyClient({})
        with self.assertRaises(ValidationError):
            clip.move_clip_edges(client, "abc", "middle", "diff", 100)

    def test_move_clip_edges_requires_valid_mode(self):
        client = DummyClient({})
        with self.assertRaises(ValidationError):
            clip.move_clip_edges(client, "abc", "left", "relative", 100)

    def test_move_clip_edges_rejects_empty_uuid(self):
        client = DummyClient({})
        with self.assertRaises(ValidationError):
            clip.move_clip_edges(client, "  ", "left", "diff", 100)

    def test_move_clip_edges_dry_run(self):
        mapping = {
            "get_content_track_basic_info_list": {
                "tracks": [{"trackIndex": 0, "trackType": "Sing", "trackName": "Lead", "clipCount": 1}],
            }
        }
        client = DummyClient(mapping)
        result = clip.move_clip_edges(client, "clip-uuid-123", "left", "diff", -480, dry_run=True)
        self.assertTrue(result["dry_run"])
        self.assertEqual(result["would_modify"]["side"], "left")
        self.assertEqual(result["would_modify"]["mode"], "diff")

    def test_move_clip_edges_executes(self):
        mapping = {
            "get_content_track_basic_info_list": {
                "tracks": [{"trackIndex": 0, "trackType": "Sing", "trackName": "Lead", "clipCount": 1}],
            },
            "move_clip_edges": {"ok": True},
        }
        client = DummyClient(mapping)
        result = clip.move_clip_edges(client, "clip-uuid-123", "right", "abs", 1920, dry_run=False)
        self.assertFalse(result["dry_run"])
        self.assertEqual(client.calls[-1][0], "move_clip_edges")
        self.assertEqual(client.calls[-1][1]["side"], "right")
        self.assertEqual(client.calls[-1][1]["mode"], "abs")

    def test_load_sound_source_requires_group_for_singer(self):
        mapping = self._track_mapping()
        mapping["get_content_track_meta_settings"] = {"trackType": "Sing"}
        client = DummyClient(mapping)
        with self.assertRaises(ValidationError):
            sound_source.load_sound_source(client, 0, "singer", 123)

    def test_collect_community_voice_rejects_non_positive_id(self):
        client = DummyClient({})
        with self.assertRaises(ValidationError):
            sound_source.collect_community_voice(client, 0)

    def test_unload_sound_source_rejects_non_sing_track(self):
        mapping = {
            "get_content_track_basic_info_list": {
                "tracks": [{"trackIndex": 0, "trackType": "GenericMidi", "trackName": "MIDI"}],
            },
            "get_content_track_meta_settings": {"trackType": "GenericMidi"},
        }
        client = DummyClient(mapping)
        with self.assertRaises(ValidationError):
            sound_source.unload_sound_source(client, 0)

    def test_unload_sound_source_dry_run(self):
        mapping = {
            "get_content_track_basic_info_list": {
                "tracks": [{"trackIndex": 0, "trackType": "Sing", "trackName": "Lead", "soundSourceName": "Tenor-1", "clipCount": 1}],
            },
            "get_content_track_meta_settings": {"trackType": "Sing", "soundSourceInfo": {"soundSourceName": "Tenor-1"}},
        }
        client = DummyClient(mapping)
        result = sound_source.unload_sound_source(client, 0, dry_run=True)
        self.assertTrue(result["dry_run"])
        self.assertEqual(result["would_unload"]["track_index"], 0)
        self.assertIn("DATA LOSS", result["warning"])

    def test_unload_sound_source_executes(self):
        mapping = {
            "get_content_track_basic_info_list": {
                "tracks": [{"trackIndex": 0, "trackType": "Sing", "trackName": "Lead", "soundSourceName": "Tenor-1", "clipCount": 1}],
            },
            "get_content_track_meta_settings": {"trackType": "Sing", "soundSourceInfo": {"soundSourceName": "Tenor-1"}},
            "unload_sound_source_on_track": {"ok": True},
        }
        client = DummyClient(mapping)
        result = sound_source.unload_sound_source(client, 0, dry_run=False)
        self.assertFalse(result["dry_run"])
        self.assertEqual(client.calls[-1][0], "unload_sound_source_on_track")

    def test_parser_accepts_sound_source_unload(self):
        parser = build_parser()
        args = parser.parse_args(["sound-source", "unload", "0", "--dry-run"])
        self.assertEqual(args.track_index, 0)
        self.assertTrue(args.dry_run)

    def test_ui_special_track_mapping(self):
        client = DummyClient({"set_special_track_visibility": {"ok": True}})
        result = ui.set_special_track_visibility(client, "tempo-and-timesig", True)
        self.assertEqual(result["track"], "tempo-and-timesig")
        self.assertEqual(
            client.calls[-1],
            ("set_special_track_visibility", {"track": "tempo_and_timesig", "visible": True}),
        )

    def test_global_args_normalization_keeps_json_working_after_subcommand(self):
        argv = normalize_global_args(["project", "info", "--json"])
        self.assertEqual(argv, ["--json", "project", "info"])

    def test_parser_accepts_track_rename_command(self):
        parser = build_parser()
        args = parser.parse_args(["track", "rename", "0", "--name", "Lead Vox"])
        self.assertEqual(args.track_index, 0)
        self.assertEqual(args.name, "Lead Vox")

    def test_delete_selected_track_requires_selection(self):
        client = DummyClient({"get_selected_track_list": {"selectedTracks": [], "selectedTrackCount": 0}})
        with self.assertRaises(InvalidContextError):
            track.delete_selected_track(client)

    def test_delete_selected_track_dry_run(self):
        mapping = {
            "get_selected_track_list": {
                "selectedTracks": [{"trackIndex": 0, "trackUuid": "{abc}"}],
                "selectedTrackCount": 1,
            },
            "get_content_track_meta_settings": {"trackType": "Sing", "trackName": "Lead"},
        }
        client = DummyClient(mapping)
        result = track.delete_selected_track(client, dry_run=True)
        self.assertTrue(result["dry_run"])
        self.assertEqual(result["would_delete"]["track_count"], 1)

    def test_delete_selected_track_executes(self):
        mapping = {
            "get_selected_track_list": {
                "selectedTracks": [{"trackIndex": 0, "trackUuid": "{abc}"}],
                "selectedTrackCount": 1,
            },
            "get_content_track_meta_settings": {"trackType": "Sing", "trackName": "Lead"},
            "delete_selected_track": {"ok": True},
        }
        client = DummyClient(mapping)
        result = track.delete_selected_track(client, dry_run=False)
        self.assertFalse(result["dry_run"])
        self.assertEqual(client.calls[-1][0], "delete_selected_track")

    def test_parser_accepts_track_delete_dry_run(self):
        parser = build_parser()
        args = parser.parse_args(["track", "delete", "--dry-run"])
        self.assertTrue(args.dry_run)

    def test_parser_accepts_project_set_tempo_command(self):
        parser = build_parser()
        args = parser.parse_args(["project", "set-tempo", "--points-json", '[{"pos":0,"value":120}]', "--replace-all"])
        self.assertTrue(args.replace_all)

    def test_parser_accepts_project_set_timesig_command(self):
        parser = build_parser()
        args = parser.parse_args(["project", "set-timesig", "--signatures-json", '[{"barPos":0,"numerator":4,"denominator":4}]', "--replace-all"])
        self.assertTrue(args.replace_all)

    def test_parser_accepts_clip_move_edges(self):
        parser = build_parser()
        args = parser.parse_args(["clip", "move-edges", "--uuid", "abc123", "--side", "left", "--mode", "diff", "--value", "480"])
        self.assertEqual(args.uuid, "abc123")
        self.assertEqual(args.side, "left")
        self.assertEqual(args.mode, "diff")
        self.assertEqual(args.value, 480)

    def test_parser_accepts_clip_move_edges_dry_run(self):
        parser = build_parser()
        args = parser.parse_args(["clip", "move-edges", "--uuid", "abc123", "--side", "right", "--mode", "abs", "--value", "1920", "--dry-run"])
        self.assertTrue(args.dry_run)

    def test_validate_song_skeleton_requires_core_keys(self):
        client = DummyClient(self._track_mapping())
        with self.assertRaises(ValidationError):
            workflow.validate_song_skeleton_spec({"tempo": []}, client)

    def test_validate_song_skeleton_rejects_missing_track(self):
        client = DummyClient(self._track_mapping())
        spec = {
            "tempo": [{"pos": 0, "value": 120}],
            "timesig": [{"barPos": 0, "numerator": 4, "denominator": 4}],
            "sections": [{"name": "Verse", "bars": 8}],
            "tracks": [{"role": "lead", "track_index": 9, "clip_type": "sing"}],
        }
        with self.assertRaises(ValidationError):
            workflow.validate_song_skeleton_spec(spec, client)

    def test_validate_song_skeleton_rejects_unknown_target_role(self):
        client = DummyClient(self._track_mapping())
        spec = {
            "tempo": [{"pos": 0, "value": 120}],
            "timesig": [{"barPos": 0, "numerator": 4, "denominator": 4}],
            "sections": [{"name": "Verse", "bars": 8, "target_roles": ["missing"]}],
            "tracks": [{"role": "lead", "track_index": 0, "clip_type": "sing"}],
        }
        with self.assertRaises(ValidationError):
            workflow.validate_song_skeleton_spec(spec, client)

    def test_song_skeleton_dry_run_builds_clip_plan(self):
        mapping = self._track_mapping()
        mapping["get_tempo_automation"] = {"points": [{"pos": 0, "value": 120, "bend": 0}], "pointCount": 1}
        mapping["get_timesignature_list"] = {"signatures": [{"barPos": 0, "numerator": 4, "denominator": 4}], "signatureCount": 1}
        mapping["set_tempo_automation"] = {"ok": True}
        mapping["set_timesignature_list"] = {"ok": True}
        mapping["measure_pos_to_tick"] = lambda args: {"tick": args["barPos"] * 1920 + args["tickOffset"]}
        client = DummyClient(mapping)
        spec = {
            "tempo": [{"pos": 0, "value": 120}],
            "timesig": [{"barPos": 0, "numerator": 4, "denominator": 4}],
            "sections": [
                {"name": "Intro", "bars": 4},
                {"name": "Verse 1", "bars": 8, "target_roles": ["lead"]},
            ],
            "tracks": [
                {"role": "lead", "track_index": 0, "clip_type": "sing", "prefix": "Lead"},
            ],
        }
        result = workflow.song_skeleton(client, spec, dry_run=True)
        self.assertTrue(result["dry_run"])
        self.assertEqual(result["summary"]["clip_count"], 2)
        self.assertEqual(result["clip_plan"][0]["name"], "Intro Lead")
        self.assertEqual(result["clip_plan"][1]["pos"], 7680)

    def test_song_skeleton_executes_sound_source_once_per_track(self):
        mapping = self._track_mapping()
        mapping["get_tempo_automation"] = {"points": [{"pos": 0, "value": 120, "bend": 0}], "pointCount": 1}
        mapping["get_timesignature_list"] = {"signatures": [{"barPos": 0, "numerator": 4, "denominator": 4}], "signatureCount": 1}
        mapping["set_tempo_automation"] = {"ok": True}
        mapping["set_timesignature_list"] = {"ok": True}
        mapping["measure_pos_to_tick"] = lambda args: {"tick": args["barPos"] * 1920 + args["tickOffset"]}
        mapping["get_content_track_meta_settings"] = {"trackType": "Sing"}
        mapping["load_new_sound_source_on_track"] = {"ok": True}
        mapping["get_content_track_clip_basic_info_list"] = {"clipCount": 0, "clips": []}
        mapping["add_new_clip"] = {"clipName": "ok"}
        client = DummyClient(mapping)
        spec = {
            "tempo": [{"pos": 0, "value": 120}],
            "timesig": [{"barPos": 0, "numerator": 4, "denominator": 4}],
            "sections": [{"name": "Verse", "bars": 8}],
            "tracks": [
                {
                    "role": "lead",
                    "track_index": 0,
                    "clip_type": "sing",
                    "prefix": "Lead",
                    "sound_source": {"kind": "singer", "id": 1, "group": "official"},
                }
            ],
        }
        result = workflow.song_skeleton(client, spec, dry_run=False)
        self.assertEqual(result["summary"]["sound_source_load_count"], 1)
        calls = [name for name, _ in client.calls]
        self.assertEqual(calls.count("load_new_sound_source_on_track"), 1)

    def test_parser_accepts_workflow_song_skeleton(self):
        parser = build_parser()
        args = parser.parse_args(["workflow", "song-skeleton", "--spec-json", '{"tempo":[],"timesig":[],"sections":[],"tracks":[]}', "--dry-run"])
        self.assertTrue(args.dry_run)


class EditorModuleTests(unittest.TestCase):
    def _editor_mapping(self):
        return {
            "get_is_editor_available": {
                "isAvailable": True,
                "isVisible": True,
                "editorType": "Sing",
                "trackIndex": 0,
                "clipIndex": 0,
                "clipName": "Verse 1",
                "defaultLanguage": "English",
            },
            "get_editor_current_clip_index": {
                "trackIndex": 0,
                "clipIndex": 0,
                "clipName": "Verse 1",
                "clipType": "Sing",
                "defaultLanguage": "English",
            },
            "get_content_in_editor": {"notes": []},
            "get_selection_in_editor": {"hasSelection": False},
        }

    def test_editor_availability_normalization(self):
        client = DummyClient(self._editor_mapping())
        result = editor.get_editor_availability(client)
        self.assertTrue(result["is_available"])
        self.assertTrue(result["is_visible"])
        self.assertEqual(result["editor_type"], "Sing")

    def test_editor_availability_returns_unavailable(self):
        client = DummyClient({"get_is_editor_available": {"isAvailable": False, "isVisible": False}})
        result = editor.get_editor_availability(client)
        self.assertFalse(result["is_available"])
        self.assertFalse(result["is_visible"])

    def test_editor_clip_normalization(self):
        client = DummyClient(self._editor_mapping())
        result = editor.get_editor_clip(client)
        self.assertEqual(result["track_index"], 0)
        self.assertEqual(result["clip_index"], 0)

    def test_editor_clip_requires_available(self):
        client = DummyClient({"get_is_editor_available": {"isAvailable": False, "isVisible": False}})
        with self.assertRaises(InvalidContextError):
            editor.get_editor_clip(client)

    def test_add_notes_requires_lyric_or_notes(self):
        client = DummyClient(self._editor_mapping())
        with self.assertRaises(ValidationError):
            editor.add_notes(client)

    def test_add_notes_with_sentence_mode(self):
        mapping = self._editor_mapping()
        mapping["add_notes_in_editor"] = {"ok": True}
        client = DummyClient(mapping)
        result = editor.add_notes(client, lyric_sentence="hello world", notes=[{"pos": 0, "dur": 480, "pitch": 60}])
        self.assertEqual(result["added_notes_count"], 1)
        self.assertEqual(result["lyric_sentence"], "hello world")
        self.assertEqual(client.calls[-1][0], "add_notes_in_editor")

    def test_add_notes_rejects_negative_offset(self):
        client = DummyClient(self._editor_mapping())
        with self.assertRaises(ValidationError):
            editor.add_notes(client, lyric="la", offset=-1)

    def test_add_notes_rejects_invalid_pitch(self):
        client = DummyClient(self._editor_mapping())
        with self.assertRaises(ValidationError):
            editor.add_notes(client, notes=[{"pos": 0, "dur": 480, "pitch": 200}])

    def test_add_notes_with_language(self):
        mapping = self._editor_mapping()
        mapping["add_notes_in_editor"] = {"ok": True}
        client = DummyClient(mapping)
        result = editor.add_notes(client, lyric_sentence="ni hao", notes=[{"pos": 0, "dur": 480, "pitch": 60}], language="Mandarin Chinese")
        self.assertEqual(result["language"], "Mandarin Chinese")

    def test_set_editor_selection_range_requires_valid_range(self):
        client = DummyClient(self._editor_mapping())
        with self.assertRaises(ValidationError):
            editor.set_editor_selection_range(client, 100, 50)

    def test_set_editor_selection_range_payload(self):
        mapping = self._editor_mapping()
        mapping["set_editor_selection_range"] = {"ok": True}
        client = DummyClient(mapping)
        result = editor.set_editor_selection_range(client, 0, 480, select_notes=True)
        self.assertEqual(result["range_begin"], 0)
        self.assertEqual(result["range_end"], 480)
        self.assertTrue(result["select_notes"])
        self.assertEqual(client.calls[-1][0], "set_editor_selection_range")

    def test_delete_editor_selection_requires_selection(self):
        client = DummyClient(self._editor_mapping())
        with self.assertRaises(InvalidContextError):
            editor.delete_editor_selection(client)

    def test_delete_editor_selection_dry_run(self):
        mapping = self._editor_mapping()
        mapping["get_selection_in_editor"] = {"hasSelection": True, "selectedNotes": [{"uuid": "a", "pos": 0}]}
        client = DummyClient(mapping)
        result = editor.delete_editor_selection(client, dry_run=True)
        self.assertTrue(result["dry_run"])
        self.assertEqual(result["would_delete"]["note_count"], 1)

    def test_delete_editor_selection_executes(self):
        mapping = self._editor_mapping()
        mapping["get_selection_in_editor"] = {"hasSelection": True, "selectedNotes": [{"uuid": "a", "pos": 0}]}
        mapping["delete_editor_selection"] = {"ok": True}
        client = DummyClient(mapping)
        result = editor.delete_editor_selection(client, dry_run=False)
        self.assertFalse(result["dry_run"])
        self.assertEqual(client.calls[-1][0], "delete_editor_selection")

    def test_modify_note_selection_requires_mode(self):
        client = DummyClient(self._editor_mapping())
        with self.assertRaises(ValidationError):
            editor.modify_note_selection(client, "invalid_mode")

    def test_modify_note_selection_replace_requires_notes(self):
        client = DummyClient(self._editor_mapping())
        with self.assertRaises(ValidationError):
            editor.modify_note_selection(client, "replace")

    def test_modify_note_selection_payload(self):
        mapping = self._editor_mapping()
        mapping["modify_note_selection_in_editor"] = {"ok": True}
        client = DummyClient(mapping)
        result = editor.modify_note_selection(
            client,
            "replace",
            notes_to_select=[{"uuid": "abc123"}],
        )
        self.assertEqual(result["mode"], "replace")
        self.assertEqual(client.calls[-1][1]["mode"], "replace")

    def test_parse_notes_rejects_invalid_json(self):
        with self.assertRaises(ValidationError):
            editor._parse_notes("not json")

    def test_parse_notes_rejects_non_array(self):
        with self.assertRaises(ValidationError):
            editor._parse_notes('{"pos": 0}')

    def test_parse_notes_rejects_missing_fields(self):
        with self.assertRaises(ValidationError):
            editor._parse_notes('[{"pos": 0}]')

    def test_parser_accepts_editor_add_notes(self):
        parser = build_parser()
        args = parser.parse_args(["editor", "add-notes", "--lyric-sentence", "hello", "--notes-json", '[{"pos":0,"dur":480,"pitch":60}]'])
        self.assertEqual(args.lyric_sentence, "hello")

    def test_parser_accepts_editor_delete_selection_dry_run(self):
        parser = build_parser()
        args = parser.parse_args(["editor", "delete-selection", "--dry-run"])
        self.assertTrue(args.dry_run)

    def test_parser_accepts_editor_selection_range(self):
        parser = build_parser()
        args = parser.parse_args(["editor", "selection-range", "--range-begin", "0", "--range-end", "480", "--select-notes"])
        self.assertEqual(args.range_begin, 0)
        self.assertEqual(args.range_end, 480)
        self.assertTrue(args.select_notes)


class ArrangementModuleTests(unittest.TestCase):
    def _selection_mapping(self):
        return {
            "get_current_arrangement_view_selection_range": {
                "horizontalSelection": {"begin": 0, "end": 1920},
                "verticalSelection": {"begin": 0, "end": 1},
            }
        }

    def test_get_arrangement_selection_normalization(self):
        client = DummyClient(self._selection_mapping())
        result = arrangement.get_arrangement_selection(client)
        self.assertTrue(result["has_selection"])
        self.assertEqual(result["horizontal"]["begin"], 0)
        self.assertEqual(result["horizontal"]["end"], 1920)
        self.assertEqual(result["vertical"]["begin"], 0)
        self.assertEqual(result["vertical"]["end"], 1)

    def test_get_arrangement_selection_no_selection(self):
        client = DummyClient({"get_current_arrangement_view_selection_range": {}})
        result = arrangement.get_arrangement_selection(client)
        self.assertFalse(result["has_selection"])

    def test_make_arrangement_selection_payload(self):
        mapping = self._selection_mapping()
        mapping["make_new_arrangement_view_selection_range"] = {"ok": True}
        client = DummyClient(mapping)
        result = arrangement.make_arrangement_selection(client, 0, 2, 0, 1920)
        self.assertEqual(result["horizontal"]["begin"], 0)
        self.assertEqual(result["vertical"]["end"], 2)
        self.assertEqual(client.calls[-1][0], "make_new_arrangement_view_selection_range")

    def test_make_arrangement_selection_rejects_invalid_track_range(self):
        client = DummyClient(self._selection_mapping())
        with self.assertRaises(ValidationError):
            arrangement.make_arrangement_selection(client, 5, 2, 0, 1920)

    def test_make_arrangement_selection_rejects_invalid_tick_range(self):
        client = DummyClient(self._selection_mapping())
        with self.assertRaises(ValidationError):
            arrangement.make_arrangement_selection(client, 0, 2, 1920, 0)

    def test_delete_arrangement_selection_requires_selection(self):
        client = DummyClient({"get_current_arrangement_view_selection_range": {}})
        with self.assertRaises(InvalidContextError):
            arrangement.delete_arrangement_selection(client)

    def test_delete_arrangement_selection_dry_run(self):
        client = DummyClient(self._selection_mapping())
        result = arrangement.delete_arrangement_selection(client, dry_run=True)
        self.assertTrue(result["dry_run"])
        self.assertEqual(result["would_delete"]["tick_range"]["begin"], 0)

    def test_delete_arrangement_selection_executes(self):
        mapping = self._selection_mapping()
        mapping["delete_arrangement_view_selection"] = {"ok": True}
        client = DummyClient(mapping)
        result = arrangement.delete_arrangement_selection(client, dry_run=False)
        self.assertFalse(result["dry_run"])
        self.assertEqual(client.calls[-1][0], "delete_arrangement_view_selection")

    def test_move_arrangement_selection_requires_selection(self):
        client = DummyClient({"get_current_arrangement_view_selection_range": {}})
        with self.assertRaises(InvalidContextError):
            arrangement.move_arrangement_selection(client, 3840)

    def test_move_arrangement_selection_dry_run(self):
        client = DummyClient(self._selection_mapping())
        result = arrangement.move_arrangement_selection(client, 3840, None, dry_run=True)
        self.assertTrue(result["dry_run"])
        self.assertEqual(result["would_move"]["to"]["tick"], 3840)

    def test_move_arrangement_selection_executes(self):
        mapping = self._selection_mapping()
        mapping["move_arrangement_selection"] = {"ok": True}
        client = DummyClient(mapping)
        result = arrangement.move_arrangement_selection(client, 3840, 1, dry_run=False)
        self.assertFalse(result["dry_run"])
        self.assertEqual(client.calls[-1][1]["targetTick"], 3840)
        self.assertEqual(client.calls[-1][1]["targetTrackIndex"], 1)

    def test_parser_accepts_arrangement_get_selection(self):
        parser = build_parser()
        args = parser.parse_args(["arrangement", "get-selection"])
        self.assertIsNotNone(args)

    def test_parser_accepts_arrangement_make_selection(self):
        parser = build_parser()
        args = parser.parse_args(["arrangement", "make-selection", "--track-begin", "0", "--track-end", "2", "--tick-begin", "0", "--tick-end", "1920"])
        self.assertEqual(args.track_begin, 0)
        self.assertEqual(args.tick_end, 1920)

    def test_parser_accepts_arrangement_delete_selection_dry_run(self):
        parser = build_parser()
        args = parser.parse_args(["arrangement", "delete-selection", "--dry-run"])
        self.assertTrue(args.dry_run)

    def test_parser_accepts_arrangement_move_selection(self):
        parser = build_parser()
        args = parser.parse_args(["arrangement", "move-selection", "--target-tick", "3840", "--target-track-index", "1"])
        self.assertEqual(args.target_tick, 3840)
        self.assertEqual(args.target_track_index, 1)


if __name__ == "__main__":
    unittest.main()
