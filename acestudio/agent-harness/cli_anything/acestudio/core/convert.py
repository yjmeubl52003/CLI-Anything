"""Tempo and position conversion helpers."""

from __future__ import annotations


def tick_to_time(client, tick: float) -> dict:
    data = client.call_tool("tick_to_time", {"tick": tick})
    return {"tick": tick, "time_seconds": data.get("time")}


def time_to_tick(client, time_seconds: float) -> dict:
    data = client.call_tool("time_to_tick", {"time": time_seconds})
    return {"time_seconds": time_seconds, "tick": data.get("tick")}


def tick_to_measure(client, tick: float, consider_beat_mode: bool) -> dict:
    data = client.call_tool("tick_to_measure_pos", {"tick": tick, "considerBeatMode": consider_beat_mode})
    return {
        "tick": tick,
        "consider_beat_mode": consider_beat_mode,
        "bar_pos": data.get("barPos"),
        "beat_pos": data.get("beatPos"),
        "tick_offset": data.get("tickOffset"),
    }


def measure_to_tick(client, bar_pos: int, tick_offset: int, consider_beat_mode: bool, beat_pos=None) -> dict:
    args = {
        "barPos": bar_pos,
        "tickOffset": tick_offset,
        "considerBeatMode": consider_beat_mode,
    }
    if beat_pos is not None:
        args["beatPos"] = beat_pos
    data = client.call_tool("measure_pos_to_tick", args)
    return {
        "bar_pos": bar_pos,
        "beat_pos": beat_pos,
        "tick_offset": tick_offset,
        "consider_beat_mode": consider_beat_mode,
        "tick": data.get("tick"),
    }
