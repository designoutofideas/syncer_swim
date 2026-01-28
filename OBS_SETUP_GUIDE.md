# OBS Setup Guide

## VLC Video Source (Recommended)

1. Open OBS Studio.
2. Add Source → VLC Video Source.
3. Click + and add files from ~/broadcast_media/.
4. Enable Loop Playlist.

## Metadata Overlay

1. Add Source → Text (GDI+).
2. Name it Metadata Overlay.
3. Tools → Scripts → Add obs_metadata_overlay.py.
4. Set Status File to obs_status.json.
5. Set Text Source Name to Metadata Overlay.

The script reads metadata from obs_status.json and shows it for the configured duration.
