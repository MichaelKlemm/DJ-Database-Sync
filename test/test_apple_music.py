from unittest import TestCase, mock
import datetime
import random
import tempfile

from djdbsync.tools.apple_music import AppleMusicDatabase

import mocks.mock_plistlib


PARSED_MEDIATHEK_SIMPLE = {
    'Major Version': 1, 'Minor Version': 1, 'Date': datetime.datetime(2020, 3, 27, 21, 8, 34),
    'Application Version': '1.0.3.1', 'Features': 5, 'Show Content Ratings': True,
    'Music Folder': 'file:///Users/michael/Music/', 'Library Persistent ID': '401B0C4DC15535A1', 'Tracks': {
        '11158': {'Track ID': 11158, 'Name': 'Teenage Dirtbag', 'Artist': 'Wheatus', 'Album Artist': 'Wheatus',
                  'Album': 'Teenage Dirtbag', 'Genre': 'Pop/Rock', 'Kind': 'AAC-Audiodatei',
                  'Size': 9729450, 'Total Time': 241840, 'Track Number': 1, 'Year': 2000, 'BPM': 95,
                  'Date Modified': datetime.datetime(2020, 3, 25, 19, 49, 57),
                  'Date Added': datetime.datetime(2019, 12, 9, 21, 13, 38), 'Bit Rate': 256, 'Sample Rate': 44100,
                  'Play Count': 1, 'Play Date': 3658775558, 'Play Date UTC': datetime.datetime(2019, 12, 9, 21, 32, 38),
                  'Skip Count': 3, 'Skip Date': datetime.datetime(2020, 3, 24, 22, 3, 27), 'Normalization': 8374,
                  'Persistent ID': '1234567890ABCDEF', 'Track Type': 'File',
                  'Location': 'file:///Users/michael/Music/Music/Wheatus/Teenage%20Dirtbag/01%20Teenage%20Dirtbag.m4a',
                  'File Folder Count': 5, 'Library Folder Count': 1}}, 'Playlists': [
        {'Name': 'Mediathek', 'Description': '', 'Master': True, 'Playlist ID': 64,
         'Playlist Persistent ID': '0000000000000005', 'Visible': False, 'All Items': True,
         'Playlist Items': [{'Track ID': 11158}]}]
}


class TestAppleMusicDatabase(TestCase):

    def __init__(self, *args, **kwargs):
        self.test_obj = None

        self.open_file_patch = None
        self.open_file = None

        self.plist_load_patch = None
        self.plist_load = None

        super(TestAppleMusicDatabase, self).__init__(*args, **kwargs)

    def setUp(self) -> None:
        self.open_file_patch = mock.patch('builtins.open', new_callable=mock.mock_open, read_data=b"")
        self.open_file = self.open_file_patch.start()

        self.plist_load_patch = mock.patch("plistlib.load", new_callable=mocks.mock_plistlib.load, data=PARSED_MEDIATHEK_SIMPLE.copy())
        self.plist_load = self.plist_load_patch.start()

        self.test_obj = AppleMusicDatabase(f"../examples/TestMediathek-{ random.randint(100000, 999999) }.xml")
        self.assertIsNone(self.test_obj.data)
        super(TestAppleMusicDatabase, self).setUp()

    def tearDown(self) -> None:
        try:
            self.open_file_patch.stop()
        except:
            pass
        self.open_file = None
        self.plist_load_patch.stop()
        self.plist_load = None
        del self.test_obj
        self.test_obj = None
        super(TestAppleMusicDatabase, self).tearDown()

    def test_load_once(self):
        self.assertIsNone(self.test_obj.data, "Unexpected initialized object")
        self.test_obj.load()
        self.assertIsNotNone(self.test_obj.data, "No data loaded")
        self.assertIsInstance(self.test_obj.data, dict)
        self.open_file.assert_called_once_with(self.test_obj.db_file, "rb")
        self.plist_load.assert_called_once_with(self.open_file.return_value)

    def test_load_twice(self):
        self.test_obj.load()
        self.assertIsNotNone(self.test_obj.data, "No data loaded")

        self.assertIsNotNone(self.test_obj.data, "Expected initialized object")
        self.assertRaises(RuntimeError, self.test_obj.load)

        self.open_file.assert_called_once()
        self.plist_load.assert_called_once()

    def test_to_str_not_loaded(self):
        str = repr(self.test_obj)
        self.assertEqual(str, "")

    def test_to_str_loaded(self):
        self.test_obj.load()
        str = repr(self.test_obj)
        self.assertEqual(str, 'Database file:///Users/michael/Music/ (Date 2020-03-27 21:08:34 / APP-Version 1.0.3.1 / DB-Version: 1.1 / 1 Tracks / 1 Playlists)')

    def test_get_db_header(self):
        hdr = self.test_obj.get_db_header()
        self.assertIsNotNone(hdr)
        self.assertIsInstance(hdr, dict)

    def test_get_db_tracks(self):
        tracks = self.test_obj.get_db_tracks()
        self.assertIsNotNone(tracks)
        self.assertIsInstance(tracks, dict)
        self.assertEqual(len(tracks), 1)

    def test_get_db_playlists(self):
        lists = self.test_obj.get_db_playlists()
        self.assertIsNotNone(lists)
        self.assertIsInstance(lists, list)
        self.assertEqual(len(lists), 1)
        self.assertIsInstance(lists[0], dict)

    def test_get_db_track_locations(self):
        tracks = self.test_obj.get_db_track_locations()
        self.assertDictEqual(tracks, {11158: '/Users/michael/Music/Music/Wheatus/Teenage Dirtbag/01 Teenage Dirtbag.m4a'})

    def test_get_all_playlists(self):
        lists = self.test_obj.get_all_playlists()
        self.assertDictEqual(lists, {'Mediathek': [11158]})

    def test_export_database(self):
        self.test_obj.load()
        self.open_file_patch.stop()

        _, tmp_csv_file = tempfile.mkstemp(suffix=".csv", prefix="TestMediathek-export-")
        self.test_obj.export_database(tmp_csv_file)
        with open(tmp_csv_file, 'r') as result:
            self.assertEqual(result.read(),
                             "11158,Teenage Dirtbag,Wheatus,Wheatus,Teenage Dirtbag,Pop/Rock,AAC-Audiodatei,"
                             "9729450,241840,1,2000,95,2020-03-25 19:49:57,2019-12-09 21:13:38,256,44100,1,3658775558,"
                             "2019-12-09 21:32:38,3,2020-03-24 22:03:27,8374,1234567890ABCDEF,File,,"
                             "file:///Users/michael/Music/Music/Wheatus/Teenage%20Dirtbag/01%20Teenage%20Dirtbag.m4a,"
                             "5,1,,,,,,,,,,,,,,,,\n")

    def test_find_track(self):
        result = self.test_obj.find_track(title="Teenage", artist="Wheatus")
        self.assertIsNotNone(result)
        self.assertIsInstance(result, dict)
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[11158], dict)
