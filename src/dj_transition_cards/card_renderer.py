from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

from dj_transition_cards import console

SIZE = (1080, 1920)
COVER = 400  # strana coveru
FRAME = 12  # tloušťka černého rámečku
TOP = 360  # horní okraj coverů
COVER_X = (70, 610)  # levý okraj A a B
TITLE_GAP = 30  # mezera mezi coverem a názvem
TITLE_WIDTH = 440  # max. šířka názvu
# The font shipped with the package first, so the card looks the same everywhere, then a bold system font.
FONT_CANDIDATES = (
    Path(__file__).parent / "assets" / "fonts" / "Montserrat-Bold.ttf",
    Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
    Path("C:/Windows/Fonts/arialbd.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
)
FONT_PATH = next((path for path in FONT_CANDIDATES if path.is_file()), None)
TITLE_SIZE = 48
MIN_TITLE_SIZE = 32
X_SIZE = 72


class CardRenderer:
    def __init__(self):
        pass

    def render(self, tracks, destination):
        for track in tracks:
            coverPath = track.get("coverPath")
            if coverPath is None or not Path(coverPath).is_file():
                console.warn(f"missing cover for {track['artist'] or '?'} – {track['title']}, card not drawn")
                return None

        if FONT_PATH is None:
            console.warn("no bold TrueType font found, titles use Pillow's default font")

        canvas = Image.new("RGBA", SIZE, (0, 0, 0, 0))
        draw = ImageDraw.Draw(canvas)

        for track, x in zip(tracks, COVER_X):
            self.drawCover(canvas, track["coverPath"], x)
            self.drawTitle(draw, track["displayTitle"], x + COVER // 2)

        xFont = loadFont(X_SIZE)
        draw.text((SIZE[0] // 2, TOP + COVER // 2), "X", font=xFont, anchor="mm",
                  fill="white", stroke_width=4, stroke_fill="black")

        canvas.save(destination)
        console.done(f"card saved to {Path(destination).parent.name}/{Path(destination).name}")
        return destination

    def drawCover(self, canvas, coverPath, x):
        # Covers come in CMYK or with a palette too; fit crops to a square without stretching.
        cover = ImageOps.fit(Image.open(coverPath).convert("RGB"), (COVER, COVER))
        ImageDraw.Draw(canvas).rectangle(
            [x - FRAME, TOP - FRAME, x + COVER + FRAME, TOP + COVER + FRAME], fill="black")
        canvas.paste(cover, (x, TOP))

    def drawTitle(self, draw, title, centerX):
        # The largest font at which the title fits in one or two lines; below the minimum it is drawn anyway.
        words = title.split()
        for size in range(TITLE_SIZE, MIN_TITLE_SIZE - 1, -4):
            font = loadFont(size)
            text, width = self.layoutTitle(draw, words, font)
            if width <= TITLE_WIDTH:
                break

        draw.multiline_text((centerX, TOP + COVER + FRAME + TITLE_GAP), text, font=font, anchor="ma",
                            align="center", fill="white", stroke_width=4, stroke_fill="black")

    def layoutTitle(self, draw, words, font):
        # One line when it fits, otherwise the break whose longer line is the shortest.
        line = " ".join(words)
        width = draw.textlength(line, font=font)
        if width <= TITLE_WIDTH or len(words) < 2:
            return line, width

        best = None
        for i in range(1, len(words)):
            lines = (" ".join(words[:i]), " ".join(words[i:]))
            widest = max(draw.textlength(part, font=font) for part in lines)
            if best is None or widest < best[1]:
                best = ("\n".join(lines), widest)
        return best


def loadFont(size):
    if FONT_PATH is None:
        return ImageFont.load_default(size)
    return ImageFont.truetype(str(FONT_PATH), size)
