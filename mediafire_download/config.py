# coding=UTF-8
"""
Author: trickerer (https://github.com/trickerer, https://github.com/trickerer01)
"""
#########################################
#
#

import pathlib
from typing import Protocol

from aiohttp import ClientTimeout

from .defs import NumRange

__all__ = ('BaseConfigContainer', 'Config')


class BaseConfig:
    NAMESPACE_VARS_REMAP = {
        'file': 'links_file',
        'path': 'dest_base',
        'log_level': 'logging_flags',
        'disable_log_colors': 'nocolors',
        'header': 'extra_headers',
        'cookie': 'extra_cookies',
    }

    def __init__(self) -> None:
        # new
        self.filter_filenum: NumRange | None = None
        self.filter_filesize: NumRange | None = None
        self.filter_filename: str | None = None
        self.filter_extensions: list[str] | None = None
        self.dump_links: bool | None = None
        self.dump_structure: bool | None = None
        self.links_file: pathlib.Path | None = None
        self.links: list[str] | None = None
        self.max_jobs: int | None = None
        # common
        self.dest_base: pathlib.Path | None = None
        self.proxy: str | None = None
        self.download_mode: str | None = None
        self.logging_flags: int = 0
        self.nocolors: bool | None = None
        self.timeout: ClientTimeout | None = None
        self.retries: int = 0
        self.extra_headers: list[tuple[str, str]] | None = None
        self.extra_cookies: list[tuple[str, str]] | None = None
        # extra (not configurable)
        self.nodelay: bool = False
        self.noconfirm: bool = False

    def _reset(self) -> None:
        self.__init__()  # noqa: PLC2801


class BaseConfigContainer(Protocol):
    filter_filesize: NumRange | None
    filter_filename: str | None
    filter_extensions: list[str] | None
    dump_links: bool | None
    dump_structure: bool | None
    links_file: pathlib.Path | None
    links: list[str] | None
    max_jobs: int | None
    dest_base: pathlib.Path | None
    proxy: str | None
    download_mode: str | None
    logging_flags: int
    nocolors: bool | None
    timeout: ClientTimeout | None
    retries: int
    extra_headers: list[tuple[str, str]] | None
    extra_cookies: list[tuple[str, str]] | None
    nodelay: bool
    noconfirm: bool


Config: BaseConfig = BaseConfig()

#
#
#########################################
