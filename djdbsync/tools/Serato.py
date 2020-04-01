import mmap
import os
import struct
from abc import abstractmethod
from typing import Tuple, List, Iterable

from djdbsync.utils.ActionRegistry import ActionRegistry
from djdbsync.utils.Writer import Visitable, Visitor, PlaylistWriter, DatabaseCsvWriter


class SeratoSyncError(Exception):
    pass


class SeratoSyncError_SongIdAlreadyExists(SeratoSyncError):
    pass


class SeratoSyncError_SongIdChanged(SeratoSyncError):
    pass


class SeratoSyncError_SongIdUnknows(SeratoSyncError):
    pass


class SeratoSongStorageFs(object):

    SSL_STORE_DIR_MOD = 0o755

    def __init__(self, root, dry_run: bool = False):
        self.root = os.path.abspath(root)
        self.dry_run = dry_run
        try:
            os.mkdir(root, SeratoSongStorageFs.SSL_STORE_DIR_MOD)
        except FileExistsError:
            pass
        else:
            print("Created new storage directory for Serato media files at {}".format(self.root))
        self.db = { os.path.splitext(i)[0]: i for i in os.listdir(self.root) }

    def add_song(self, id: int, path: str, update_existing: bool = False) -> str:
        path = os.path.normpath(path)
        filename = str(id) + os.path.splitext(path)[1]
        filepath = os.path.join(self.root, filename)
        if id in self.db:
            if self.db[id] != filename:
                raise SeratoSyncError_SongIdAlreadyExists()
            old_path = os.readlink(filepath)
            if path == old_path:
                return filepath
            if not update_existing:
                raise SeratoSyncError_SongIdChanged()
            print("Path of Song-ID {} has changed from {} to {}".format(id, old_path, path))
            if not self.dry_run:
                os.remove(filepath)

        if self.dry_run:
            print("Creating symlink from {} to {}".format(path, filepath))
        else:
            os.symlink(path, filepath)
        self.db[id] = filepath

    def get_file(self, id):
        if id in self.db:
            return self.db[id]
        raise SeratoSyncError_SongIdUnknows()


class SeratoBinFile(object):

    SSL_OBJ_HDR_ENCODING = 'utf-8'
    SSL_OBJ_STR_ENCODING = 'utf-16be'

    def __init__(self, root: str, binfile: str):
        self.dbfile = open(os.path.join(root, binfile), 'r+b')
        self.ssldb = mmap.mmap(self.dbfile.fileno(), 0)

    def read_bytes(self, num_bytes: int) -> bytes:
        return self.ssldb.read(num_bytes)

    def read_string(self, strlen: int, encoding: str = SSL_OBJ_STR_ENCODING) -> str:
        return self.read_bytes(strlen).decode(encoding)

    def read_uint32(self) -> int:
        return struct.unpack(">I", self.read_bytes(4))[0]

    def read_uint16(self) -> int:
        return struct.unpack(">H", self.read_bytes(2))[0]

    def read_uint8(self) -> int:
        return struct.unpack(">B", self.read_bytes(1))[0]

    def read_type_id(self) -> str:
        return self.read_bytes(4).decode(SeratoBinFile.SSL_OBJ_HDR_ENCODING)

    def read_object_header(self) -> Tuple[str, int, callable]:
        pos = self.ssldb.tell()
        def _reset():
            self.ssldb.seek(pos)

        hdr = self.read_type_id()
        size = self.read_uint32()

        return hdr, size, _reset

    def is_byte_left(self) -> bool:
        return self.ssldb.tell() < self.ssldb.size()

    def get_pos(self) -> int:
        return self.ssldb.tell()


class SeratoObject(Visitable):

    def __init__(self, hdr: str, data: object):
        self.hdr = hdr
        self.data = data

    def visit(self, obj: Visitor):
        obj.accept(self)

    def set(self, data: object):
        self.data = data

    def get(self) -> object:
        return self.data

    @classmethod
    @abstractmethod
    def create_from_bin(cls, data: SeratoBinFile, length: int) -> object:
        raise NotImplementedError("Method {} needs to be overwritten ")


