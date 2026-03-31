"""Track-related ACE Studio operations."""

from __future__ import annotations


from cli_anything.acestudio.mcp_client import ValidationError


def _raw_track_list(client) -> list[dict]:
    data = client.call_tool("get_content_track_basic_info_list")
    tracks = data.get("tracks", [])
    if not isinstance(tracks, list):
        raise ValidationError("ACE Studio returned an invalid track list.")
    return tracks


def _get_track_or_raise(client, track_index: int) -> dict:
    tracks = _raw_track_list(client)
    for track in tracks:
        if track.get("trackIndex") == track_index:
            return track
    raise ValidationError(f"Track index {track_index} does not exist.")


def _extract_palette_colors(data) -> list[str]:
    if isinstance(data, dict):
        colors = data.get("colors")
        if isinstance(colors, list):
            return [str(color) for color in colors]
    if isinstance(data, list):
        return [str(color) for color in data]
    return []


def get_color_palette(client) -> dict:
    data = client.call_tool("get_color_palette")
    colors = _extract_palette_colors(data)
    return {
        "color_count": len(colors),
        "colors": colors,
    }


def list_tracks(client) -> dict:
    tracks = _raw_track_list(client)
    return {
        "track_count": len(tracks),
        "tracks": [
            {
                "index": track.get("trackIndex"),
                "type": track.get("trackType"),
                "name": track.get("trackName"),
                "clip_count": track.get("clipCount"),
                "sound_source_name": track.get("soundSourceName"),
            }
            for track in tracks
        ],
    }


def get_meta(client, track_index: int) -> dict:
    _get_track_or_raise(client, track_index)
    data = client.call_tool("get_content_track_meta_settings", {"trackIndex": track_index})
    return {"track_index": track_index, "meta": data}


def get_selected(client) -> dict:
    data = client.call_tool("get_selected_track_list")
    selected = data.get("selectedTracks", [])
    return {
        "selected_track_count": data.get("selectedTrackCount", len(selected)),
        "selected_tracks": [
            {
                "index": item.get("trackIndex"),
                "uuid": item.get("trackUuid"),
            }
            for item in selected
        ],
    }


def rename_track(client, track_index: int, new_name: str) -> dict:
    if not new_name.strip():
        raise ValidationError("Track name must not be empty.")
    track = _get_track_or_raise(client, track_index)
    if track.get("trackName") == new_name:
        raise ValidationError("New track name matches the current name.")
    result = client.call_tool("rename_content_track", {"trackIndex": track_index, "newName": new_name})
    return {
        "track_index": track_index,
        "previous_name": track.get("trackName"),
        "new_name": new_name,
        "result": result,
    }


def set_track_color(client, track_index: int, color: str) -> dict:
    track = _get_track_or_raise(client, track_index)
    palette = get_color_palette(client)
    if color not in palette["colors"]:
        raise ValidationError(f"Color {color} is not in the ACE Studio color palette.")
    result = client.call_tool("change_content_track_color", {"trackIndex": track_index, "color": color})
    return {
        "track_index": track_index,
        "track_name": track.get("trackName"),
        "color": color,
        "validated_against_palette": True,
        "result": result,
    }


def set_selected_tracks(client, track_indices: list[int]) -> dict:
    seen: set[int] = set()
    normalized: list[int] = []
    for track_index in track_indices:
        if track_index in seen:
            continue
        _get_track_or_raise(client, track_index)
        seen.add(track_index)
        normalized.append(track_index)
    result = client.call_tool(
        "set_selected_track_list",
        {"tracks": [{"trackIndex": track_index} for track_index in normalized]},
    )
    return {
        "selected_track_indices": normalized,
        "result": result,
    }


def clear_selected_tracks(client) -> dict:
    result = client.call_tool("set_selected_track_list", {"tracks": []})
    return {
        "selected_track_indices": [],
        "result": result,
    }


def set_track_mute(client, track_index: int, mute: bool) -> dict:
    track = _get_track_or_raise(client, track_index)
    result = client.call_tool("set_content_track_mute_solo", {"trackIndex": track_index, "mute": mute})
    return {
        "track_index": track_index,
        "track_name": track.get("trackName"),
        "mute": mute,
        "result": result,
    }


def set_track_solo(client, track_index: int, solo: bool) -> dict:
    track = _get_track_or_raise(client, track_index)
    result = client.call_tool("set_content_track_mute_solo", {"trackIndex": track_index, "solo": solo})
    return {
        "track_index": track_index,
        "track_name": track.get("trackName"),
        "solo": solo,
        "result": result,
    }


def set_track_pan(client, track_index: int, pan: float) -> dict:
    if pan < -1 or pan > 1:
        raise ValidationError("Pan must be between -1 and 1.")
    track = _get_track_or_raise(client, track_index)
    result = client.call_tool("set_content_track_pan_gain", {"trackIndex": track_index, "pan": pan})
    return {
        "track_index": track_index,
        "track_name": track.get("trackName"),
        "pan": pan,
        "result": result,
    }


def set_track_gain(client, track_index: int, gain: float) -> dict:
    if gain < 0:
        raise ValidationError("Gain must be greater than or equal to 0.")
    track = _get_track_or_raise(client, track_index)
    result = client.call_tool("set_content_track_pan_gain", {"trackIndex": track_index, "gain": gain})
    return {
        "track_index": track_index,
        "track_name": track.get("trackName"),
        "gain": gain,
        "result": result,
    }


def set_track_record_settings(
    client,
    track_index: int,
    *,
    listen=None,
    input_channel=None,
    midi_source=None,
    midi_device=None,
    midi_channel=None,
    record_mode=None,
) -> dict:
    updates = {}
    if midi_source != "custom" and (midi_device is not None or midi_channel is not None):
        raise ValidationError("--midi-device and --midi-channel require --midi-source custom.")
    if listen is not None:
        updates["listen"] = listen
    if input_channel is not None:
        if input_channel < -1:
            raise ValidationError("Input channel must be greater than or equal to -1.")
        updates["inputChannelIndex"] = input_channel
    if midi_source is not None:
        if midi_source not in {"none", "all", "computerKeyboard", "custom"}:
            raise ValidationError("Invalid MIDI source.")
        updates["midiInputSourceType"] = midi_source
    if midi_device is not None:
        updates["midiInputDeviceName"] = midi_device
    if midi_channel is not None:
        if midi_channel < -1 or midi_channel > 15:
            raise ValidationError("MIDI channel must be between -1 and 15.")
        updates["midiInputChannel"] = midi_channel
    if record_mode is not None:
        if record_mode not in {"monophonic", "polyphonic"}:
            raise ValidationError("Record mode must be monophonic or polyphonic.")
        updates["recordMode"] = record_mode
    if not updates:
        raise ValidationError("At least one record setting must be provided.")
    track = _get_track_or_raise(client, track_index)
    result = client.call_tool("set_content_track_record_setting", {"trackIndex": track_index, **updates})
    return {
        "track_index": track_index,
        "track_name": track.get("trackName"),
        "updates": updates,
        "result": result,
    }
