#!/usr/bin/env python3
"""ACE Studio CLI harness built on the official MCP server."""

from __future__ import annotations

import argparse
import json
import shlex
import sys
from typing import Any, Callable

from cli_anything.acestudio import __version__
from cli_anything.acestudio.core import clip as clip_core
from cli_anything.acestudio.core import convert as convert_core
from cli_anything.acestudio.core import project as project_core
from cli_anything.acestudio.core import sound_source as sound_source_core
from cli_anything.acestudio.core import track as track_core
from cli_anything.acestudio.core import transport as transport_core
from cli_anything.acestudio.core import ui as ui_core
from cli_anything.acestudio.mcp_client import (
    ACEStudioMCPClient,
    MCPClientError,
    ServerUnavailableError,
    SessionInitializationError,
    ToolCallError,
    ValidationError,
)
from cli_anything.acestudio.utils.repl_skin import ReplSkin


def make_client(args) -> ACEStudioMCPClient:
    return ACEStudioMCPClient(url=args.url, timeout=args.timeout, client_version=__version__)


def emit(data: Any, as_json: bool) -> None:
    if as_json:
        print(json.dumps(data, indent=2, ensure_ascii=True, default=str))
        return
    if isinstance(data, dict):
        _print_dict(data)
    elif isinstance(data, list):
        _print_list(data)
    else:
        print(str(data))


def _print_dict(data: dict[str, Any], indent: int = 0) -> None:
    prefix = "  " * indent
    for key, value in data.items():
        if isinstance(value, dict):
            print(f"{prefix}{key}:")
            _print_dict(value, indent + 1)
        elif isinstance(value, list):
            print(f"{prefix}{key}:")
            _print_list(value, indent + 1)
        else:
            print(f"{prefix}{key}: {value}")


def _print_list(items: list[Any], indent: int = 0) -> None:
    prefix = "  " * indent
    for idx, item in enumerate(items):
        if isinstance(item, dict):
            print(f"{prefix}[{idx}]")
            _print_dict(item, indent + 1)
        else:
            print(f"{prefix}- {item}")


def cli_error_to_exit_code(exc: Exception) -> int:
    if isinstance(exc, ServerUnavailableError):
        return 2
    if isinstance(exc, SessionInitializationError):
        return 3
    if isinstance(exc, ValidationError):
        return 4
    if isinstance(exc, ToolCallError):
        return 6
    return 1


def run_command(args) -> int:
    try:
        result = args.func(args)
        emit(result, args.as_json)
        return 0
    except MCPClientError as exc:
        payload = {"error": str(exc), "type": exc.__class__.__name__}
        if getattr(args, "as_json", False):
            print(json.dumps(payload, ensure_ascii=True))
        else:
            print(f"Error: {exc}", file=sys.stderr)
        return cli_error_to_exit_code(exc)
    except ValueError as exc:
        payload = {"error": str(exc), "type": exc.__class__.__name__}
        if getattr(args, "as_json", False):
            print(json.dumps(payload, ensure_ascii=True))
        else:
            print(f"Error: {exc}", file=sys.stderr)
        return 4


def cmd_server_ping(args):
    client = make_client(args)
    init = client.initialize()
    return {
        "reachable": True,
        "session_id": client.session_id,
        "protocol_version": init.get("protocolVersion"),
        "server_info": init.get("serverInfo", {}),
    }


def cmd_server_capabilities(args):
    client = make_client(args)
    init = client.initialize()
    tools = client.list_tools()
    return {
        "protocol_version": init.get("protocolVersion"),
        "capabilities": init.get("capabilities", {}),
        "tool_count": len(tools),
        "tool_names": [tool.get("name") for tool in tools],
    }


def cmd_project_info(args):
    return project_core.get_info(make_client(args))


def cmd_project_playback_status(args):
    return project_core.get_playback_status(make_client(args))


def cmd_project_synthesis_status(args):
    return project_core.get_synthesis_status(make_client(args))


def cmd_project_tempo_list(args):
    return project_core.get_tempo_list(make_client(args))


def cmd_project_timesig_list(args):
    return project_core.get_timesig_list(make_client(args))


def _load_json_array(raw: str, label: str) -> list[dict[str, Any]]:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValidationError(f"{label} must be valid JSON.") from exc
    if not isinstance(parsed, list):
        raise ValidationError(f"{label} must be a JSON array.")
    return parsed


