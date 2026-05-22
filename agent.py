import os
import re
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

# -------- Parsing --------

load_dotenv()


def _parse_timestamp(line: str) -> Optional[str]:
    m = re.match(r"^(\d{4}/\d{2}/\d{2})\s+(\d{2}:\d{2}:\d{2})", line)
    return f"{m.group(1)} {m.group(2)}" if m else None


_LOCATION_RE = re.compile(
    r"✅ Location - Lat:\s*(?P<lat>-?\d+\.\d+|-?\d+),\s*"
    r"Lon:\s*(?P<lon>-?\d+\.\d+|-?\d+),\s*"
    r"Speed:\s*(?P<speed>-?\d+\.\d+|-?\d+),\s*"
    r"Course:\s*(?P<course>-?\d+\.\d+|-?\d+),\s*"
    r"Serial:\s*(?P<serial>\d+)"
)

_IMEI_LOGIN_RE = re.compile(r"Login packet - IMEI:\s*(?P<imei>\d+)")
_IMEI_HEARTBEAT_RE = re.compile(r"IMEI IN HEARTBEAT:\s*(?P<imei>\d+)")
_SAVED_HEARTBEAT_RE = re.compile(r"Saved heartbeat for IMEI:\s*(?P<imei>\d+)")
_SAVED_LOCATION_RE = re.compile(r"Saved location for IMEI:\s*(?P<imei>\d+)")

_TERMINAL_KV = {
    "Defense": re.compile(r"- Defense:\s*(?P<v>.+)"),
    "ACC": re.compile(r"- ACC:\s*(?P<v>.+)"),
    "Charge": re.compile(r"- Charge:\s*(?P<v>.+)"),
    "GPS Tracking": re.compile(r"- GPS Tracking:\s*(?P<v>.+)"),
    "Oil/Electricity": re.compile(r"- Oil/Electricity:\s*(?P<v>.+)"),
    "Battery": re.compile(r"- Battery:\s*(?P<v>.+)"),
    "GSM Signal": re.compile(r"- GSM Signal:\s*(?P<v>.+)"),
}


