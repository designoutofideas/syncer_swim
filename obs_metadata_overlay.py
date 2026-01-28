# OBS Python script to display metadata overlays
# Place this file in OBS Scripts and configure the status file + text source.

import json
import os
from datetime import datetime, timezone
from pathlib import Path
import obspython as obs

status_file = str(Path("obs_status.json").resolve())
source_name = "Metadata Overlay"
last_media = None
visible_until = None


def format_metadata_text(metadata: dict) -> str:
    if not metadata:
        return ""
    title = metadata.get("title") or "Unknown Title"
    description = metadata.get("description") or ""
    air_date = metadata.get("original_air_date") or ""

    lines = [f"🎬 {title}"]
    if description:
        lines.append(description)
    if air_date:
        lines.append(f"📅 {air_date}")
    return "\n".join(lines)


def read_status() -> dict:
    try:
        if not os.path.exists(status_file):
            return {}
        with open(status_file, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception:
        return {}


def parse_utc(ts: str):
    try:
        return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except Exception:
        return None


def update_text_source(text: str) -> None:
    source = obs.obs_get_source_by_name(source_name)
    if source is None:
        return
    settings = obs.obs_data_create()
    obs.obs_data_set_string(settings, "text", text)
    obs.obs_source_update(source, settings)
    obs.obs_data_release(settings)
    obs.obs_source_release(source)


def tick():
    global last_media, visible_until

    status = read_status()
    current = status.get("current_item") or {}
    metadata = status.get("metadata") or {}
    display_until = parse_utc(status.get("display_until_utc", ""))

    media_key = current.get("media")
    now = datetime.now(timezone.utc)

    if media_key and media_key != last_media:
        text = format_metadata_text(metadata)
        update_text_source(text)
        last_media = media_key
        visible_until = display_until

    if visible_until and now >= visible_until:
        update_text_source("")
        visible_until = None


def script_description():
    return "Displays current media metadata from obs_status.json in a text source."


def script_properties():
    props = obs.obs_properties_create()
    obs.obs_properties_add_path(props, "status_file", "Status File", obs.OBS_PATH_FILE, "JSON Files (*.json)", None)
    obs.obs_properties_add_text(props, "source_name", "Text Source Name", obs.OBS_TEXT_DEFAULT)
    return props


def script_update(settings):
    global status_file, source_name
    status_file = obs.obs_data_get_string(settings, "status_file") or status_file
    source_name = obs.obs_data_get_string(settings, "source_name") or source_name


def script_defaults(settings):
    obs.obs_data_set_default_string(settings, "status_file", status_file)
    obs.obs_data_set_default_string(settings, "source_name", source_name)


def script_load(settings):
    obs.timer_add(tick, 1000)


def script_unload():
    obs.timer_remove(tick)