def cmd_project_set_tempo(args):
    points = _load_json_array(args.points_json, "--points-json")
    return project_core.set_tempo_automation(make_client(args), points, args.replace_all)


def cmd_project_set_timesig(args):
    signatures = _load_json_array(args.signatures_json, "--signatures-json")
    return project_core.set_timesignature_list(make_client(args), signatures, args.replace_all)


def cmd_track_list(args):
    return track_core.list_tracks(make_client(args))


def cmd_track_meta(args):
    return track_core.get_meta(make_client(args), args.track_index)


def cmd_track_selected(args):
    return track_core.get_selected(make_client(args))


def cmd_track_rename(args):
    return track_core.rename_track(make_client(args), args.track_index, args.name)


def cmd_track_set_color(args):
    return track_core.set_track_color(make_client(args), args.track_index, args.color)


def cmd_track_select(args):
    return track_core.set_selected_tracks(make_client(args), args.track_indices)


def cmd_track_clear_selection(args):
    return track_core.clear_selected_tracks(make_client(args))


def cmd_track_set_mute(args):
    return track_core.set_track_mute(make_client(args), args.track_index, args.state == "on")


def cmd_track_set_solo(args):
    return track_core.set_track_solo(make_client(args), args.track_index, args.state == "on")


def cmd_track_set_pan(args):
    return track_core.set_track_pan(make_client(args), args.track_index, args.pan)


def cmd_track_set_gain(args):
    return track_core.set_track_gain(make_client(args), args.track_index, args.gain)


def cmd_track_set_record(args):
    listen = None if args.listen is None else args.listen == "on"
    return track_core.set_track_record_settings(
        make_client(args),
        args.track_index,
        listen=listen,
        input_channel=args.input_channel,
        midi_source=args.midi_source,
        midi_device=args.midi_device,
        midi_channel=args.midi_channel,
        record_mode=args.record_mode,
    )


def cmd_clip_list(args):
    return clip_core.list_clips(make_client(args), args.track_index)


def cmd_clip_meta(args):
    return clip_core.get_meta(make_client(args), args.track_index, args.clip_index, args.time_unit)


def cmd_clip_notes(args):
    return clip_core.get_notes(
        make_client(args),
        args.track_index,
        args.clip_index,
        args.range_begin,
        args.range_end,
        args.range_scope,
    )


def cmd_clip_lyrics(args):
    return clip_core.get_lyrics(
        make_client(args),
        args.track_index,
        args.clip_index,
        args.range_begin,
        args.range_end,
        args.range_scope,
    )


def cmd_clip_audio_info(args):
    return clip_core.get_audio_info(make_client(args), args.track_index, args.clip_index)


def cmd_clip_add(args):
    return clip_core.add_clip(make_client(args), args.track_index, args.pos, args.dur, args.clip_type, args.name)


def cmd_sound_source_list(args):
    return sound_source_core.list_sound_sources(
        make_client(args),
        args.source_type,
        args.category,
        args.keyword,
        args.language,
        args.tags,
    )


def cmd_sound_source_tags(args):
    return sound_source_core.list_tags(make_client(args), args.source_type)


def cmd_sound_source_community_list(args):
    return sound_source_core.list_community_voices(
        make_client(args),
        args.page,
        args.my_collection,
        args.keyword,
        args.language,
        args.tags,
    )


def cmd_sound_source_collect_community(args):
    return sound_source_core.collect_community_voice(make_client(args), args.id)


def cmd_sound_source_load(args):
    return sound_source_core.load_sound_source(
        make_client(args),
        args.track_index,
        args.kind,
        args.id,
        args.group,
        args.router_id,
    )


def cmd_convert_tick_to_time(args):
    return convert_core.tick_to_time(make_client(args), args.tick)


def cmd_convert_time_to_tick(args):
    return convert_core.time_to_tick(make_client(args), args.time_seconds)


def cmd_convert_tick_to_measure(args):
    return convert_core.tick_to_measure(make_client(args), args.tick, args.consider_beat_mode)


def cmd_convert_measure_to_tick(args):
    if args.consider_beat_mode and args.beat_pos is None:
        raise ValidationError("--beat-pos is required when --consider-beat-mode is set.")
    return convert_core.measure_to_tick(
        make_client(args),
        args.bar_pos,
        args.tick_offset,
        args.consider_beat_mode,
        args.beat_pos,
    )


