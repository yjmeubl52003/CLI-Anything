"""Playback and navigation operations."""

from __future__ import annotations


def control_playback(client, action: str) -> dict:
    data = client.call_tool("control_playback", {"action": action})
    return {"action": action, "result": data}


def get_metronome(client) -> dict:
    data = client.call_tool("get_metronome_on")
    if isinstance(data, dict):
        return {"is_metronome_on": data.get("isMetronomeOn")}
    if isinstance(data, str):
        lowered = data.lower()
        if "enabled" in lowered:
            return {"is_metronome_on": True, "raw": data}
        if "disabled" in lowered:
            return {"is_metronome_on": False, "raw": data}
    return {"is_metronome_on": None, "raw": data}


def set_metronome(client, is_on: bool) -> dict:
    data = client.call_tool("set_metronome_on", {"isMetronomeOn": is_on})
    return {"is_metronome_on": is_on, "result": data}


def get_loop(client) -> dict:
    data = client.call_tool("get_loop_info")
    return {
        "is_valid": data.get("isValid"),
        "is_active": data.get("isActive"),
        "start": data.get("start"),
        "end": data.get("end"),
    }


def set_loop_active(client, is_active: bool) -> dict:
    data = client.call_tool("set_loop_active", {"isActive": is_active})
    return {"is_active": is_active, "result": data}


def set_loop_range(client, start: int, end: int) -> dict:
    data = client.call_tool("set_loop_range", {"start": start, "end": end})
    return {"start": start, "end": end, "result": data}


def get_marker(client, scope: str | None = None) -> dict:
    args = {}
    if scope:
        args["scope"] = scope
    data = client.call_tool("get_marker_line_position", args)
    return {
        "track_index": data.get("trackIndex"),
        "tick": data.get("tick"),
        "scope": data.get("scope"),
    }


def seek_marker(client, time_seconds: float) -> dict:
    data = client.call_tool("seek_marker_line_position", {"time": time_seconds})
    return {"time_seconds": time_seconds, "result": data}


def move_marker(
    client,
    tick: int,
    force_seek: bool = False,
    is_global_tick: bool = True,
    scope: str | None = None,
    set_to_line_selection: bool = True,
    track_index: int | None = None,
) -> dict:
    args = {
        "tick": tick,
        "forceSeek": force_seek,
        "is_global_tick": is_global_tick,
        "set_to_line_selection": set_to_line_selection,
    }
    if scope:
        args["scope"] = scope
    if track_index is not None:
        args["trackIndex"] = track_index
    data = client.call_tool("change_marker_line_position", args)
    return {
        "tick": tick,
        "force_seek": force_seek,
        "is_global_tick": is_global_tick,
        "scope": scope,
        "set_to_line_selection": set_to_line_selection,
        "track_index": track_index,
        "result": data,
    }
