# CLAUDE.md

Personal project, Python. Manual git and execution rules of `../../CLAUDE.md` apply: no commits, no runs.

## What it does

`dj-cards <folder>` takes every DJ transition clip in the folder (a short vertical video, about 30 s, one
transition between two tracks), recognizes the two tracks, downloads their cover art and renders the clip
again with both covers and titles on top, for TikTok, Reels and Shorts.

The reference look (a clip from 2026-10-22): both covers side by side in the upper third, each in a black
frame, the track title alone under each (no artist, shortened: "We found love" X "I Gotta feeling"), shown
for the first ~5 s and then gone. The upper third keeps the overlay out of TikTok's own UI at the bottom and
on the right.

## Pipeline

One clip is one pair of tracks. Every stage reads the previous stage's file and writes its own, so a stage
can be rerun alone and a corrected `pair.json` costs no new recognition:

```text
<folder>/clip.mov
  1. identify → .dj-cards/clip/pair.json   audio windows at the start, middle and end of the clip
  2. covers   → .dj-cards/clip/covers/     by the ids recognition returned, else by artist + title
  3. card     → .dj-cards/clip/card.png    cover A  X  cover B with titles, transparent PNG
  4. render   → out/clip.mp4               ffmpeg overlays the card for --overlay seconds, 1080×1920
```

`pair.json` is the hand-editable boundary: everything after it is deterministic, everything before it a
guess. It keeps the title as recognized next to the shortened display title, so either can be corrected.

Decisions:

- During a transition both tracks play at once and a recognizer usually names only the louder one, so the
  clip is queried in several windows; the track found earlier is A. A clip with one track found is marked
  for a manual fix, not rendered with one cover.
- Display titles drop `feat.`, remix and edit tags and bracketed parts; the artist is not shown.
- Text is drawn into the card PNG with Pillow, not with ffmpeg `drawtext` (diacritics, wrapping, shadows);
  ffmpeg only composites.
- ffmpeg and ffprobe are system dependencies called as processes, not Python bindings.
- The recognition service is not chosen yet (ACRCloud, AudD or the unofficial Shazam client `shazamio`);
  first check by hand that Shazam on a phone names both tracks of a clip at its start and end.
- Covers: Deezer API (no key, 1000×1000) first, iTunes Search API as a fallback.
