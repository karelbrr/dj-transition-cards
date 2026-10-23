from pathlib import Path

from moviepy import CompositeVideoClip, ImageClip, VideoFileClip, vfx

from dj_transition_cards import console

WIDTH, HEIGHT = 1080, 1920
FPS = 30
FADE_OUT = 0.5  # seconds the card takes to disappear at the end of the overlay


class VideoRenderer:
    def render(self, videoPath, cardPath, destination, overlay=5):
        if not Path(cardPath).is_file():
            console.warn(f"no card at {cardPath}, video not rendered")
            return None

        destination = Path(destination)
        video = VideoFileClip(str(videoPath))
        try:
            # Fill the 9:16 frame and crop what sticks out: a landscape clip loses its sides instead of getting bars.
            scale = max(WIDTH / video.w, HEIGHT / video.h)
            frame = video.resized(scale)
            frame = frame.cropped(x_center=frame.w / 2, y_center=frame.h / 2, width=WIDTH, height=HEIGHT)
            console.info(f"{video.w}×{video.h} → {WIDTH}×{HEIGHT}, card for the first {overlay} s")

            card = (ImageClip(str(cardPath))
                    .with_duration(min(overlay, video.duration))
                    .with_effects([vfx.CrossFadeOut(FADE_OUT)]))

            # Not use_bgclip: moviepy 2.2.1 then leaves the background out of the duration and the audio, so the
            # export ended with the card and was silent. A black background keeps the composite without a mask.
            final = CompositeVideoClip([frame, card.with_position((0, 0))], size=(WIDTH, HEIGHT), bg_color=(0, 0, 0))
            # No -pix_fmt here: moviepy appends its own for libx264 after ffmpeg_params, and ffmpeg falls back
            # to yuv420p, which every phone plays.
            final.write_videofile(str(destination), fps=FPS, codec="libx264", preset="slow",
                                  audio_codec="aac", audio_bitrate="192k",
                                  ffmpeg_params=["-crf", "18", "-movflags", "+faststart"])
        finally:
            video.close()

        console.done(f"exported to {destination.parent.name}/{destination.name}")
        return destination
