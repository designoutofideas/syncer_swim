#!/usr/bin/env python3
import json
import os
import time
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

MEDIA_DIR = Path(os.path.expanduser("~/broadcast_media"))
SCHEDULE_FILE = Path("schedule.json")
METADATA_FILE = Path("media_metadata.json")
STATUS_FILE = Path("obs_status.json")
SUPPORTED_VIDEO_EXTS = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".m4v"}
SUPPORTED_AUDIO_EXTS = {".mp3", ".wav", ".flac", ".aac", ".ogg"}
SUPPORTED_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}

POLL_INTERVAL_SECONDS = 1
RESCAN_INTERVAL_SECONDS = 10


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def format_utc(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def safe_read_json(path: Path, default):
    try:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def atomic_write_json(path: Path, data) -> None:
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    tmp_path.replace(path)


def ffprobe_metadata(file_path: Path) -> Dict:
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_format",
                "-show_entries",
                "format=duration:format_tags=title,comment,description,date,creation_time",
                str(file_path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(result.stdout)
    except Exception:
        payload = {}

    tags = payload.get("format", {}).get("tags", {}) if payload else {}
    duration = payload.get("format", {}).get("duration") if payload else None

    title = tags.get("title") or file_path.stem
    description = tags.get("description") or tags.get("comment") or ""
    original_air_date = tags.get("date") or tags.get("creation_time") or ""

    return {
        "title": title,
        "description": description,
        "original_air_date": original_air_date,
        "duration_seconds": float(duration) if duration else None,
    }


def discover_media(directory: Path) -> Dict[str, Dict]:
    items: Dict[str, Dict] = {}
    if not directory.exists():
        return items

    all_files = [p for p in directory.rglob("*") if p.is_file()]
    images_by_stem = {p.stem: p for p in all_files if p.suffix.lower() in SUPPORTED_IMAGE_EXTS}

    for file_path in all_files:
        ext = file_path.suffix.lower()
        if ext in SUPPORTED_VIDEO_EXTS:
            metadata = ffprobe_metadata(file_path)
            items[file_path.name] = {
                "type": "video",
                "path": str(file_path),
                **metadata,
            }
        elif ext in SUPPORTED_AUDIO_EXTS:
            image_path = images_by_stem.get(file_path.stem)
            metadata = ffprobe_metadata(file_path)
            items[file_path.name] = {
                "type": "audio",
                "path": str(file_path),
                "image_path": str(image_path) if image_path else None,
                **metadata,
            }
    return items


def update_metadata_cache() -> Dict:
    media_items = discover_media(MEDIA_DIR)
    payload = {
        "updated_at": format_utc(utc_now()),
        "items": media_items,
    }
    atomic_write_json(METADATA_FILE, payload)
    return payload


def load_schedule() -> Dict:
    default = {"timezone": "UTC", "items": [], "last_updated": format_utc(utc_now())}
    return safe_read_json(SCHEDULE_FILE, default)


def parse_time_to_seconds(time_str: str) -> Optional[int]:
    try:
        parts = [int(p) for p in time_str.split(":")]
        if len(parts) != 3:
            return None
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    except Exception:
        return None


def resolve_schedule_items(schedule: Dict) -> List[Dict]:
    items = schedule.get("items", [])
    normalized = []
    for item in items:
        seconds = parse_time_to_seconds(item.get("time", ""))
        if seconds is None:
            continue
        normalized.append({**item, "_seconds": seconds})
    normalized.sort(key=lambda x: x["_seconds"])
    return normalized


def select_current_item(schedule_items: List[Dict], now_utc: datetime) -> Tuple[Optional[Dict], Optional[Dict]]:
    if not schedule_items:
        return None, None

    now_seconds = now_utc.hour * 3600 + now_utc.minute * 60 + now_utc.second
    current = None
    next_item = None

    for idx, item in enumerate(schedule_items):
        if item["_seconds"] <= now_seconds:
            current = item
            if idx + 1 < len(schedule_items):
                next_item = schedule_items[idx + 1]
            else:
                next_item = schedule_items[0]
        elif item["_seconds"] > now_seconds and current is None:
            next_item = item
            current = schedule_items[-1]
            break

    if current is None:
        current = schedule_items[-1]
    if next_item is None:
        next_item = schedule_items[0]

    return current, next_item


def build_status(current_item: Optional[Dict], next_item: Optional[Dict], metadata_cache: Dict) -> Dict:
    now = utc_now()
    status = {
        "current_utc": format_utc(now),
        "current_item": None,
        "next_item": None,
        "metadata": None,
    }

    items = metadata_cache.get("items", {})

    if current_item:
        media_key = current_item.get("media")
        metadata = items.get(media_key)
        display_duration = current_item.get("metadata_display_duration", 10)
        display_until = now.timestamp() + int(display_duration)
        status["current_item"] = {
            "time": current_item.get("time"),
            "media": media_key,
            "metadata_display_duration": display_duration,
        }
        status["metadata"] = metadata
        status["display_until_utc"] = format_utc(datetime.fromtimestamp(display_until, tz=timezone.utc))

    if next_item:
        status["next_item"] = {
            "time": next_item.get("time"),
            "media": next_item.get("media"),
        }

    return status


def run_scheduler() -> None:
    print("Starting broadcast scheduler...")
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)

    metadata_cache = safe_read_json(METADATA_FILE, {"items": {}})
    last_metadata_scan = 0.0

    schedule_cache = load_schedule()
    schedule_mtime = SCHEDULE_FILE.stat().st_mtime if SCHEDULE_FILE.exists() else 0.0

    while True:
        now = time.time()
        if now - last_metadata_scan > RESCAN_INTERVAL_SECONDS:
            metadata_cache = update_metadata_cache()
            last_metadata_scan = now

        if SCHEDULE_FILE.exists():
            mtime = SCHEDULE_FILE.stat().st_mtime
            if mtime != schedule_mtime:
                schedule_cache = load_schedule()
                schedule_mtime = mtime

        schedule_items = resolve_schedule_items(schedule_cache)
        current_item, next_item = select_current_item(schedule_items, utc_now())
        status = build_status(current_item, next_item, metadata_cache)
        atomic_write_json(STATUS_FILE, status)
        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    run_scheduler()
