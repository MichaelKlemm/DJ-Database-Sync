#!/usr/bin/env python3
"""
Utility to synchronize Databases and Playlists of various DJ and Music applications

Prominent examples:
 * iTunes / AppleMusic
 * Serato DJ Pro

"""
import os
import argparse

from djdbsync.tools.Serato import SeratoConfig, SeratoSongStorageFs
from djdbsync.tools.AppleMusic import AppleMusicDatabase
from djdbsync.utils.ActionRegistry import ActionRegistry

import logging

log = logging.getLogger(__name__)

HAVE_GUI = False


# try:
#     from kivy.app import App
#     from kivy.uix.label import Label
# except:
#     HAVE_GUI = False


class ArgumentMultilineHelpFormatter(argparse.ArgumentDefaultsHelpFormatter):

    def _split_lines(self, text, width):
        if text.startswith('ML|'):
            text = text[3:]
            import textwrap
            return textwrap.wrap(text,
                                 width,
                                 replace_whitespace=False)
        # pylint: disable=protected-access
        return super()._split_lines(text, width)

    def _fill_text(self, text, width, indent):
        import textwrap
        return textwrap.fill(text,
                             width,
                             replace_whitespace=False,
                             initial_indent=indent,
                             subsequent_indent=indent)


# if HAVE_GUI:
#
#
#     class DjMediaSyncGui(App):
#
#         def build(self):
#             return Label(text='Hello world')


class DjMediaSyncController(object):

    def __init__(self):
        self.argparse = argparse.ArgumentParser(
            # prog="Music Database and Playlist synchronisation utility for DJs",
            # version="0.0.1-beta",
            # usage="Benutzung",
            formatter_class=ArgumentMultilineHelpFormatter,
            description=__doc__,
            epilog="test...",
            add_help=False,
        )
        self.init_option_parser_groups()
        self.serato_parser = None
        self.apple_database = None
        ActionRegistry.register_object(self)

    def init_option_parser_groups(self):
        self.init_commands()
        self.init_common_option_group()
        self.init_serato_options()
        self.init_apple_music_options()

    def init_commands(self):
        # cmds = self.argparse.add_subparsers(title="Commands",
        #                                    description="The following commands are available")
        cmds = self.argparse.add_mutually_exclusive_group()
        for command, description in ActionRegistry.get_commands_desc().items():
            helptext, _ = description
            cmds.add_argument('commands',
                              metavar=command,
                              # dest='commands',
                              action='append',
                              help=helptext,
                              nargs='?')

    def init_common_option_group(self):
        i = self.argparse.add_argument_group(title="Common options", description="abc")

        i.add_argument("-d",
                       "--dry-run",
                       action="store_true",
                       dest="dry_run",
                       default=False,
                       help="")

        i.add_argument("-u",
                       "--update-existing",
                       action="store_true",
                       dest="update_existing",
                       default=False,
                       help="")

        i.add_argument("-o",
                       "--out-dir",
                       dest="output_directory",
                       help="")

        i.add_argument("-l",
                       "--loglevel",
                       choices=["DEBUG", "INFO", "WARN", "ERROR"],
                       default="ERROR",
                       help="")

        i.add_argument("-v",
                       "--version",
                       action="version",
                       help="")

        i.add_argument("-h",
                       "--help",
                       action="help",
                       help="")

    def init_serato_options(self):
        i = self.argparse.add_argument_group(title="Serato DJ tool options",
                                             description="")

        i.add_argument(  # "-s",
            "--serato-dir",
            dest="serato_directory",
            default=os.path.expanduser('~/Music/_Serato_'),
            help="Directoy to the Serato database folder. You should only use the productive path"
                 "if you really know what you do. It is supposed to either make a backup first or"
                 "to change this path to a copy of this folder.")

        i.add_argument("--link-dir",
                       dest="serato_media_dir",
                       help="Directory to create the the linked media files at. This directory should not be a"
                            "subdirectoy of a folder the Apple Music application looks for songs at. If this"
                            "directory does not exist, it will be created. At this directory all songs from Apple"
                            "Music will be stored by there database ID and linked to the concrete file")

        i.add_argument(  # "-c",
            "--crate",
            dest="crate_files",
            nargs='?',
            action="append",
            help="Select a specific crate file. This is a relative path base on serato-dir")

        i.add_argument(  # "-e",
            "--export-file",
            dest="export_target",
            default="print",
            help="Select a specific crate file. This is a relative path base on serato-dir")

    def init_apple_music_options(self):
        i = self.argparse.add_argument_group(title="Apple Music tool options", description="ABC")

        i.add_argument(  # "-i",
            "--itunes-db",
            dest="apple_database_file",
            default=os.path.expanduser('~/Music/Mediathek.xml'),
            help="")

    @ActionRegistry.register_command(name='create-itunes-links')
    def create_sym_links(self, apple_database_file: str, serato_media_dir: str, update_existing: bool, dry_run: bool):
        """
        Create links named by the Song-ID in the iTunes DB to the real file

        By reading the iTunes / AppleMusic database (set by `apple_database_file`) the program will create a linked file
        in the directory `serato_media_dir`

        :param apple_database_file:
        :param serato_media_dir:
        :param update_existing:
        :param dry_run:
        :return:
        """
        storage = SeratoSongStorageFs(serato_media_dir, dry_run=dry_run)

        self.apple_database.load()
        for track_id, track_path in self.apple_database.get_db_track_locations().items():
            storage.add_song(track_id, track_path, update_existing=update_existing)

    def __launch__(self):
        options = self.argparse.parse_args()
        options = vars(options)
        commands = [i for i in options.pop("commands") if i]

        if "serato_directory" in options and options["serato_directory"]:
            self.serato_parser = SeratoConfig(options["serato_directory"])
            ActionRegistry.register_object(self.serato_parser)

        if "apple_database_file" in options and options["apple_database_file"]:
            self.apple_database = AppleMusicDatabase(options["apple_database_file"])
            ActionRegistry.register_object(self.apple_database)

        for action in commands:  # options.get("commands", []):
            action_params, num_optional = ActionRegistry.get_action_args(action)
            num_required = len(action_params) - num_optional
            params = {}
            for i in range(len(action_params)):
                if action_params[i] not in options:
                    if i < num_required:
                        raise Exception("Argument '{}' missing for action {}".format(action_params[i], action))
                    continue
                params[action_params[i]] = options[action_params[i]]
            ActionRegistry.do_action(action, **params)

    @staticmethod
    def launch():
        try:
            DjMediaSyncController().__launch__()
        except Exception as e:
            print("Error while launching application")
            print(repr(e))