class SeratoStringParam(SeratoObject):

    def __init__(self, typeid: str, value: str):
        super().__init__(typeid, value)

    @classmethod
    def create_from_bin(cls, data: SeratoBinFile, length: int) -> SeratoObject:
        name, length, reset = data.read_object_header()
        return cls(name, data.read_string(length))


class SeratoCrateSortInfo(SeratoObject):

    def __init__(self, name: str, brev: bytes):
        self.name: str = name
        self.brev: bytes = brev
        super().__init__(name, str(brev))

    def __repr__(self):
        return "Sort:     {} / 0x{}".format(self.name, self.brev.hex())

    @classmethod
    def create_from_bin(cls, data: SeratoBinFile, length: int) -> SeratoObject:
        expected_end = data.get_pos() + length

        sort_column = None
        sort_brev = None

        while data.get_pos() < expected_end:
            name, length, reset = data.read_object_header()
            if name == "tvcn":
                sort_column = data.read_string(length)
            elif name == "brev":
                sort_brev = data.read_bytes(length)
            else:
                raise IndexError("Unknown type '{}' with size {} at position {} while parsing Serato SSL file".format(
                    name, length, data.get_pos()))
        return cls(sort_column, sort_brev)


class SeratoCrateColumnInfo(SeratoObject):

    def __init__(self, name: str, width: str):
        self.name = name
        self.width = width
        super().__init__(name, width)

    def __repr__(self):
        return "Column:   {} / {}".format(self.name, self.width)

    @classmethod
    def create_from_bin(cls, data: SeratoBinFile, length: int) -> SeratoObject:
        expected_end = data.get_pos() + length

        column_name = None
        column_width = None

        while data.get_pos() < expected_end:
            name, length, reset = data.read_object_header()
            if name == "tvcn":
                column_name = data.read_string(length)
            elif name == "tvcw":
                column_width = data.read_string(length)
            else:
                raise IndexError("Unknown type '{}' with size {} at position {} while parsing Serato SSL file".format(
                    name, length, data.get_pos()))
        return cls(column_name, column_width)


class SeratoCrateTrackInfo(SeratoObject):

    def __init__(self, path: str, *args, **kwargs):
        self.data = kwargs
        self.path = path
        super().__init__("Track", "")

    def __repr__(self):
        return "Track:    {}".format(self.path)

    @classmethod
    def create_from_bin(cls, data: SeratoBinFile, length: int) -> SeratoObject:
        expected_end = data.get_pos() + length

        path = None

        key_convert_tbl = {
            "ptrk": ("s", "path"), # Crate v1.0
            "pfil": ("s", "path"), # DB v2.0
            "ttyp": ("s", "filetype"),
            "tsng": ("s", "title"),
            "tart": ("s", "artist"),
            "talb": ("s", "album"),
            "tgen": ("s", "genre"),
            "tlen": ("s", "duration"),
            "tlbl": ("s", "label"),
            "tbit": ("s", "resolution"),
            "tsmp": ("s", "sample_rate"),
            "tbpm": ("s", "beats_per_minute"),
            "ttyr": ("s", "year"),
            "tkey": ("s", "tone_key"),
            "tiid": ("s", "uuid"),
            "tadd": ("s", "track_added"),
            "tcmp": ("s", "composition"),
            "tcor": ("s", "cor"),
            "tcom": ("s", "composition2"),
            "trmx": ("s", "remix?"),
            "tsiz": ("s", "size"),
            "uadd": ("u32", "ts_added"),
            "utkn": ("u32", "track_number"),
            "ulbl": ("u32", "label"),
            "utme": ("u32", "modified"),
            "udsc": ("u32", "dsc"),
            "utpc": ("u32", "play_count"),
            "ufsb": ("u32", "fsb"),
            "sbav": ("u16", "bav"),
            "bhrt": ("u8", "hrt"),
            "bmis": ("u8", "mis"),
            "bply": ("u8", "ply"),
            "blop": ("u8", "lop"),
            "bitu": ("u8", "itu"),
            "bovc": ("u8", "ovc"),
            "bcrt": ("u8", "crt"),
            "biro": ("u8", "iro"),
            "bwlb": ("u8", "wlb"),
            "bwll": ("u8", "wll"),
            "buns": ("u8", "uns"),
            "bbgl": ("u8", "bgl"),
            "bkrk": ("u8", "krk"),
        }
        values = {}

        while data.get_pos() < expected_end:
            name, length, reset = data.read_object_header()
            #if name == "ptrk":
            #    # TODO: Remove hard coded leading slash / this will not working on non UNIX machines
            #    path = "/" + data.read_string(length)
            type, lbl = key_convert_tbl.get(name, (None, None))
            if type == "s":
                values[lbl] = data.read_string(length)
            elif type == "u32" and length == 4:
                values[lbl] = data.read_uint32()
            elif type == "u16" and length == 2:
                values[lbl] = data.read_uint16()
            elif type == "u8"  and length == 1:
                values[lbl] = data.read_uint8()
            else:
                raise IndexError("Unknown type '{}' with size {} at position {} while parsing Serato SSL file".format(
                    name, length, data.get_pos()))
        values['path'] = '/' + values['path']
        return cls(**values)


