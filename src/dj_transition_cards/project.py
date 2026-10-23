import json
from pathlib import Path

from dj_transition_cards import console
from dj_transition_cards.analyzer import displayTitle

PAIR_FIELDS = ("artist", "title", "displayTitle", "score", "firstSeen", "windows")


class Project:
    def __init__(self, videoPath):
        videoFile = Path(videoPath)

        desktopPath = Path(videoPath).parent

        folderName = videoFile.stem

        newFolder = desktopPath / folderName

        console.step("Project", str(newFolder))
        if newFolder.exists():
            console.info("folder exists, reusing it")
        newFolder.mkdir(exist_ok=True)

        self.folderPath = newFolder
        self.cardPath = self.folderPath / "card.png"
        self.pairPath = self.folderPath / "pair.json"

    def moveMusic(self, audioPath):
        audio_file = Path(audioPath)

        destination = self.folderPath / audio_file.name

        audio_file.rename(destination)
        console.done(f"audio moved to {self.folderPath.name}/{destination.name}")

        return destination

    def loadPair(self):
        # The tracks as recognized or as corrected by hand; None when the clip was never recognized.
        if not self.pairPath.is_file():
            return None
        try:
            pair = json.loads(self.pairPath.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise ValueError(f"{self.pairPath.name} is not valid JSON: {e}") from e
        if not isinstance(pair, dict) or not all(isinstance(track, dict) for track in pair.values()):
            raise ValueError(f'{self.pairPath.name} must be {{"a": {{…}}, "b": {{…}}}}')

        tracks = []
        for track in pair.values():
            track = {**track, "artist": track.get("artist") or None, "title": track.get("title") or ""}
            # A track filled in by hand needs only its title; the card text follows from it.
            if not track.get("displayTitle"):
                track["displayTitle"] = displayTitle(track["title"])
            tracks.append(track)
        return tracks

    def savePair(self, tracks):
        # Fewer than two tracks get an empty slot to fill in by hand, more than two stay for the user to delete.
        slots = [{field: track.get(field) for field in PAIR_FIELDS} for track in tracks]
        while len(slots) < 2:
            slots.append({"artist": None, "title": "", "displayTitle": ""})
        pair = dict(zip("abcdefgh", slots))
        self.pairPath.write_text(json.dumps(pair, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        console.done(f"saved to {self.folderPath.name}/{self.pairPath.name}")
