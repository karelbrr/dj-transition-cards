# dj-transition-cards

Puts the covers and titles of the two tracks of a DJ transition clip onto the video, for TikTok and Reels.
It recognizes the tracks with ACRCloud, downloads the covers from Deezer (iTunes as a fallback), draws a card
and renders a 1080×1920 export with the card over the first seconds.

```bash
dj-cards ~/Desktop/clips              # every clip in the folder
dj-cards ~/Desktop/clip.mov           # one clip
dj-cards ~/Desktop/clips --overlay 4  # card on screen for 4 s
dj-cards ~/Desktop/clips --force      # render clips that already have an export again
```

Each clip gets a folder of its own next to it, with the audio, `pair.json`, the covers, the card and the
export `<clip>-tiktok.mp4`. The original clip is never changed.

## Setup

Needs Python 3.12+. ffmpeg comes with moviepy, nothing else to install.

```bash
git clone <repository url> dj-transition-cards
cd dj-transition-cards
python3 -m venv .venv
.venv/bin/pip install -e .
cp .env.example .env
```

Fill in `.env` with the keys of your own ACRCloud project (console.acrcloud.com → Audio & Video Recognition →
Projects: Recorded Audio, Audio Fingerprinting, bucket ACRCloud Music). `~/.config/dj-cards/.env` works too,
for a tool run from anywhere. Never commit `.env`.

To run `dj-cards` from any folder, link it into a folder on your `PATH`:

```bash
ln -s "$PWD/.venv/bin/dj-cards" ~/.local/bin/dj-cards
```

### Font

The card uses `src/dj_transition_cards/assets/fonts/Montserrat-Bold.ttf` when it is there (Montserrat is free
under the SIL Open Font License, fonts.google.com/specimen/Montserrat), otherwise a bold system font (Arial
Bold on macOS and Windows, DejaVu Sans Bold on Linux).

## Fixing a clip

`pair.json` holds the two recognized tracks; a later run reads it instead of recognizing again. When a track is
wrong or missing, edit it there (a `title` is enough), delete that track's cover in `covers/` if the track
changed, and run the clip again. Delete `pair.json` to recognize the clip anew.
