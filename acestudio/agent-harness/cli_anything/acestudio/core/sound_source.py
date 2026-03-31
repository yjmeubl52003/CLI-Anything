"""Sound source browsing operations."""

from __future__ import annotations


from cli_anything.acestudio.mcp_client import ValidationError
from cli_anything.acestudio.core.track import _get_track_or_raise, get_meta


def list_sound_sources(client, source_type: str, category=None, keyword=None, language=None, tags=None) -> dict:
    args = {"type": source_type}
    if category:
        args["category"] = category
    if keyword:
        args["keyword"] = keyword
    if language:
        args["language"] = language
    if tags:
        args["tags"] = list(tags)
    data = client.call_tool("get_available_sound_source_list", args)
    return {
        "type": source_type,
        "filters": {
            "category": category,
            "keyword": keyword,
            "language": language,
            "tags": list(tags or []),
        },
        "results": data,
    }


def list_tags(client, source_type: str) -> dict:
    data = client.call_tool("get_suggested_sound_source_tag_list", {"type": source_type})
    return {"type": source_type, "results": data}


def list_community_voices(client, page: int = 0, is_my_collection: bool = False, keyword=None, language=None, tags=None) -> dict:
    args = {
        "page": page,
        "isMyCollection": is_my_collection,
    }
    if keyword:
        args["keyword"] = keyword
    if language:
        args["language"] = language
    if tags:
        args["tags"] = list(tags)
    data = client.call_tool("get_available_community_voice_list", args)
    return {
        "page": page,
        "is_my_collection": is_my_collection,
        "filters": {
            "keyword": keyword,
            "language": language,
            "tags": list(tags or []),
        },
        "results": data,
    }


def collect_community_voice(client, voice_id: int) -> dict:
    if voice_id <= 0:
        raise ValidationError("Community voice id must be greater than 0.")
    result = client.call_tool("collect_community_voice", {"id": voice_id})
    return {
        "voice_id": voice_id,
        "result": result,
    }


def load_sound_source(client, track_index: int, kind: str, source_id: int, group: str | None = None, router_id: int | None = None) -> dict:
    if kind not in {"singer", "choir", "instrument", "ensemble"}:
        raise ValidationError("Sound source kind must be singer, choir, instrument, or ensemble.")
    if source_id <= 0:
        raise ValidationError("Sound source id must be greater than 0.")
    if kind in {"singer", "choir"} and not group:
        raise ValidationError("--group is required for singer and choir sound sources.")

    track = _get_track_or_raise(client, track_index)
    meta = get_meta(client, track_index)
    args = {
        "trackIndex": track_index,
        "soundSourceType": kind,
        "id": source_id,
    }
    if group:
        args["group"] = group
    if router_id is not None:
        args["routerId"] = router_id
    result = client.call_tool("load_new_sound_source_on_track", args)
    return {
        "track_index": track_index,
        "track_name": track.get("trackName"),
        "kind": kind,
        "id": source_id,
        "group": group,
        "router_id": router_id,
        "precheck": {
            "track_exists": True,
            "track_type_before": track.get("trackType"),
            "track_meta_before": meta.get("meta"),
        },
        "result": result,
    }
