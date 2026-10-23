from pathlib import Path
from moviepy.video.io.VideoFileClip import VideoFileClip

from dj_transition_cards import console


class Extractor:
    def __init__(self, videoPath):
        # Convert the input string into a Path object
        self.videoPath = Path(videoPath)

        console.step("Video", str(self.videoPath.resolve()))

        if self.videoPath.is_dir():
            console.error("this is a folder, expected a video file")
        elif not self.videoPath.is_file():
            console.error("the path does not exist")

    def extract_audio(self):
        # 1. Safety check: make sure the file actually exists
        if not self.videoPath.is_file():
            console.error(f"video file not found: {self.videoPath.resolve()}")
            return

        # 2. Dynamically create the output path (e.g., video.mp4 -> video.mp3)
        audioPath = self.videoPath.with_suffix(".mp3")

        console.step("Audio", f"{self.videoPath.name} → {audioPath.name}")

        try:
            # 3. Load the video file (moviepy expects string paths)
            video = VideoFileClip(str(self.videoPath))

            # 4. Extract and write the audio track to a file
            # 'logger=None' turns off the messy progress bar text in the console
            video.audio.write_audiofile(str(audioPath), logger=None)
            self.duration = video.duration

            # 5. Clean up system resources and close file locks
            video.close()
            console.done(f"{self.duration:.1f} s of audio")

            return audioPath

        except Exception as e:
            console.error(f"audio extraction failed: {e}")
