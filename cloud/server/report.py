"""Morning report = query over events.jsonl."""

from __future__ import annotations

from typing import Any

from store import store


def build_morning_report() -> dict[str, Any]:
    events = store.read_all()
    episodes: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None

    for msg in events:
        t = msg.get("type")
        p = msg.get("payload") or {}
        ts = msg.get("ts", 0)

        if t == "agent_state":
            state = p.get("state")
            if state in {"ATTEND", "LEAD", "ESCALATE", "EMERGENCY", "FOLLOW"} and current is None:
                current = {
                    "start_ts": ts,
                    "peak_state": state,
                    "agitation": p.get("agitation"),
                    "reason": p.get("reason"),
                    "resolution": None,
                    "end_ts": None,
                }
            elif current is not None:
                # escalate peak
                order = ["IDLE", "ATTEND", "LEAD", "ESCALATE", "EMERGENCY", "FOLLOW"]
                if state in order and order.index(state) > order.index(current["peak_state"]):
                    current["peak_state"] = state
                if state == "IDLE":
                    current["end_ts"] = ts
                    current["resolution"] = "resolved"
                    current["duration_s"] = round(ts - current["start_ts"], 1)
                    episodes.append(current)
                    current = None

        elif t == "caregiver_ack" and current is not None:
            current["resolution"] = f"caregiver:{p.get('action')}"
            current["end_ts"] = ts
            current["duration_s"] = round(ts - current["start_ts"], 1)
            episodes.append(current)
            current = None

        elif t == "alert" and current is not None:
            current["alert_headline"] = p.get("headline")

    if current is not None:
        current["end_ts"] = events[-1].get("ts") if events else current["start_ts"]
        current["duration_s"] = round(current["end_ts"] - current["start_ts"], 1)
        current["resolution"] = current.get("resolution") or "open"
        episodes.append(current)

    return {
        "episode_count": len(episodes),
        "episodes": episodes,
        "summary": _summary(episodes),
    }


def _summary(episodes: list[dict[str, Any]]) -> str:
    if not episodes:
        return "A quiet night. Everything was calm."
    n = len(episodes)
    resolved = sum(1 for e in episodes if e.get("resolution") and e["resolution"] != "open")
    parts = []
    for e in episodes:
        dur = e.get("duration_s", 0)
        mins = int(dur // 60)
        secs = int(dur % 60)
        parts.append(
            f"{e.get('peak_state')} for {mins}m{secs:02d}s — {e.get('reason', '')} "
            f"({e.get('resolution', 'open')})"
        )
    head = f"{n} event{'s' if n != 1 else ''} overnight, {resolved} resolved."
    return head + " " + " · ".join(parts)
