import plistlib
from unittest.mock import MagicMock

PARSE_PLIST_DATA = {}


def load(data: dict = {}):

    mock = MagicMock(name='plistlib.load', spec=plistlib.load)
    mock.return_value = data
    return mock
