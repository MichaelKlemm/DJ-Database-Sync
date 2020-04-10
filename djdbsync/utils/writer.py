import csv

from djdbsync.utils.helper import Visitor, Visitable


class FixedExcel(csv.Dialect):
    delimiter = ';'
    quotechar = '"'
    doublequote = True
    skipinitialspace = False
    lineterminator = '\r\n'
    quoting = csv.QUOTE_NONNUMERIC


class PlaylistWriter:

    def __init__(self, output_file: str):
        self.output_file = output_file
        self.file_handle = None

    def __enter__(self):
        self.file_handle = open(self.output_file, 'w+')
        return PlaylistWriterVisitor(self)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.file_handle.close()

    def append_track(self, path: str):
        if not self.file_handle:
            raise FileNotFoundError("File {} not opened".format(self.output_file))
        self.file_handle.write(path)
        self.file_handle.write("\n")


class PlaylistWriterVisitor(Visitor):

    def __init__(self, writer: PlaylistWriter):
        self.writer = writer

    def accept(self, obj: Visitable):
        # Replace for forward declaration. Avoid cyclic dependency
        # pylint: disable=import-outside-toplevel, cyclic-import
        from djdbsync.tools.serato import SeratoCrateTrackInfo
        if isinstance(obj, SeratoCrateTrackInfo):
            self.writer.append_track(obj.path)


class DatabaseCsvWriterVisitor(Visitor):

    def __init__(self, writer: 'DatabaseCsvWriter'):
        self.writer = writer

    def accept(self, obj: Visitable):
        # Replace for forward declaration. Avoid cyclic dependency
        # pylint: disable=import-outside-toplevel, cyclic-import
        from djdbsync.tools.serato import SeratoCrateTrackInfo
        if isinstance(obj, SeratoCrateTrackInfo):
            self.writer.append_track(path=obj.path, **obj.data)


class DatabaseCsvWriter:

    COLUMNS = [
        "artist",
        "title",
        "album",
        "genre",
        "duration",
        "path",
        "filetype",
        "resolution",
        "size",
        "sample_rate",
        "beats_per_minute",
        "tone_key",
        "label",
        "year",
        "uuid",
        "track_added",
    ]

    def __init__(self, output_file: str):
        self.output_file = output_file
        self.file = None
        self.writer = None

    def __enter__(self):
        self.file = open(self.output_file, 'w+')
        self.writer = csv.DictWriter(self.file, fieldnames=DatabaseCsvWriter.COLUMNS,
                                     extrasaction="ignore", dialect="excel-fixed")
        return DatabaseCsvWriterVisitor(self)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.file.close()

    def append_track(self, **data):
        if not self.file or not self.writer:
            raise FileNotFoundError("File {} not opened".format(self.output_file))
        try:
            self.writer.writerow(data)
        except Exception as err:
            print(err)
            raise err
