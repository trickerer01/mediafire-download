# coding=UTF-8
"""
Author: trickerer (https://github.com/trickerer, https://github.com/trickerer01)
"""
#########################################
#
#

import pathlib
from collections.abc import Callable
from typing import TypedDict

from aiohttp import ClientTimeout

from .defs import DownloadMode
from .filters import Filter
from .logging import Logger


class MediafireOptions(TypedDict):
    # for local
    dest_base: pathlib.Path
    retries: int
    max_jobs: int
    timeout: ClientTimeout
    nodelay: bool
    noconfirm: bool
    proxy: str
    extra_headers: list[tuple[str, str]]
    extra_cookies: list[tuple[str, str]]
    filters: tuple[Filter, ...]
    hooks_before_download: tuple[Callable]
    hooks_after_scan: tuple[Callable]
    download_mode: DownloadMode
    # for global
    logger: Logger

#
#
#########################################
