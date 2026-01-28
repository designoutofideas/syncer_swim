# Architecture

## Overview

This project runs a UTC-based playout schedule for OBS. The scheduler watches a media directory, extracts metadata with FFprobe, writes a status file, and allows hot-reload while broadcasting.

## Components

- broadcast_scheduler.py: daemon loop that scans ~/broadcast_media, extracts metadata, and writes obs_status.json.
- schedule_manager.py: CLI for managing schedule.json.
- obs_metadata_overlay.py: OBS script that shows metadata in a text source.
- setup.sh: installs dependencies and creates ~/broadcast_media.

## Data Files

- schedule.json: UTC schedule items, start times, and overlay duration.
- media_metadata.json: metadata extracted from media files.
- obs_status.json: current and next item, metadata, and display timing.

## Flow

1. Media files are copied into ~/broadcast_media.
2. broadcast_scheduler.py scans files and updates media_metadata.json.
3. schedule_manager.py edits schedule.json.
4. broadcast_scheduler.py merges schedule + metadata and writes obs_status.json.
5. obs_metadata_overlay.py reads obs_status.json and updates the OBS text source.
