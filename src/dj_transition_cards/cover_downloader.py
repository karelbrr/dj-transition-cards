from pathlib import Path

import httpx

from dj_transition_cards import console
from dj_transition_cards.analyzer import titleKey

DEEZER_SEARCH = "https://api.deezer.com/search"
ITUNES_SEARCH = "https://itunes.apple.com/search"
NOT_ORIGINAL_ARTISTS = ("karaoke", "tribute", "cover", "made famous", "originally performed")


class CoverDownloader:
    def __init__(self):
        self.client = httpx.Client(timeout=10)

    def download(self, track, destination):
        # An existing file wins, so a cover put into the folder by hand is never overwritten.
        destination = Path(destination)
        name = f"{track['artist'] or '?'} – {track['title']}"
        if destination.exists():
            console.info(f"{name} → {destination.name} already there, kept")
            return {**track, "coverPath": destination}

        try:
            found = self.searchDeezer(track) or self.searchItunes(track)
            if found is None:
                console.warn(f"{name}: no cover on Deezer or iTunes")
                return track
            destination.parent.mkdir(parents=True, exist_ok=True)
            self.fetch(found["coverUrl"], destination)
        except httpx.HTTPError as e:
            console.error(f"{name}: {e}")
            return track

        console.info(f"{found['artist']} – {found['title']} → {found['album']} ({found['source']})")
        return {
            **track,
            "artist": track["artist"] or found["artist"],
            "album": found["album"],
            "coverSource": found["source"],
            "coverPath": destination,
        }

    def searchDeezer(self, track):
        title = track["title"].replace('"', "")
        query = f'track:"{title}"'
        if track["artist"]:
            artist = track["artist"].replace('"', "")
            query = f'artist:"{artist}" {query}'
        response = self.client.get(DEEZER_SEARCH, params={"q": query, "limit": 25})
        response.raise_for_status()
        body = response.json()
        # Deezer answers its own errors (a quota, a bad query) with a 200 and an "error" object.
        if "error" in body:
            console.warn(f"Deezer: {body['error'].get('message', body['error'])}")
            return None

        candidates = [
            {
                "artist": item["artist"]["name"],
                "title": item["title"],
                "album": item["album"]["title"],
                "coverUrl": item["album"]["cover_xl"],
                "rank": item.get("rank", 0),
                "source": "deezer",
            }
            for item in body.get("data", [])
            if item.get("album", {}).get("cover_xl")
        ]
        return self.pickBest(track, candidates)

    def searchItunes(self, track):
        term = f"{track['artist']} {track['title']}" if track["artist"] else track["title"]
        response = self.client.get(ITUNES_SEARCH,
                                   params={"term": term, "media": "music", "entity": "song", "limit": 10})
        response.raise_for_status()

        candidates = [
            {
                "artist": item["artistName"],
                "title": item["trackName"],
                "album": item.get("collectionName"),
                "coverUrl": item["artworkUrl100"].replace("100x100bb", "1000x1000bb"),
                "rank": None,
                "source": "itunes",
            }
            for item in response.json().get("results", [])
            if item.get("kind") == "song" and item.get("artworkUrl100")
        ]
        return self.pickBest(track, candidates)

    def pickBest(self, track, candidates):
        # A known artist must match: a wrong cover is worse than none, which the folder can fix by hand.
        key = titleKey(track["title"])
        artist = (track["artist"] or "").lower()
        matching = [
            c for c in candidates
            if titleKey(c["title"]) == key
               and not any(word in c["artist"].lower() for word in NOT_ORIGINAL_ARTISTS)
               and artist in c["artist"].lower()
        ]
        if not matching:
            return None
        # max keeps the first of equal ranks, so iTunes (no rank) gets its own relevance order.
        return max(matching, key=lambda c: c["rank"] or 0)

    def fetch(self, url, destination):
        # Written under a temporary name first: a half-written file would count as a finished cover next run.
        response = self.client.get(url, follow_redirects=True)
        response.raise_for_status()
        partial = destination.with_name(destination.name + ".part")
        partial.write_bytes(response.content)
        partial.replace(destination)