def cmd_transport_play(args):
    return transport_core.control_playback(make_client(args), "start")


def cmd_transport_stop(args):
    return transport_core.control_playback(make_client(args), "stop")


def cmd_transport_toggle(args):
    return transport_core.control_playback(make_client(args), "toggle")


def cmd_metronome_get(args):
    return transport_core.get_metronome(make_client(args))


def cmd_metronome_set(args):
    return transport_core.set_metronome(make_client(args), args.state == "on")


def cmd_loop_get(args):
    return transport_core.get_loop(make_client(args))


def cmd_loop_set_active(args):
    return transport_core.set_loop_active(make_client(args), args.state == "on")


def cmd_loop_set_range(args):
    return transport_core.set_loop_range(make_client(args), args.start, args.end)


def cmd_marker_get(args):
    return transport_core.get_marker(make_client(args), args.scope)


def cmd_marker_seek(args):
    return transport_core.seek_marker(make_client(args), args.seconds)


def cmd_marker_move(args):
    return transport_core.move_marker(
        make_client(args),
        tick=args.tick,
        force_seek=args.force_seek,
        is_global_tick=args.global_tick,
        scope=args.scope,
        set_to_line_selection=args.set_to_line_selection,
        track_index=args.track_index,
    )


def cmd_ui_mixer(args):
    return ui_core.set_mixer_visibility(make_client(args), args.state == "show")


def cmd_ui_special_track(args):
    return ui_core.set_special_track_visibility(make_client(args), args.track_name, args.state == "show")


def add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--url", default="http://localhost:21572/mcp", help="ACE Studio MCP URL")
    parser.add_argument("--timeout", default=10.0, type=float, help="Request timeout in seconds")
    parser.add_argument("--json", dest="as_json", action="store_true", help="Output as JSON")