class SeratorFile(Visitable):

    @abstractmethod
    def append_content(self, ssl_obj: SeratoObject):
        raise NotImplementedError("Method needs to be implemented")

    @abstractmethod
    def get_content(self):
        raise NotImplementedError("Method needs to be implemented")

    @classmethod
    @abstractmethod
    def create_from_bin(cls, data: SeratoBinFile) -> object:
        raise NotImplementedError("Method needs to be implemented")


class SeratoSslCrate(SeratorFile):

    def __init__(self):
        self.objects: List[SeratoObject] = []

    def append_content(self, ssl_obj: SeratoObject):
        self.objects.append(ssl_obj)

    def get_content(self):
        return self.objects

    def __repr__(self):
        return "\n".join([repr(i) for i in self.objects])

    def visit(self, obj: Visitor):
        obj.accept(self)
        for i in self.objects:
            i.visit(obj)

    @classmethod
    def create_from_bin(cls, data: SeratoBinFile) -> object:

        self = cls()

        recognized_objects = {
            "osrt": SeratoCrateSortInfo,
            "ovct": SeratoCrateColumnInfo,
            "otrk": SeratoCrateTrackInfo,
        }

        while(data.is_byte_left()):
            name, length, reset = data.read_object_header()
            obj_cls = recognized_objects.get(name, None)
            if not obj_cls:
                raise IndexError("Unknown type '{}' with size {} at position {} while parsing Serato SSL file".format(
                    name, length, data.get_pos()))
            self.append_content(obj_cls.create_from_bin(data, length))

        return self


class SeratoSslDatabase(SeratorFile):

    def __init__(self):
        self.objects: List[SeratoObject] = []

    def append_content(self, ssl_obj: SeratoObject):
        self.objects.append(ssl_obj)

    def get_content(self):
        return self.objects

    def __repr__(self):
        return "\n".join([repr(i) for i in self.objects])

    def visit(self, obj: Visitor):
        obj.accept(self)
        for i in self.objects:
            i.visit(obj)

    @classmethod
    def create_from_bin(cls, data: SeratoBinFile) -> object:

        self = cls()

        recognized_objects = {
            "osrt": SeratoCrateSortInfo,
            "ovct": SeratoCrateColumnInfo,
            "otrk": SeratoCrateTrackInfo,
        }

        while(data.is_byte_left()):
            name, length, reset = data.read_object_header()
            obj_cls = recognized_objects.get(name, None)
            if not obj_cls:
                raise IndexError("Unknown type '{}' with size {} at position {} while parsing Serato SSL file".format(
                    name, length, data.get_pos()))
            self.append_content(obj_cls.create_from_bin(data, length))

        return self


