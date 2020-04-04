import csv


class FixedExcel(csv.Dialect):
    delimiter = ';'
    quotechar = '"'
    doublequote = True
    skipinitialspace = False
    lineterminator = '\r\n'
    quoting = csv.QUOTE_NONNUMERIC


class PlaylistWriter(object):

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
        from djdbsync.tools.Serato import SeratoCrateTrackInfo
        if isinstance(obj, SeratoCrateTrackInfo):
            self.writer.append_track(obj.path)


class DatabaseCsvWriterVisitor(Visitor):

    def __init__(self, writer: 'DatabaseCsvWriter'):
        self.writer = writer

    def accept(self, obj: Visitable):
        from djdbsync.tools.Serato import SeratoCrateTrackInfo
        if isinstance(obj, SeratoCrateTrackInfo):
            self.writer.append_track(path=obj.path, **obj.data)


class DatabaseCsvWriter(object):

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
        self.fd = None
        self.writer = None

    def __enter__(self):
        self.fd = open(self.output_file, 'w+')
        self.writer = csv.DictWriter(self.fd, fieldnames=DatabaseCsvWriter.COLUMNS,
                                     extrasaction="ignore", dialect="excel-fixed")
        return DatabaseCsvWriterVisitor(self)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.fd.close()

    def append_track(self, **data):
        if not self.fd or not self.writer:
            raise FileNotFoundError("File {} not opened".format(self.output_file))
        try:
            self.writer.writerow(data)
        except Exception as e:
            print(e)
            raise e