def attach_command(subparsers, name: str, help_text: str, func: Callable, configure: Callable | None = None):
    parser = subparsers.add_parser(name, help=help_text)
    if configure:
        configure(parser)
    parser.set_defaults(func=func)
    return parser


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cli-anything-acestudio", description="ACE Studio CLI via the official local MCP server")
    add_common_args(parser)
    groups = parser.add_subparsers(dest="group")

    server = groups.add_parser("server", help="Server health and capability commands")
    server_sub = server.add_subparsers(dest="command")
    attach_command(server_sub, "ping", "Check ACE Studio MCP reachability", cmd_server_ping)
    attach_command(server_sub, "capabilities", "List MCP capabilities and tool names", cmd_server_capabilities)

    project = groups.add_parser("project", help="Project inspection commands")
    project_sub = project.add_subparsers(dest="command")
    attach_command(project_sub, "info", "Show project info", cmd_project_info)
    attach_command(project_sub, "playback-status", "Show playback status", cmd_project_playback_status)
    attach_command(project_sub, "synthesis-status", "Show synthesis status", cmd_project_synthesis_status)
    attach_command(project_sub, "tempo-list", "List tempo automation points", cmd_project_tempo_list)
    attach_command(project_sub, "timesig-list", "List time signatures", cmd_project_timesig_list)

    def cfg_project_set_tempo(p):
        p.add_argument("--points-json", required=True)
        p.add_argument("--replace-all", action="store_true", default=False)

    attach_command(project_sub, "set-tempo", "Replace the full tempo automation map", cmd_project_set_tempo, cfg_project_set_tempo)

    def cfg_project_set_timesig(p):
        p.add_argument("--signatures-json", required=True)
        p.add_argument("--replace-all", action="store_true", default=False)

    attach_command(project_sub, "set-timesig", "Replace the full time signature map", cmd_project_set_timesig, cfg_project_set_timesig)

    track = groups.add_parser("track", help="Track inspection commands")
    track_sub = track.add_subparsers(dest="command")
    attach_command(track_sub, "list", "List tracks", cmd_track_list)
    attach_command(track_sub, "meta", "Show track metadata", cmd_track_meta, lambda p: p.add_argument("track_index", type=int))
    attach_command(track_sub, "selected", "Show selected tracks", cmd_track_selected)
    attach_command(
        track_sub,
        "rename",
        "Rename a track",
        cmd_track_rename,
        lambda p: (p.add_argument("track_index", type=int), p.add_argument("--name", required=True)),
    )
    attach_command(
        track_sub,
        "set-color",
        "Set track color",
        cmd_track_set_color,
        lambda p: (p.add_argument("track_index", type=int), p.add_argument("--color", required=True)),
    )

    def cfg_track_select(p):
        p.add_argument("--track-index", dest="track_indices", type=int, action="append", required=True)

    attach_command(track_sub, "select", "Select track headers", cmd_track_select, cfg_track_select)
    attach_command(track_sub, "clear-selection", "Clear selected tracks", cmd_track_clear_selection)

    def cfg_track_state(p):
        p.add_argument("track_index", type=int)
        p.add_argument("state", choices=["on", "off"])

    attach_command(track_sub, "set-mute", "Set track mute state", cmd_track_set_mute, cfg_track_state)
    attach_command(track_sub, "set-solo", "Set track solo state", cmd_track_set_solo, cfg_track_state)
    attach_command(
        track_sub,
        "set-pan",
        "Set track pan",
        cmd_track_set_pan,
        lambda p: (p.add_argument("track_index", type=int), p.add_argument("--pan", required=True, type=float)),
    )
    attach_command(
        track_sub,
        "set-gain",
        "Set track gain",
        cmd_track_set_gain,
        lambda p: (p.add_argument("track_index", type=int), p.add_argument("--gain", required=True, type=float)),
    )

    def cfg_track_record(p):
        p.add_argument("track_index", type=int)
        p.add_argument("--listen", choices=["on", "off"], default=None)
        p.add_argument("--input-channel", type=int, default=None)
        p.add_argument("--midi-source", choices=["none", "all", "computerKeyboard", "custom"], default=None)
        p.add_argument("--midi-device", default=None)
        p.add_argument("--midi-channel", type=int, default=None)
        p.add_argument("--record-mode", choices=["monophonic", "polyphonic"], default=None)

    attach_command(track_sub, "set-record", "Set track record settings", cmd_track_set_record, cfg_track_record)

    clip = groups.add_parser("clip", help="Clip inspection commands")
    clip_sub = clip.add_subparsers(dest="command")
    attach_command(clip_sub, "list", "List clips on a track", cmd_clip_list, lambda p: p.add_argument("track_index", type=int))

    def cfg_clip_meta(p):
        p.add_argument("track_index", type=int)
        p.add_argument("clip_index", type=int)
        p.add_argument("--time-unit", choices=["default", "tick", "second"], default="default")

    attach_command(clip_sub, "meta", "Show clip metadata", cmd_clip_meta, cfg_clip_meta)

    def cfg_clip_range(p):
        p.add_argument("track_index", type=int)
        p.add_argument("clip_index", type=int)
        p.add_argument("--range-begin", type=float, default=None)
        p.add_argument("--range-end", type=float, default=None)
        p.add_argument("--range-scope", choices=["project", "canvas"], default="project")

    attach_command(clip_sub, "notes", "Show note clip content", cmd_clip_notes, cfg_clip_range)
    attach_command(clip_sub, "lyrics", "Show lyric sentences", cmd_clip_lyrics, cfg_clip_range)

    def cfg_clip_audio(p):
        p.add_argument("track_index", type=int)
        p.add_argument("clip_index", type=int)

    attach_command(clip_sub, "audio-info", "Show audio clip info", cmd_clip_audio_info, cfg_clip_audio)

    def cfg_clip_add(p):
        p.add_argument("track_index", type=int)
        p.add_argument("--pos", required=True, type=int)
        p.add_argument("--dur", required=True, type=int)
        p.add_argument("--type", dest="clip_type", required=True, choices=["sing", "instrument", "genericmidi"])
        p.add_argument("--name", default=None)

    attach_command(clip_sub, "add", "Add a new clip", cmd_clip_add, cfg_clip_add)

    sound = groups.add_parser("sound-source", help="Sound source browsing commands")
    sound_sub = sound.add_subparsers(dest="command")

    def cfg_sound_list(p):
        p.add_argument("--type", dest="source_type", required=True, choices=["voice", "choir", "instrument", "ensemble"])
        p.add_argument("--category", default=None)
        p.add_argument("--keyword", default=None)
        p.add_argument("--language", default=None)
        p.add_argument("--tag", dest="tags", action="append", default=[])

    attach_command(sound_sub, "list", "List available sound sources", cmd_sound_source_list, cfg_sound_list)

    def cfg_sound_tags(p):
        p.add_argument("--type", dest="source_type", required=True, choices=["voice", "instrument"])

    attach_command(sound_sub, "tags", "List suggested tags", cmd_sound_source_tags, cfg_sound_tags)

    def cfg_sound_community(p):
        p.add_argument("--page", default=0, type=int)
        p.add_argument("--my-collection", action="store_true", default=False)
        p.add_argument("--keyword", default=None)
        p.add_argument("--language", default=None)
        p.add_argument("--tag", dest="tags", action="append", default=[])

    attach_command(sound_sub, "community-list", "List community voices", cmd_sound_source_community_list, cfg_sound_community)
    attach_command(
        sound_sub,
        "collect-community",
        "Collect a community voice",
        cmd_sound_source_collect_community,
        lambda p: p.add_argument("--id", required=True, type=int),
    )

    def cfg_sound_load(p):
        p.add_argument("track_index", type=int)
        p.add_argument("--kind", required=True, choices=["singer", "choir", "instrument", "ensemble"])
        p.add_argument("--id", required=True, type=int)
        p.add_argument("--group", default=None)
        p.add_argument("--router-id", type=int, default=None)

    attach_command(sound_sub, "load", "Load a sound source onto a track", cmd_sound_source_load, cfg_sound_load)

    convert = groups.add_parser("convert", help="Tempo and position conversion commands")
    convert_sub = convert.add_subparsers(dest="command")
    attach_command(convert_sub, "tick-to-time", "Convert tick to seconds", cmd_convert_tick_to_time, lambda p: p.add_argument("tick", type=float))
    attach_command(convert_sub, "time-to-tick", "Convert seconds to tick", cmd_convert_time_to_tick, lambda p: p.add_argument("time_seconds", type=float))

    def cfg_tick_to_measure(p):
        p.add_argument("tick", type=float)
        p.add_argument("--consider-beat-mode", action="store_true", default=False)

    attach_command(convert_sub, "tick-to-measure", "Convert tick to measure position", cmd_convert_tick_to_measure, cfg_tick_to_measure)

    def cfg_measure_to_tick(p):
        p.add_argument("bar_pos", type=int)
        p.add_argument("tick_offset", type=int)
        p.add_argument("--consider-beat-mode", action="store_true", default=False)
        p.add_argument("--beat-pos", type=int, default=None)

    attach_command(convert_sub, "measure-to-tick", "Convert measure position to tick", cmd_convert_measure_to_tick, cfg_measure_to_tick)

    transport = groups.add_parser("transport", help="Playback transport commands")
    transport_sub = transport.add_subparsers(dest="command")
    attach_command(transport_sub, "play", "Start playback", cmd_transport_play)
    attach_command(transport_sub, "stop", "Stop playback", cmd_transport_stop)
    attach_command(transport_sub, "toggle", "Toggle playback", cmd_transport_toggle)

    metronome = groups.add_parser("metronome", help="Metronome commands")
    metronome_sub = metronome.add_subparsers(dest="command")
    attach_command(metronome_sub, "get", "Show metronome state", cmd_metronome_get)

    def cfg_metronome_set(p):
        p.add_argument("state", choices=["on", "off"])

    attach_command(metronome_sub, "set", "Set metronome state", cmd_metronome_set, cfg_metronome_set)

    loop = groups.add_parser("loop", help="Loop commands")
    loop_sub = loop.add_subparsers(dest="command")
    attach_command(loop_sub, "get", "Show loop state", cmd_loop_get)
    attach_command(loop_sub, "set-active", "Enable or disable loop", cmd_loop_set_active, cfg_metronome_set)

    def cfg_loop_range(p):
        p.add_argument("--start", required=True, type=int)
        p.add_argument("--end", required=True, type=int)

    attach_command(loop_sub, "set-range", "Set loop range", cmd_loop_set_range, cfg_loop_range)

    marker = groups.add_parser("marker", help="Marker commands")
    marker_sub = marker.add_subparsers(dest="command")

    def cfg_marker_get(p):
        p.add_argument("--scope", choices=["global", "arrangement", "editor"], default=None)

    attach_command(marker_sub, "get", "Show marker position", cmd_marker_get, cfg_marker_get)

    def cfg_marker_seek(p):
        p.add_argument("--seconds", required=True, type=float)

    attach_command(marker_sub, "seek", "Seek marker to seconds", cmd_marker_seek, cfg_marker_seek)

    def cfg_marker_move(p):
        p.add_argument("--tick", required=True, type=int)
        p.add_argument("--force-seek", action="store_true", default=False)
        p.add_argument("--local-tick", dest="global_tick", action="store_false", default=True)
        p.add_argument("--scope", choices=["global", "arrangement", "editor"], default=None)
        p.add_argument("--no-set-to-line-selection", dest="set_to_line_selection", action="store_false", default=True)
        p.add_argument("--track-index", type=int, default=None)

    attach_command(marker_sub, "move", "Move marker", cmd_marker_move, cfg_marker_move)

    ui = groups.add_parser("ui", help="UI visibility commands")
    ui_sub = ui.add_subparsers(dest="command")

    def cfg_ui_mixer(p):
        p.add_argument("state", choices=["show", "hide"])

    attach_command(ui_sub, "mixer", "Show or hide the mixer", cmd_ui_mixer, cfg_ui_mixer)

    def cfg_ui_special_track(p):
        p.add_argument("track_name", choices=["chord", "tempo-and-timesig"])
        p.add_argument("state", choices=["show", "hide"])

    attach_command(ui_sub, "special-track", "Show or hide a special track", cmd_ui_special_track, cfg_ui_special_track)

    return parser