def parse_gps_log(log_text: str) -> Dict[str, Any]:
    imeis_seen: set[str] = set()

    unknown_protocol_count = 0
    crc_mismatch_count = 0
    invalid_packet_count = 0

    last_location_per_imei: Dict[str, Dict[str, Any]] = {}
    terminal_snapshots_per_imei: Dict[str, List[Dict[str, Any]]] = {}

    current_terminal_data: Dict[str, str] = {}
    awaiting_terminal_snapshot = False

    # Many trackers log location packets after prior IMEI context;
    # we also fall back to the most recent IMEI seen in the stream.
    last_imei_for_location: Optional[str] = None
    last_imei_seen_in_stream: Optional[str] = None
    # If we see 'IMEI IN HEARTBEAT' (or login) but location packets come later,
    # treat that as the current IMEI context.
    current_imei_context: Optional[str] = None



    lines = log_text.splitlines()
    all_timestamps: List[str] = []

    for line in lines:
        ts = _parse_timestamp(line)
        if ts:
            all_timestamps.append(ts)

        if "⚠️ Unknown protocol" in line:
            unknown_protocol_count += 1
        if "CRC mismatch" in line:
            crc_mismatch_count += 1
        if "Invalid packet" in line:
            invalid_packet_count += 1

        m = _IMEI_LOGIN_RE.search(line)
        if m:
            imei_login = m.group("imei")
            imeis_seen.add(imei_login)
            current_imei_context = imei_login


        m = _IMEI_HEARTBEAT_RE.search(line)
        if m:
            imeis_seen.add(m.group("imei"))
            if awaiting_terminal_snapshot and current_terminal_data:
                imei = m.group("imei")
                terminal_snapshots_per_imei.setdefault(imei, []).append(
                    {"timestamp": ts, **current_terminal_data}
                )
                current_terminal_data = {}
                awaiting_terminal_snapshot = False

        m = _SAVED_HEARTBEAT_RE.search(line)
        if m:
            imeis_seen.add(m.group("imei"))

        m = _SAVED_LOCATION_RE.search(line)
        if m:
            last_imei_for_location = m.group("imei")

        # Track the most recent IMEI seen anywhere (login/heartbeat/saved heartbeat/terminal status)
        # as a fallback for location packets that don't get properly attributed.
        if last_imei_seen_in_stream is None:
            pass
        if not last_imei_seen_in_stream:
            # set if we can detect an IMEI on this line
            for rx in (_IMEI_LOGIN_RE, _IMEI_HEARTBEAT_RE, _SAVED_HEARTBEAT_RE):
                mm = rx.search(line)
                if mm:
                    last_imei_seen_in_stream = mm.group("imei")
                    break


        if "Terminal Status:" in line:
            current_terminal_data = {}
            awaiting_terminal_snapshot = True

        for _k, pat in _TERMINAL_KV.items():
            mm = pat.search(line)
            if mm:
                current_terminal_data[_k] = mm.group("v").strip()

        m = _LOCATION_RE.search(line)
        if m:
            imei = last_imei_for_location
            if imei is None:
                continue
            last_location_per_imei[imei] = {
                "timestamp": ts,
                "serial": m.group("serial"),
                "lat": float(m.group("lat")),
                "lon": float(m.group("lon")),
                "speed": float(m.group("speed")),
                "course": float(m.group("course")),
            }

    timestamps_sorted = sorted(all_timestamps)
    time_range = None
    if timestamps_sorted:
        time_range = {
            "start": timestamps_sorted[0],
            "end": timestamps_sorted[-1],
            "lines": len(timestamps_sorted),
        }

    return {
        "imeis_seen": sorted(imeis_seen),
        "time_range": time_range,
        "counters": {
            "unknown_protocol": unknown_protocol_count,
            "crc_mismatch": crc_mismatch_count,
            "invalid_packet": invalid_packet_count,
        },
        "last_location_per_imei": last_location_per_imei,
        "terminal_snapshots_per_imei": terminal_snapshots_per_imei,
    }


# -------- LLM (best-effort Groq via LangChain) --------


def _maybe_call_groq(prompt: str) -> Optional[str]:
    api_key = os.getenv("API_KEY")
    model = os.getenv("CHAT_MODEL")

    try:
        from langchain_groq import ChatGroq  # type: ignore
        from langchain_core.messages import HumanMessage  # type: ignore
    except Exception:
        return None

    if not api_key or not model:
        return None

    try:
        llm = ChatGroq(api_key=api_key, model=model)
        resp = llm.invoke([HumanMessage(content=prompt)])
        return getattr(resp, "content", None) or str(resp)
    except Exception:
        return None


# -------- Public API --------


