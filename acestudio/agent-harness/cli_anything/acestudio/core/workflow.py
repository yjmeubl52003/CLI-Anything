"""Higher-level ACE Studio workflow helpers."""

from __future__ import annotations

from typing import Any

from cli_anything.acestudio.core import clip as clip_core
from cli_anything.acestudio.core import convert as convert_core
from cli_anything.acestudio.core import project as project_core
from cli_anything.acestudio.core import sound_source as sound_source_core
from cli_anything.acestudio.core import track as track_core
from cli_anything.acestudio.mcp_client import ValidationError


def _validate_section(section: dict[str, Any], index: int) -> dict[str, Any]:
    if not isinstance(section, dict):
        raise ValidationError(f"Section #{index + 1} must be an object.")
    name = section.get("name")
    bars = section.get("bars")
    if not isinstance(name, str) or not name.strip():
        raise ValidationError(f"Section #{index + 1} must include a non-empty name.")
    if not isinstance(bars, int) or bars <= 0:
        raise ValidationError(f"Section {name!r} must have a positive integer bars value.")
    target_roles = section.get("target_roles")
    if target_roles is not None:
        if not isinstance(target_roles, list) or not all(isinstance(role, str) and role for role in target_roles):
            raise ValidationError(f"Section {name!r} target_roles must be a list of role names.")
    return {
        "name": name.strip(),
        "bars": bars,
        "target_roles": target_roles,
    }


def _validate_track_spec(track_spec: dict[str, Any], existing_indexes: set[int], index: int) -> dict[str, Any]:
    if not isinstance(track_spec, dict):
        raise ValidationError(f"Track spec #{index + 1} must be an object.")
    role = track_spec.get("role")
    track_index = track_spec.get("track_index")
    clip_type = track_spec.get("clip_type")
    prefix = track_spec.get("prefix") or role
    if not isinstance(role, str) or not role.strip():
        raise ValidationError(f"Track spec #{index + 1} must include a non-empty role.")
    if not isinstance(track_index, int):
        raise ValidationError(f"Track spec {role!r} must include an integer track_index.")
    if track_index not in existing_indexes:
        raise ValidationError(f"Track spec {role!r} refers to missing track index {track_index}.")
    if clip_type not in {"sing", "instrument", "genericmidi"}:
        raise ValidationError(f"Track spec {role!r} clip_type must be sing, instrument, or genericmidi.")
    sound_source = track_spec.get("sound_source")
    if sound_source is not None:
        if not isinstance(sound_source, dict):
            raise ValidationError(f"Track spec {role!r} sound_source must be an object.")
        kind = sound_source.get("kind")
        source_id = sound_source.get("id")
        group = sound_source.get("group")
        if kind not in {"singer", "choir", "instrument", "ensemble"}:
            raise ValidationError(f"Track spec {role!r} sound_source.kind is invalid.")
        if not isinstance(source_id, int) or source_id <= 0:
            raise ValidationError(f"Track spec {role!r} sound_source.id must be a positive integer.")
        if kind in {"singer", "choir"} and not isinstance(group, str):
            raise ValidationError(f"Track spec {role!r} singer/choir sound_source requires group.")
    return {
        "role": role.strip(),
        "track_index": track_index,
        "clip_type": clip_type,
        "prefix": str(prefix).strip(),
        "sound_source": sound_source,
    }


def validate_song_skeleton_spec(spec: dict[str, Any], client) -> dict[str, Any]:
    if not isinstance(spec, dict):
        raise ValidationError("Song skeleton spec must be a JSON object.")
    tempo = spec.get("tempo")
    timesig = spec.get("timesig")
    sections = spec.get("sections")
    tracks = spec.get("tracks")
    if tempo is None or timesig is None or sections is None or tracks is None:
        raise ValidationError("Song skeleton spec must include tempo, timesig, sections, and tracks.")
    if not isinstance(sections, list) or not sections:
        raise ValidationError("Song skeleton spec must include at least one section.")
    if not isinstance(tracks, list) or not tracks:
        raise ValidationError("Song skeleton spec must include at least one target track.")

    existing_track_info = track_core.list_tracks(client)
    existing_indexes = {track["index"] for track in existing_track_info["tracks"]}

    normalized_sections = [_validate_section(section, i) for i, section in enumerate(sections)]
    normalized_tracks = [_validate_track_spec(track, existing_indexes, i) for i, track in enumerate(tracks)]

    roles = {track["role"] for track in normalized_tracks}
    for section in normalized_sections:
        if section["target_roles"] is not None:
            unknown = [role for role in section["target_roles"] if role not in roles]
            if unknown:
                raise ValidationError(
                    f"Section {section['name']!r} references unknown target_roles: {', '.join(unknown)}."
                )

    return {
        "tempo": tempo,
        "timesig": timesig,
        "sections": normalized_sections,
        "tracks": normalized_tracks,
        "existing_tracks": existing_track_info,
    }