def normalize_global_args(argv: list[str]) -> list[str]:
    """Allow global flags like --json/--url/--timeout anywhere in argv."""
    globals_with_values = {"--url", "--timeout"}
    globals_without_values = {"--json"}
    global_args: list[str] = []
    remainder: list[str] = []
    i = 0
    while i < len(argv):
        token = argv[i]
        if token in globals_without_values:
            global_args.append(token)
            i += 1
            continue
        if token in globals_with_values:
            if i + 1 >= len(argv):
                remainder.append(token)
                i += 1
                continue
            global_args.extend([token, argv[i + 1]])
            i += 2
            continue
        remainder.append(token)
        i += 1
    return global_args + remainder


def repl_loop(base_args) -> int:
    skin = ReplSkin("acestudio", version=__version__)
    skin.print_banner()
    skin.info(f"MCP endpoint: {base_args.url}")
    pt_session = skin.create_prompt_session()
    parser = build_parser()

    while True:
        try:
            line = skin.get_input(pt_session, project_name="ACE Studio")
        except (EOFError, KeyboardInterrupt):
            break
        line = line.strip()
        if not line:
            continue
        if line in ("quit", "exit"):
            break
        if line == "help":
            skin.help(
                {
                    "server ping/capabilities": "MCP health and discovery",
                    "project info/playback-status/synthesis-status": "Project inspection",
                    "project set-tempo/set-timesig": "Tempo and time signature replacement",
                    "track list/meta/selected/rename/set-color/select/...": "Track inspection and writes",
                    "clip list/meta/notes/lyrics/audio-info/add": "Clip inspection and creation",
                    "sound-source list/tags/community-list/load/collect-community": "Sound source browsing and loading",
                    "convert tick-to-time/time-to-tick/tick-to-measure/measure-to-tick": "Time conversion",
                    "transport play/stop/toggle": "Playback control",
                    "metronome get/set, loop get/set-active/set-range, marker get/seek/move": "Navigation controls",
                    "ui mixer/special-track": "ACE Studio UI visibility",
                }
            )
            continue

        argv = ["--url", base_args.url, "--timeout", str(base_args.timeout)]
        if base_args.as_json:
            argv.append("--json")
        argv.extend(shlex.split(line))
        try:
            args = parser.parse_args(argv)
            if not hasattr(args, "func"):
                parser.print_help()
                continue
            code = run_command(args)
            if code != 0:
                skin.error(f"Command failed with exit code {code}")
        except SystemExit:
            pass
        except Exception as exc:  # pragma: no cover - REPL fallback path
            skin.error(f"Unexpected error: {exc}")

    skin.print_goodbye()
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(argv or sys.argv[1:])
    argv = normalize_global_args(argv)
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        return repl_loop(args)
    return run_command(args)


if __name__ == "__main__":
    raise SystemExit(main())