def run_agent(log_path: str, user_question: Optional[str] = None) -> str:
    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
        log_text = f.read()

    facts = parse_gps_log(log_text)
    q = user_question or "What do I want to know from this GPS tracking log?"

    prompt = (
        "You are an AI assistant for a GPS tracking log.\n"
        "Use ONLY the provided JSON facts. If info is missing, say so.\n"
        "Return a helpful bullet-point answer.\n\n"
        f"USER_QUESTION: {q}\n\n"
        f"FACTS_JSON: {facts}\n"
    )

    llm_answer = _maybe_call_groq(prompt)
    if llm_answer:
        return llm_answer

    imeis = facts.get("imeis_seen", [])
    tr = facts.get("time_range")
    counters = facts.get("counters", {})
    last_locs: Dict[str, Dict[str, Any]] = facts.get("last_location_per_imei", {})

    q_lower = (q or "").lower()
    wants_location = any(k in q_lower for k in ["location", "lat", "lon", "coordinate", "coordinates"])
    wants_speed = any(k in q_lower for k in ["speed", "course", "direction"])
    wants_errors = any(k in q_lower for k in ["error", "crc", "mismatch", "invalid", "unknown protocol"])
    wants_device = any(k in q_lower for k in ["device", "imei", "devices"])

    bullets: List[str] = []
    bullets.append(f"**Devices seen:** {', '.join(imeis) if imeis else 'None'}")
    if tr:
        bullets.append(f"**Time range:** {tr['start']} → {tr['end']}")

    if wants_errors or (not wants_location and not wants_speed and not wants_device):
        bullets.append(
            "**Parsing counters:** "
            f"unknown_protocol={counters.get('unknown_protocol')}, "
            f"crc_mismatch={counters.get('crc_mismatch')}, "
            f"invalid_packet={counters.get('invalid_packet')}"
        )

    if wants_device or wants_location or wants_speed:
        bullets.append("**Latest known location per IMEI (from parsed log):**")
        if not last_locs:
            bullets.append("- No location packets were parsed.")
        else:
            for imei in imeis:
                loc = last_locs.get(imei)
                if not loc:
                    continue
                line = f"- IMEI {imei}: {loc.get('timestamp')} | lat={loc.get('lat')}, lon={loc.get('lon')}"
                if wants_speed:
                    line += f", speed={loc.get('speed')}, course={loc.get('course')}"
                bullets.append(line)

    if not bullets:
        bullets.append("**Summary:** Could not extract any structured facts from the log.")

    return "\n".join(
        [
            "**Report (offline parsed facts)**",
            f"**Your question:** {q}",
            *bullets,
        ]
    )


def run_lookup(log_path: str, imei: str) -> str:
    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
        log_text = f.read()

    facts = parse_gps_log(log_text)
    loc = facts.get("last_location_per_imei", {}).get(imei)
    snaps = facts.get("terminal_snapshots_per_imei", {}).get(imei, [])

    prompt = (
        "You are an AI assistant for a GPS tracking log.\n"
        "Use ONLY the provided JSON facts. If info is missing for that IMEI, say so.\n"
        "Return a short response in plain text with these fields if available:\n"
        "IEMI, Date, time, lat, lon, speed, direction(course), and latest terminal status fields.\n\n"
        f"USER_QUESTION: Lookup latest data for IMEI {imei}.\n\n"
        "FACTS_JSON:"
        f"{{\n  \"imei\": {imei!r},\n"
        f"  \"last_location\": {loc!r},\n"
        f"  \"terminal_snapshots\": {snaps[-1:]!r},\n"
        f"  \"devices_seen\": {facts.get('imeis_seen')!r},\n"
        f"  \"counters\": {facts.get('counters')!r}\n"
        "}}\n"
    )

    llm_answer = _maybe_call_groq(prompt)
    if llm_answer:
        return llm_answer

    # Offline fallback
    if not loc:
        last_snap = snaps[-1] if snaps else {}
        snap_ts = last_snap.get("timestamp")

        status_parts: List[str] = []
        for k, v in last_snap.items():
            if k == "timestamp":
                continue
            status_parts.append(f"{k}: {v}")

        status_text = "\n".join(status_parts)
        extra_ts = f"last_terminal_snapshot_time: {snap_ts}" if snap_ts else ""

        if status_text and extra_ts:
            return f"IEMI: {imei}\nstatus: location_not_found\n{extra_ts}\n{status_text}"
        if extra_ts:
            return f"IEMI: {imei}\nstatus: location_not_found\n{extra_ts}"
        return f"IEMI: {imei}\nstatus: location_not_found"

    ts = loc.get("timestamp")
    date_part, time_part = (None, None)
    if ts and " " in ts:
        date_part, time_part = ts.split(" ", 1)
    elif ts:
        time_part = ts

    return (
        f"IEMI: {imei}\n"
        f"Date: {date_part or ''}\n"
        f"time: {time_part or ''}\n"
        f"lat: {loc.get('lat')}\n"
        f"lon: {loc.get('lon')}\n"
        f"speed: {loc.get('speed')}\n"
        f"direction: {loc.get('course')}"
    )

