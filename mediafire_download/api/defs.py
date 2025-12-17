# coding=UTF-8
"""
Author: trickerer (https://github.com/trickerer, https://github.com/trickerer01)
"""
#########################################
#
#

from enum import Enum
from typing import NamedTuple

CONNECT_REQUEST_DELAY = 0.3
CONNECT_RETRY_DELAY = (4.0, 8.0)

UTF8 = 'utf-8'
HTTPS_PREFIX = 'https://'

SITE_PRIMARY = f'{HTTPS_PREFIX}www.mediafire.com'
SITE_API = f'{SITE_PRIMARY}/api'
API_VERSION = '1.5'


class DownloadMode(str, Enum):
    FULL = 'full'
    TOUCH = 'touch'
    SKIP = 'skip'


DOWNLOAD_MODES: tuple[str, ...] = tuple(_.value for _ in DownloadMode.__members__.values())
'''('full','touch','skip')'''
DOWNLOAD_MODE_DEFAULT = DownloadMode.FULL.value
"""'full'"""


class Mem:
    KB = 1024
    MB = KB * 1024
    GB = MB * 1024


class NumRange(NamedTuple):
    min: float
    max: float

    def __bool__(self) -> bool:
        return any(bool(getattr(self, _)) for _ in self._fields)

#
#
#########################################
