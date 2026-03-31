"""Project-related ACE Studio operations."""

from __future__ import annotations

from typing import Any

from cli_anything.acestudio.mcp_client import ValidationError


def get_info(client) -> dict[str, Any]:
    data = client.call_tool("get_project_status_info")
    return {
        "project_name": data.get("projectName", ""),
        "is_temp_project": data.get("isTempProject", False),
        "is_new_project": data.get("isNewProject", False),
        "duration_ticks": data.get("duration"),
    }


def get_playback_status(client) -> dict[str, Any]:
    data = client.call_tool("get_playback_status")
    return {
        "status": data.get("status"),
        "position_seconds": data.get("position"),
    }


def get_synthesis_status(client) -> dict[str, Any]:
    data = client.call_tool("get_synthesis_status")
    if isinstance(data, dict):
        return data
    return {"status": data}


def get_tempo_list(client) -> dict[str, Any]:
    data = client.call_tool("get_tempo_automation")
    points = data.get("points", [])
    return {
        "point_count": data.get("pointCount", len(points)),
        "points": [
            {
                "tick": point.get("pos"),
                "bpm": point.get("value"),
                "bend": point.get("bend"),
            }
            for point in points
        ],
    }


def get_timesig_list(client) -> dict[str, Any]:
    data = client.call_tool("get_timesignature_list")
    signatures = data.get("signatures", [])
    return {
        "signature_count": data.get("signatureCount", len(signatures)),
        "signatures": [
            {
                "bar_pos": item.get("barPos"),
                "numerator": item.get("numerator"),
                "denominator": item.get("denominator"),
            }
            for item in signatures
        ],
    }


def _normalize_tempo_points(points: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not isinstance(points, list) or not points:
        raise ValidationError("Tempo points must be a non-empty JSON array.")
    normalized = []
    last_pos = None
    for point in points:
        if not isinstance(point, dict):
            raise ValidationError("Each tempo point must be an object.")
        if "pos" not in point or "value" not in point:
            raise ValidationError("Each tempo point must include pos and value.")
        pos = point["pos"]
        value = point["value"]
        bend = point.get("bend")
        if not isinstance(pos, (int, float)) or pos < 0:
            raise ValidationError("Tempo point pos must be a number greater than or equal to 0.")
        if not isinstance(value, (int, float)) or value < 1 or value > 1000:
            raise ValidationError("Tempo point value must be between 1 and 1000 BPM.")
        if last_pos is not None and pos <= last_pos:
            raise ValidationError("Tempo points must be strictly increasing by pos.")
        normalized_point = {"pos": pos, "value": value}
        if bend is not None:
            if not isinstance(bend, (int, float)):
                raise ValidationError("Tempo point bend must be numeric when provided.")
            normalized_point["bend"] = bend
        normalized.append(normalized_point)
        last_pos = pos
    return normalized


def _normalize_timesig_signatures(signatures: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not isinstance(signatures, list) or not signatures:
        raise ValidationError("Time signatures must be a non-empty JSON array.")
    normalized = []
    last_bar_pos = None
    valid_denominators = {2, 4, 8, 16, 32}
    for signature in signatures:
        if not isinstance(signature, dict):
            raise ValidationError("Each time signature entry must be an object.")
        if "barPos" not in signature or "numerator" not in signature or "denominator" not in signature:
            raise ValidationError("Each time signature entry must include barPos, numerator, and denominator.")
        bar_pos = signature["barPos"]
        numerator = signature["numerator"]
        denominator = signature["denominator"]
        if not isinstance(bar_pos, int) or bar_pos < 0:
            raise ValidationError("Time signature barPos must be an integer greater than or equal to 0.")
        if not isinstance(numerator, int) or numerator <= 0:
            raise ValidationError("Time signature numerator must be a positive integer.")
        if denominator not in valid_denominators:
            raise ValidationError("Time signature denominator must be one of 2, 4, 8, 16, or 32.")
        if last_bar_pos is not None and bar_pos <= last_bar_pos:
            raise ValidationError("Time signatures must be strictly increasing by barPos.")
        normalized.append(
            {
                "barPos": bar_pos,
                "numerator": numerator,
                "denominator": denominator,
            }
        )
        last_bar_pos = bar_pos
    return normalized


def set_tempo_automation(client, points: list[dict[str, Any]], replace_all: bool) -> dict[str, Any]:
    if not replace_all:
        raise ValidationError("set-tempo requires --replace-all because ACE Studio replaces the full tempo map.")
    current = get_tempo_list(client)
    normalized_points = _normalize_tempo_points(points)
    result = client.call_tool("set_tempo_automation", {"points": normalized_points})
    return {
        "replace_all": True,
        "point_count_before": current.get("point_count"),
        "point_count_after": len(normalized_points),
        "points_submitted": normalized_points,
        "result": result,
    }


def set_timesignature_list(client, signatures: list[dict[str, Any]], replace_all: bool) -> dict[str, Any]:
    if not replace_all:
        raise ValidationError("set-timesig requires --replace-all because ACE Studio replaces the full time signature map.")
    current = get_timesig_list(client)
    normalized_signatures = _normalize_timesig_signatures(signatures)
    result = client.call_tool("set_timesignature_list", {"signatures": normalized_signatures})
    return {
        "replace_all": True,
        "signature_count_before": current.get("signature_count"),
        "signature_count_after": len(normalized_signatures),
        "signatures_submitted": normalized_signatures,
        "result": result,
    }