class SeratoFileHeader(SeratorFile):
    # TODO: Do we need this additional object header or would the StringParam sufficient?

    IDENTIFIER = 'vrsn'

    SSL_CLS_TABLE = {
        'Serato ScratchLive Crate': {
            '1.0': SeratoSslCrate,
        },
        'Serato Scratch LIVE Database': {
            '2.0': SeratoSslDatabase,
        },
    }

    def __init__(self, version: str, file_type: str):
        self.typeid = SeratoFileHeader.IDENTIFIER
        self.version = version
        self.file_type = file_type
        self.content = None

    def append_content(self, content: SeratorFile):
        self.content = content

    def get_cls(self):
        return SeratoFileHeader.SSL_CLS_TABLE.get(self.file_type, {}).get(self.version, None)

    def __repr__(self):
        return "\n".join([
            "Type:     {}\nVersion:  {}".format(self.file_type, self.version),
            repr(self.content)
        ])

    def visit(self, obj: Visitor):
        obj.accept(self)
        self.content.visit(obj)

    @classmethod
    def create_from_bin(cls, data: SeratoBinFile) -> 'SeratoFileHeader':
        name, length, reset = data.read_object_header()
        if name != SeratoFileHeader.IDENTIFIER:
            reset()
            raise TypeError("Header was '{}' but expected to be '{}'".format(name, SeratoFileHeader.IDENTIFIER))
        header_value = data.read_string(length)
        version, file_type = header_value.split('/')
        return cls(version, file_type)


class SeratoConfig(object):

    SERATO_DEFAULT_DB_FILE = "database V2"
    SERATO_DEFAULT_CRATE_DIR = "Subcrates"

    def __init__(self, path):
        self.root_path = path

    def from_bin_file(self, file: str = None) -> SeratorFile:
        if not file:
            file = SeratoConfig.SERATO_DEFAULT_DB_FILE
        reader = SeratoBinFile(self.root_path, file)
        file_header: SeratoFileHeader = SeratoFileHeader.create_from_bin(reader)
        cls: SeratorFile = file_header.get_cls()
        if not cls:
            raise NotImplementedError("File/protocol '{}' / version={} not implemented".format(
                file_header.file_type, file_header.version))
        file_header.append_content(cls.create_from_bin(reader))
        return file_header

    def parse_db(self):
        return self.from_bin_file()

    def _get_files_with_rel_path(self, subdir: str) -> List[str]:
        for _, _, files in os.walk(os.path.join(self.root_path, subdir)):
            return [ os.path.join(subdir, i) for i in files ]

    def get_crates(self) -> Iterable[str]:
        return self._get_files_with_rel_path(SeratoConfig.SERATO_DEFAULT_CRATE_DIR)

    @ActionRegistry.register_command("list-crates")
    def list_crates(self):
        print(self.get_crates())

    def parse_crate(self, name):
        return self.from_bin_file(name)

    @ActionRegistry.register_command("export-crate")
    def export_crate(self, crate_files: List[str] = None, export_target: str = "print"):
        if crate_files is None:
            crate_files = []
        if not crate_files:
            crate_files = self.list_crates()
        for crate_file in crate_files:
            crate = self.parse_crate(crate_file)
            if export_target == "print":
                print(f"File:     {crate_file}")
                print(crate)
            elif export_target.endswith(".m3u"):
                with PlaylistWriter(export_target) as playlist:
                    crate.visit(playlist)

    @ActionRegistry.register_command("export-serato")
    def export_db(self, crate_file, export_target: str = "print"):
        db = self.parse_db()
        if export_target == "print":
            print(repr(db))
        elif export_target.endswith(".m3u"):
            with PlaylistWriter(export_target) as playlist:
                db.visit(playlist)
        elif export_target.endswith(".csv"):
            with DatabaseCsvWriter(export_target) as csv:
                db.visit(csv)

    def get_smart_crates(self) -> Iterable[str]:
        return []
