#!/usr/bin/env python3
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

MEDIA_DIR = Path(os.path.expanduser("~/broadcast_media"))
SCHEDULE_FILE = Path("schedule.json")
METADATA_FILE = Path("media_metadata.json")


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


def load_schedule() -> Dict:
    default = {"timezone": "UTC", "items": [], "last_updated": format_utc(utc_now())}
    return safe_read_json(SCHEDULE_FILE, default)


def save_schedule(schedule: Dict) -> None:
    schedule["last_updated"] = format_utc(utc_now())
    atomic_write_json(SCHEDULE_FILE, schedule)


def load_metadata() -> Dict:
    return safe_read_json(METADATA_FILE, {"items": {}})


def list_media_items(metadata: Dict) -> List[str]:
    return sorted(metadata.get("items", {}).keys())


def prompt_time() -> str:
    while True:
        value = input("Enter UTC time (HH:MM:SS): ").strip()
        parts = value.split(":")
        if len(parts) == 3 and all(part.isdigit() for part in parts):
            hour, minute, second = [int(p) for p in parts]
            if 0 <= hour < 24 and 0 <= minute < 60 and 0 <= second < 60:
                return f"{hour:02d}:{minute:02d}:{second:02d}"
        print("Invalid time format.")


def prompt_int(message: str, default: int) -> int:
    value = input(f"{message} [{default}]: ").strip()
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def add_schedule_item(schedule: Dict, metadata: Dict) -> None:
    media_items = list_media_items(metadata)
    if not media_items:
        print("No media files found in metadata. Run a rescan first.")
        return

    print("Available media:")
    for idx, name in enumerate(media_items, start=1):
        print(f"{idx}. {name}")

    choice = input("Select media number: ").strip()
    if not choice.isdigit() or not (1 <= int(choice) <= len(media_items)):
        print("Invalid selection.")
        return

    media_name = media_items[int(choice) - 1]
    time_str = prompt_time()
    display_duration = prompt_int("Metadata display duration (seconds)", 10)

    schedule["items"].append(
        {
            "time": time_str,
            "media": media_name,
            "metadata_display_duration": display_duration,
        }
    )
    schedule["items"] = sorted(schedule["items"], key=lambda x: x.get("time", ""))
    save_schedule(schedule)
    print("Schedule item added.")


def remove_schedule_item(schedule: Dict) -> None:
    items = schedule.get("items", [])
    if not items:
        print("No schedule items.")
        return

    print("Scheduled items:")
    for idx, item in enumerate(items, start=1):
        print(f"{idx}. {item['time']} -> {item['media']}")

    choice = input("Remove which item number: ").strip()
    if not choice.isdigit() or not (1 <= int(choice) <= len(items)):
        print("Invalid selection.")
        return

    items.pop(int(choice) - 1)
    schedule["items"] = items
    save_schedule(schedule)
    print("Schedule item removed.")


def list_schedule(schedule: Dict) -> None:
    items = schedule.get("items", [])
    if not items:
        print("No schedule items.")
        return
    for item in items:
        print(f"{item['time']} -> {item['media']}")


def auto_fill(schedule: Dict, metadata: Dict) -> None:
    media_items = list_media_items(metadata)
    if not media_items:
        print("No media files found in metadata. Run a rescan first.")
        return

    confirm = input("This will overwrite the current schedule. Type 'yes' to continue: ").strip()
    if confirm.lower() != "yes":
        print("Cancelled.")
        return

    schedule["items"] = []
    hour = 0
    for media_name in media_items:
        time_str = f"{hour:02d}:00:00"
        schedule["items"].append(
            {
                "time": time_str,
                "media": media_name,
                "metadata_display_duration": 10,
            }
        )
        hour = (hour + 1) % 24
        if hour == 0:
            break

    save_schedule(schedule)
    print("Schedule auto-filled for 24 hours.")


def export_playlist(schedule: Dict) -> None:
    playlist_path = Path("obs_playlist.m3u")
    metadata = load_metadata()
    items = schedule.get("items", [])
    media_lookup = metadata.get("items", {})

    lines = ["#EXTM3U"]
    for item in items:
        media_name = item.get("media")
        media = media_lookup.get(media_name)
        if not media:
            continue
        lines.append(media.get("path", media_name))

    playlist_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Playlist exported to {playlist_path}")


def rescan_metadata() -> None:
    from broadcast_scheduler import update_metadata_cache

    update_metadata_cache()
    print("Metadata rescan complete.")


def show_status() -> None:
    status = safe_read_json(Path("obs_status.json"), None)
    if not status:
        print("No status file found.")
        return
    current = status.get("current_item")
    next_item = status.get("next_item")
    print(f"UTC now: {status.get('current_utc')}")
    if current:
        print(f"Now: {current.get('time')} -> {current.get('media')}")
    if next_item:
        print(f"Next: {next_item.get('time')} -> {next_item.get('media')}")


def ensure_directories() -> None:
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)


def main() -> None:
    ensure_directories()
    schedule = load_schedule()
    metadata = load_metadata()

    while True:
        print("\nSchedule Manager")
        print("1. List schedule")
        print("2. Remove schedule item")
        print("3. Add schedule item")
        print("4. Rescan media metadata")
        print("5. Auto-Fill 24 Hours")
        print("6. Current Status")
        print("7. Export Playlist")
        print("8. Reload metadata")
        print("9. Exit")

        choice = input("Select option: ").strip()
        if choice == "1":
            list_schedule(schedule)
        elif choice == "2":
            remove_schedule_item(schedule)
        elif choice == "3":
            metadata = load_metadata()
            add_schedule_item(schedule, metadata)
        elif choice == "4":
            rescan_metadata()
            metadata = load_metadata()
        elif choice == "5":
            metadata = load_metadata()
            auto_fill(schedule, metadata)
        elif choice == "6":
            show_status()
        elif choice == "7":
            export_playlist(schedule)
        elif choice == "8":
            metadata = load_metadata()
            print("Metadata reloaded.")
        elif choice == "9":
            break
        else:
            print("Invalid option.")


if __name__ == "__main__":
    main()
