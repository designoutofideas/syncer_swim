# Quickstart

## 1) Install

Run the setup script:

./setup.sh

## 2) Add Media

Copy media files into your broadcast folder:

cp /path/to/media/* ~/broadcast_media/

Supported:
- Video: mp4, mkv, mov, avi, webm, m4v
- Audio: mp3, wav, flac, aac, ogg (optional matching image by same filename)

## 3) Start the Scheduler

python3 broadcast_scheduler.py

## 4) Create a Schedule

Open another terminal:

python3 schedule_manager.py

Quick workflow:
- Option 5: Auto-Fill 24 Hours
- Type yes
- Option 9: Exit

## 5) Configure OBS

See OBS setup instructions in [OBS_SETUP_GUIDE.md](OBS_SETUP_GUIDE.md).
