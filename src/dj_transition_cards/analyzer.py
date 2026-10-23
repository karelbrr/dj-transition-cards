from acrcloud.recognizer import ACRCloudRecognizer
import os
import re
from dotenv import load_dotenv
import json
from pathlib import Path

from dj_transition_cards import console

NO_RESULT = 1001
ACRCLOUD_KEYS = ("ACRCLOUD_HOST", "ACRCLOUD_ACCESS_KEY", "ACRCLOUD_ACCESS_SECRET")
USER_ENV = Path.home() / ".config" / "dj-cards" / ".env"

MASHUP_SEPARATOR = re.compile(r"\s+(?:x|vs\.?|×)\s+", re.IGNORECASE)
BRACKETS = re.compile(r"\([^)]*\)|\[[^\]]*\]")
VERSION_SUFFIX = re.compile(r"\s+-\s+.*$")
FEATURING = re.compile(r"\s+(?:feat\.?|ft\.?|featuring)\s+.*$", re.IGNORECASE)
VERSION_WORDS = {"remix", "extended", "edit", "mix", "radio", "version", "original", "club", "remastered"}


class Analyzer():
    def __init__(self, audioPath):
        # The project's .env first, then the user's; neither overrides a variable already set.
        load_dotenv()
        load_dotenv(USER_ENV)
        missing = [name for name in ACRCLOUD_KEYS if not os.getenv(name)]
        if missing:
            raise RuntimeError(f"ACRCloud keys missing ({', '.join(missing)}): copy .env.example to .env "
                               f"or to {USER_ENV} and fill it in")

        self.audioPath = audioPath
        self.recognizer = ACRCloudRecognizer({
            'host': os.getenv('ACRCLOUD_HOST'),
            'access_key': os.getenv('ACRCLOUD_ACCESS_KEY'),
            'access_secret': os.getenv('ACRCLOUD_ACCESS_SECRET'),
            'timeout': 10,
        })

    def analyzeAll(self, duration, step=5, minScore=50):
        # Variants of one song (remix, extended mix, cover) share a title key and become one track;
        # a mashup ("A X B") counts as a sighting of each of its parts.
        console.step("Identify", f"a ~10 s window every {step} s over {duration:.1f} s")
        tracks = {}
        start = 0
        while start < duration - 3:
            for hit in self.recognizeWindow(start):
                for title, artist in splitMashup(hit):
                    key = titleKey(title)
                    track = tracks.get(key)
                    if track is None:
                        tracks[key] = {"title": title, "artist": artist, "score": hit["score"],
                                       "firstSeen": start, "windows": [start], "displayTitle": displayTitle(title), }
                        continue
                    if start not in track["windows"]:
                        track["windows"].append(start)
                    if artist and (track["artist"] is None or hit["score"] > track["score"]):
                        track["title"], track["artist"] = title, artist
                    track["score"] = max(track["score"], hit["score"])
            start += step

        confident = [t for t in tracks.values() if t["score"] >= minScore or len(t["windows"]) >= 2]
        console.done(f"{len(confident)} tracks, {len(tracks) - len(confident)} dropped "
                     f"(score under {minScore} in a single window)")
        if len(confident) != 2:
            console.warn(f"expected 2 tracks of a transition, found {len(confident)}")
        return sorted(confident, key=lambda t: t["firstSeen"])

    def recognizeWindow(self, start):
        result = json.loads(self.recognizer.recognize_by_file(str(self.audioPath), start))
        code = result["status"]["code"]
        if code == NO_RESULT:
            console.info(f"{start:>3} s  no result")
            return []
        if code != 0:
            raise RuntimeError(f"ACRCloud failed at {start}s: {code} {result['status']['msg']}")

        music = result["metadata"]["music"]
        console.info(
            f"{start:>3} s  " + " · ".join(f"{artistOf(m) or '?'} – {m['title']} ({m['score']})" for m in music))
        return music


def artistOf(hit):
    artists = hit.get("artists") or []
    return artists[0]["name"] if artists else None


def splitMashup(hit):
    # The mashup's own artist is the DJ who made it, not the artist of either part.
    parts = MASHUP_SEPARATOR.split(hit["title"])
    if len(parts) > 1:
        return [(BRACKETS.sub("", part).strip(), None) for part in parts]
    return [(hit["title"], artistOf(hit))]


def titleKey(title):
    title = FEATURING.sub("", VERSION_SUFFIX.sub("", BRACKETS.sub("", title)))
    words = [w for w in re.findall(r"\w+", title.lower()) if w not in VERSION_WORDS]
    return " ".join(words) or title.lower()


def displayTitle(title):
    title = re.sub(r'[\(\[][^ text][^ \(\)\[\]]*[\)\]]', '', title)
    title = re.sub(r'\([^)]*\)|\[[^\]]*\]', '', title)

    title = re.sub(r'\s+-\s+.*$', '', title)

    title = re.sub(r'\s+(?:feat\.?|featuring)\b.*$', '', title, flags=re.IGNORECASE)
    return title.strip()
