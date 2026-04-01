"""Unit tests for ACE Studio CLI core modules and MCP client."""

from __future__ import annotations

import unittest

from cli_anything.acestudio.acestudio_cli import build_parser, normalize_global_args
from cli_anything.acestudio.core import clip, convert, project, sound_source, track, transport, ui, workflow
from cli_anything.acestudio.mcp_client import ValidationError
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

    def test_parser_accepts_project_set_tempo_command(self):
        parser = build_parser()
        args = parser.parse_args(["project", "set-tempo", "--points-json", '[{"pos":0,"value":120}]', "--replace-all"])
        self.assertTrue(args.replace_all)

    def test_parser_accepts_project_set_timesig_command(self):
        parser = build_parser()
        args = parser.parse_args(["project", "set-timesig", "--signatures-json", '[{"barPos":0,"numerator":4,"denominator":4}]', "--replace-all"])
        self.assertTrue(args.replace_all)

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


if __name__ == "__main__":
    unittest.main()
