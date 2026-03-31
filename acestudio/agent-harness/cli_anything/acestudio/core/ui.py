"""UI visibility operations."""

from __future__ import annotations


from cli_anything.acestudio.mcp_client import ValidationError


SPECIAL_TRACK_MAP = {
    "chord": "chord",
    "tempo-and-timesig": "tempo_and_timesig",
}


def set_mixer_visibility(client, visible: bool) -> dict:
    result = client.call_tool("set_mixer_visibility", {"visible": visible})
    return {
        "visible": visible,
        "result": result,
    }


def set_special_track_visibility(client, track_name: str, visible: bool) -> dict:
    mapped = SPECIAL_TRACK_MAP.get(track_name)
    if not mapped:
        raise ValidationError("Special track must be chord or tempo-and-timesig.")
    result = client.call_tool("set_special_track_visibility", {"track": mapped, "visible": visible})
    return {
        "track": track_name,
        "visible": visible,
        "result": result,
    }