def _section_boundaries(client, sections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    boundaries = []
    current_bar = 0
    for section in sections:
        start_info = convert_core.measure_to_tick(client, current_bar, 0, False)
        end_info = convert_core.measure_to_tick(client, current_bar + section["bars"], 0, False)
        boundaries.append(
            {
                "name": section["name"],
                "bars": section["bars"],
                "target_roles": section["target_roles"],
                "start_bar": current_bar,
                "end_bar": current_bar + section["bars"],
                "start_tick": start_info["tick"],
                "end_tick": end_info["tick"],
            }
        )
        current_bar += section["bars"]
    return boundaries


def build_song_skeleton_plan(client, spec: dict[str, Any]) -> dict[str, Any]:
    validated = validate_song_skeleton_spec(spec, client)
    tempo_result = project_core.set_tempo_automation(client, validated["tempo"], replace_all=True)
    timesig_result = project_core.set_timesignature_list(client, validated["timesig"], replace_all=True)
    sections = _section_boundaries(client, validated["sections"])

    clip_plan = []
    for track_spec in validated["tracks"]:
        for section in sections:
            target_roles = section["target_roles"]
            if target_roles is not None and track_spec["role"] not in target_roles:
                continue
            duration = section["end_tick"] - section["start_tick"]
            clip_plan.append(
                {
                    "track_index": track_spec["track_index"],
                    "role": track_spec["role"],
                    "clip_type": track_spec["clip_type"],
                    "name": f"{section['name']} {track_spec['prefix']}",
                    "pos": section["start_tick"],
                    "dur": duration,
                    "section": section["name"],
                }
            )

    return {
        "tempo_result": tempo_result,
        "timesig_result": timesig_result,
        "sections": sections,
        "tracks": validated["tracks"],
        "clip_plan": clip_plan,
        "existing_tracks": validated["existing_tracks"],
    }


def song_skeleton(client, spec: dict[str, Any], dry_run: bool = False) -> dict[str, Any]:
    plan = build_song_skeleton_plan(client, spec)
    if dry_run:
        return {
            "dry_run": True,
            "summary": {
                "section_count": len(plan["sections"]),
                "track_count": len(plan["tracks"]),
                "clip_count": len(plan["clip_plan"]),
            },
            "sections": plan["sections"],
            "tracks": plan["tracks"],
            "clip_plan": plan["clip_plan"],
        }

    created_clips = []
    loaded_sound_sources = []
    loaded_for_tracks: set[int] = set()

    for track_spec in plan["tracks"]:
        sound_source = track_spec.get("sound_source")
        if sound_source and track_spec["track_index"] not in loaded_for_tracks:
            loaded_sound_sources.append(
                sound_source_core.load_sound_source(
                    client,
                    track_spec["track_index"],
                    sound_source["kind"],
                    sound_source["id"],
                    sound_source.get("group"),
                    sound_source.get("router_id"),
                )
            )
            loaded_for_tracks.add(track_spec["track_index"])

    for clip_item in plan["clip_plan"]:
        created_clips.append(
            clip_core.add_clip(
                client,
                clip_item["track_index"],
                clip_item["pos"],
                clip_item["dur"],
                clip_item["clip_type"],
                clip_item["name"],
            )
        )

    return {
        "dry_run": False,
        "summary": {
            "section_count": len(plan["sections"]),
            "track_count": len(plan["tracks"]),
            "clip_count": len(created_clips),
            "sound_source_load_count": len(loaded_sound_sources),
        },
        "tempo_result": plan["tempo_result"],
        "timesig_result": plan["timesig_result"],
        "sections": plan["sections"],
        "created_clips": created_clips,
        "loaded_sound_sources": loaded_sound_sources,
    }
