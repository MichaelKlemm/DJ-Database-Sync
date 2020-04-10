import csv
import plistlib
from typing import Dict, List, Tuple
from urllib.parse import unquote, urlparse

from fuzzywuzzy import fuzz

from djdbsync.utils.actions import ActionRegistry


class AppleMusicDatabase:
    APPLE_MUSIC_DB_HEADERS = [
        "Major Version",
        "Minor Version",
        "Date",
        "Application Version",
        "Features",
        "Show Content Ratings",
        "Music Folder",
        "Library Persistent ID",
    ]

    APPLE_MUSIC_DB_COLUMNS = [
        "Track ID",
        "Name",
        "Artist",
        "Album Artist",
        "Album",
        "Genre",
        "Kind",
        "Size",
        "Total Time",
        "Track Number",
        "Year",
        "BPM",
        "Date Modified",
        "Date Added",
        "Bit Rate",
        "Sample Rate",
        "Play Count",
        "Play Date",
        "Play Date UTC",
        "Skip Count",
        "Skip Date",
        "Normalization",
        "Persistent ID",
        "Track Type",
        "Track Count",
        "Location",
        "File Folder Count",
        "Library Folder Count",
        "Matched",
        "Sort Album",
        "Sort Name",
        "Sort Artist",
        "Sort Album Artist",
        "Disc Number",
        "Disc Count",
        "Comments",
        'Rating',
        'Album Rating Computed',
        'Album Rating',
        'Purchased',
        'Composer',
        'Sort Composer',
        'Compilation',
        "Work",
    ]

    class EnsureLoaded:
        def __call__(self, func):
            def _wrapper(func_self: 'AppleMusicDatabase', *args, **kwargs):
                if not AppleMusicDatabase.is_loaded.__get__(func_self, AppleMusicDatabase)():
                    AppleMusicDatabase.load.__get__(func_self, AppleMusicDatabase)()
                return func.__get__(func_self)(*args, **kwargs)
            return _wrapper

    def __init__(self, db_file: str):
        self.db_file = db_file
        self.data: Dict[str, object] = None

    def is_loaded(self) -> bool:
        return self.data is not None

    def load(self):
        if self.is_loaded():
            raise RuntimeError("Apple DB loaded twice")
        with open(self.db_file, 'rb') as file:
            self.data = plistlib.load(file)

    @EnsureLoaded()
    def get_db_header(self) -> Dict[str, object]:
        return {key: self.data[key] for key in self.data if key in AppleMusicDatabase.APPLE_MUSIC_DB_HEADERS}

    @EnsureLoaded()
    def get_db_tracks(self) -> Dict[str, Dict[str, object]]:
        return self.data.get("Tracks", {})

    @EnsureLoaded()
    def get_db_playlists(self) -> List[Dict[str, object]]:
        return self.data.get("Playlists", [])

    def __repr__(self):
        if self.is_loaded():
            hdr = self.get_db_header()
            return "Database {} (Date {} / APP-Version {} / DB-Version: {} / {} Tracks / {} Playlists)".format(
                hdr.get("Music Folder", "unknown"),
                hdr.get("Date", "unknown"),
                hdr.get("Application Version", "unknows"),
                "{}.{}".format(hdr.get("Major Version", 0), hdr.get("Minor Version", 0)),
                len(self.get_db_tracks()),
                len(self.get_db_playlists()),
            )
        return ""

    def get_db_track_locations(self) -> Dict[int, str]:
        return {
            int(i): unquote(urlparse(j["Location"]).path)
            for i, j in self.get_db_tracks().items()
            if "Location" in j
        }

    def get_all_playlists(self) -> Dict[str, List[int]]:
        return {i["Name"]: list(int(j["Track ID"]) for j in i["Playlist Items"]) for i in self.get_db_playlists()}

    def export_database(self, export_target: str = "print"):
        if export_target == "print":
            print("\n".join([repr(i) for i in self.data.get("Tracks", {}).values()]))
        elif export_target.lower().endswith(".csv"):
            with open(export_target, 'w+') as file:
                out = csv.DictWriter(file, AppleMusicDatabase.APPLE_MUSIC_DB_COLUMNS)
                for track in self.get_db_tracks().values():
                    out.writerow(track)

    @ActionRegistry.register_command('export-itunes')
    def export_database_cmd(self, export_target: str = "print"):
        self.export_database(export_target)

    def find_track(self, artist: str, title: str, accuracy: int = 70, limit: int = 1) -> Dict[int, object]:
        results: List[Tuple[int, int, object]] = list()
        target_ratio = accuracy * accuracy
        for track_id, track in self.get_db_tracks().items():
            ratio = fuzz.partial_ratio(artist, track.get("Artist", ""))
            ratio *= fuzz.partial_ratio(title, track.get("Name", ""))
            if ratio >= target_ratio:
                results.append(tuple((ratio, track_id, track)))

        results_sorted = sorted(results, key=lambda i: (100*100) - i[0])
        return {int(i[1]): i[2] for _, i in zip(range(limit), results_sorted)}
