"""Clip-related ACE Studio operations."""

from __future__ import annotations


from cli_anything.acestudio.mcp_client import ValidationError
from cli_anything.acestudio.core.track import _get_track_or_raise


def _clip_overlap(begin_a, end_a, begin_b, end_b) -> bool:
    return max(begin_a, begin_b) < min(end_a, end_b)


def list_clips(client, track_index: int) -> dict:
    _get_track_or_raise(client, track_index)
    data = client.call_tool("get_content_track_clip_basic_info_list", {"trackIndex": track_index})
    clips = data.get("clips", [])
    return {
        "track_index": track_index,
        "clip_count": data.get("clipCount", len(clips)),
        "clips": [
            {
                "index": index,
                "type": clip.get("clipType"),
                "name": clip.get("clipName"),
                "color": clip.get("clipColor"),
                "begin": clip.get("clipBegin"),
                "end": clip.get("clipEnd"),
                "note_count": clip.get("noteCount"),
            }
            for index, clip in enumerate(clips)
        ],
    }


def get_meta(client, track_index: int, clip_index: int, preferred_time_unit: str = "default") -> dict:
    _get_track_or_raise(client, track_index)
    data = client.call_tool(
        "get_clip_meta_info",
        {
            "trackIndex": track_index,
            "clipIndex": clip_index,
            "preferredTimeUnit": preferred_time_unit,
        },
    )
    return {
        "track_index": track_index,
        "clip_index": clip_index,
        "meta": data,
    }


def get_notes(client, track_index: int, clip_index: int, range_begin=None, range_end=None, range_scope: str = "project") -> dict:
    _get_track_or_raise(client, track_index)
    args = {
        "trackIndex": track_index,
        "clipIndex": clip_index,
        "rangeScope": range_scope,
    }
    if range_begin is not None:
        args["rangeBegin"] = range_begin
    if range_end is not None:
        args["rangeEnd"] = range_end
    data = client.call_tool("get_note_clip_content", args)
    return {
        "track_index": track_index,
        "clip_index": clip_index,
        "range_scope": range_scope,
        "content": data,
    }


def get_lyrics(client, track_index: int, clip_index: int, range_begin=None, range_end=None, range_scope: str = "project") -> dict:
    _get_track_or_raise(client, track_index)
    args = {
        "trackIndex": track_index,
        "clipIndex": clip_index,
        "rangeScope": range_scope,
    }
    if range_begin is not None:
        args["rangeBegin"] = range_begin
    if range_end is not None:
        args["rangeEnd"] = range_end
    data = client.call_tool("get_note_clip_lyrics", args)
    return {
        "track_index": track_index,
        "clip_index": clip_index,
        "sentence_count": data.get("sentenceCount"),
        "lyrics": data.get("sentences", []),
        "filtered_range": data.get("filteredRange"),
    }


def get_audio_info(client, track_index: int, clip_index: int) -> dict:
    _get_track_or_raise(client, track_index)
    data = client.call_tool("get_audio_clip_content_info", {"trackIndex": track_index, "clipIndex": clip_index})
    return {
        "track_index": track_index,
        "clip_index": clip_index,
        "audio_file_name": data.get("audioFileName"),
        "loading_state": data.get("loadingState"),
    }


def add_clip(client, track_index: int, pos: int, dur: int, clip_type: str, name: str | None = None) -> dict:
    track = _get_track_or_raise(client, track_index)
    if pos < 0:
        raise ValidationError("Clip position must be greater than or equal to 0.")
    if dur <= 0:
        raise ValidationError("Clip duration must be greater than 0.")
    if clip_type not in {"sing", "instrument", "genericmidi"}:
        raise ValidationError("Clip type must be sing, instrument, or genericmidi.")

    existing = list_clips(client, track_index)
    new_end = pos + dur
    overlapping = []
    for clip in existing["clips"]:
        clip_begin = clip.get("begin")
        clip_end = clip.get("end")
        if clip_begin is None or clip_end is None:
            continue
        if _clip_overlap(pos, new_end, clip_begin, clip_end):
            overlapping.append(
                {
                    "index": clip.get("index"),
                    "name": clip.get("name"),
                    "begin": clip_begin,
                    "end": clip_end,
                }
            )

    args = {
        "trackIndex": track_index,
        "pos": pos,
        "dur": dur,
        "type": clip_type,
    }
    if name:
        args["name"] = name
    created = client.call_tool("add_new_clip", args)
    return {
        "track_index": track_index,
        "track_name": track.get("trackName"),
        "requested": {
            "pos": pos,
            "dur": dur,
            "type": clip_type,
            "name": name,
        },
        "precheck": {
            "existing_clip_count": existing["clip_count"],
            "overlaps_existing_clips": bool(overlapping),
            "overlapping_clips": overlapping,
        },
        "created_clip": created,
    }
