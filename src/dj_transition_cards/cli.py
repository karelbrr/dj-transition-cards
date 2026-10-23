import argparse
from pathlib import Path

from dj_transition_cards import console
from dj_transition_cards.analyzer import Analyzer
from dj_transition_cards.card_renderer import CardRenderer
from dj_transition_cards.cover_downloader import CoverDownloader
from dj_transition_cards.extractor import Extractor
from dj_transition_cards.project import Project
from dj_transition_cards.video_renderer import VideoRenderer

VIDEO_SUFFIXES = {".mov", ".mp4", ".m4v"}
EXPORT_SUFFIX = "-tiktok.mp4"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="dj-cards",
        description="Adds the covers and titles of the two tracks of each DJ transition clip.",
    )
    parser.add_argument("path", type=Path, help="a clip, or a folder whose clips are all processed")
    parser.add_argument(
        "--overlay",
        type=float,
        default=5.0,
        help="seconds the covers stay on screen from the start of the clip (default: 5)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="render again clips whose export already exists (the tracks still come from pair.json)",
    )
    args = parser.parse_args(argv)

    clips = findClips(args.path)
    if not clips:
        parser.error(f"no clip ({', '.join(sorted(VIDEO_SUFFIXES))}) at {args.path}")

    results = []
    for number, clip in enumerate(clips, start=1):
        console.step("Clip", f"{number}/{len(clips)}  {clip.name}")
        # One clip's failure is reported and the batch goes on.
        try:
            results.append((clip, *processClip(clip, args.overlay, args.force)))
        except Exception as e:
            console.error(f"{type(e).__name__}: {e}")
            results.append((clip, "failed", str(e)))

    return summarize(results)


def findClips(path):
    # Only the folder itself, not its subfolders: the project folders hold the exports.
    if path.is_file():
        return [path]
    if not path.is_dir():
        return []
    return sorted(p for p in path.iterdir()
                  if p.is_file() and p.suffix.lower() in VIDEO_SUFFIXES and not p.name.endswith(EXPORT_SUFFIX))


def processClip(videoPath, overlay, force):
    exportPath = videoPath.parent / videoPath.stem / f"{videoPath.stem}{EXPORT_SUFFIX}"
    if exportPath.exists() and not force:
        console.info(f"already exported to {exportPath.parent.name}/{exportPath.name}, skipped (--force redoes it)")
        return "skipped", ""

    project = Project(videoPath)
    pairName = f"{project.folderPath.name}/{project.pairPath.name}"

    # pair.json is paid for once: a later run, or one after a correction by hand, reads it instead.
    tracks = project.loadPair()
    if tracks is None:
        extractor = Extractor(videoPath)
        audioPath = extractor.extract_audio()
        if audioPath is None:
            raise RuntimeError("audio extraction failed")
        audioPath = project.moveMusic(audioPath)
        tracks = Analyzer(audioPath).analyzeAll(extractor.duration)
        project.savePair(tracks)
    else:
        console.step("Pair", f"from {pairName}, delete it to recognize again")

    console.step("Result")
    for label, track in zip("ABCDEFGH", tracks):
        line = f"{label}  {track['artist'] or '?'} – {track['title'] or '?'}"
        if track.get("windows"):
            line += f"   score {track.get('score')}, windows {', '.join(f'{w} s' for w in track['windows'])}"
        console.info(line)
    if len(tracks) != 2 or not all(track["title"] for track in tracks):
        return "needs fix", f"edit {pairName} to two tracks with a title and run again"

    console.step("Covers", "Deezer, iTunes fallback")
    coverDownloader = CoverDownloader()
    tracks = [coverDownloader.download(track, project.folderPath / "covers" / f"{label}.jpg")
              for label, track in zip("ab", tracks)]

    console.step("Card")
    if CardRenderer().render(tracks, project.cardPath) is None:
        return "needs fix", f"missing cover, put it into {project.folderPath.name}/covers and run again"

    console.step("Render")
    VideoRenderer().render(videoPath, project.cardPath, exportPath, overlay)
    return "exported", str(exportPath)


def summarize(results):
    console.step("Summary")
    for clip, status, detail in results:
        line = f"{clip.name}: {status}" + (f", {detail}" if detail else "")
        if status == "exported":
            console.done(line)
        elif status == "skipped":
            console.info(line)
        elif status == "needs fix":
            console.warn(line)
        else:
            console.error(line)

    counts = {}
    for _, status, _ in results:
        counts[status] = counts.get(status, 0) + 1
    console.info(" · ".join(f"{count} {status}" for status, count in counts.items()))
    return 0 if all(status in ("exported", "skipped") for _, status, _ in results) else 1
