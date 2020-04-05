import csv
import plistlib
from typing import Dict, List
from urllib.parse import unquote, urlparse

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

    class RaiseOnDataNotLoaded:

        def __init__(self, func: callable):
            self.func = func

        def __call__(self, obj: 'AppleMusicDatabase', *args, **kwargs):
            if not obj.data:
                raise LookupError("Apple DB requires to be loaded first. Use load()")
            return self.func.__get__(obj)(*args, **kwargs)

    def __init__(self, dbfile: str):
        self.dbfile = dbfile
        self.data = None

    def load(self):
        if self.data:
            raise RuntimeError("Apple DB loaded twice")
        with open(self.dbfile, 'r+b') as file:
            self.data = plistlib.load(file)

    @RaiseOnDataNotLoaded
    def get_db_header(self) -> Dict[str, object]:
        return {key: self.data[key] for key in self.data if key in AppleMusicDatabase.APPLE_MUSIC_DB_HEADERS}

    @RaiseOnDataNotLoaded
    def get_db_tracks(self) -> Dict[str, Dict[str, object]]:
        return self.data.get("Tracks", {})

    @RaiseOnDataNotLoaded
    def get_db_playlists(self) -> List[Dict[str, object]]:
        return self.data.get("Playlists", [])

    def __repr__(self):
        hdr = self.get_db_header()
        return "Database {} (Date {} / APP-Version {} / DB-Version: {} / {} Tracks / {} Playlists)".format(
            hdr.get("Music Folder", "unknown"),
            hdr.get("Date", "unknown"),
            hdr.get("Application Version", "unknows"),
            "{}.{}".format(hdr.get("Major Version", 0), hdr.get("Minor Version", 0)),
            len(self.get_db_tracks()),
            len(self.get_db_playlists()),
        )

    def get_db_track_locations(self) -> Dict[int, str]:
        return {
            i: unquote(urlparse(j["Location"]).path)
            for i, j in self.get_db_tracks().items()
            if "Location" in j
        }

    def get_all_playlists(self):
        return {i["Name"]: list(j["Track ID"] for j in i["Playlist Items"]) for i in self.get_all_playlists()}

    @ActionRegistry.register_command('export-itunes')
    def export_database(self, export_target: str = "print"):  # "apple-db.csv"):
        self.load()
        if export_target == "print":
            print("\n".join([repr(i) for i in self.data.get("Tracks", {}).values()]))
        elif export_target.lower().endswith(".csv"):
            with open(export_target, 'w+') as file:
                out = csv.DictWriter(file, AppleMusicDatabase.APPLE_MUSIC_DB_COLUMNS)
                for track in self.data.get("Tracks", {}).values():
                    out.writerow(track)

    @staticmethod
    def _string_match(str1: str, str2: str) -> int:
        if str1 == str2:
            return 100
        str1 = str1.lower()
        str2 = str2.lower()
        if str1 == str2:
            return 95
        if str1.startswith(str2) or str2.startswith(str1):
            return 90
        words = str1.split(' ')
        result = 0
        for i in words:
            if i in str2:
                result += 1
        return result * (90 / len(words))

    def find_track(self, artist: str, _title: str, accuracy: int = 70) -> List[int]:
        results = []
        self.load()
        for track_id, track_info in self.data.get("Tracks", {}).items():
            artist_match = AppleMusicDatabase._string_match(artist, track_info['Artist'])
            title_match = AppleMusicDatabase._string_match(artist, track_info['Name'])
            if (artist_match * title_match) > (accuracy * accuracy):
                results.append(track_id)
        return results