# coding=UTF-8
"""
Author: trickerer (https://github.com/trickerer, https://github.com/trickerer01)
"""
#########################################
#
#

from __future__ import annotations

import json
import pathlib
import sys
from contextlib import AbstractAsyncContextManager

from .api import SITE_PRIMARY, DownloadParams
from .config import Config
from .defs import SLASH, UTF8
from .logger import Log
from .util import datetime_str_nfull, sanitize_filename

__all__ = ('create_callbacks',)


class PathJSONEncoder(json.JSONEncoder):
    def default(self, o: pathlib.Path) -> str:
        return o.as_posix()


class Callback(AbstractAsyncContextManager):
    pass


class DownloadParamsCallback(Callback):
    def execute(self, url: str, download_params: DownloadParams) -> None: ...
    def __str__(self) -> str: ...


class FileSystemCallback(Callback):
    def execute(self, root_id: str, ftree) -> None: ...
    def __str__(self) -> str: ...


class DumpLinksCallback(DownloadParamsCallback):
    def __init__(self, filename_base: str) -> None:
        super().__init__()
        self._filepath = pathlib.Path(Config.dest_base) / f'{filename_base}_links.json'
        self._json = {
            'args': ' '.join(sys.argv[1:]),
        }

    async def __aenter__(self) -> DumpLinksCallback:
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        Log.info(f'[{self.__class__.__name__}] Saving to {self._filepath}')
        self._filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(self._filepath, 'wt', encoding=UTF8) as outfile:
            json.dump(self._json, outfile, ensure_ascii=False, indent=4, cls=PathJSONEncoder)
            outfile.write('\n')

    def execute(self, url: str, download_params: DownloadParams) -> None:
        if url not in self._json:
            self._json[url] = []
        self._json[url].append(DownloadParams(
            download_params.num,
            download_params.num_orig,
            download_params.file_url,
            download_params.output_path.relative_to(Config.dest_base),
            download_params.expected_size,
            download_params.file_hash,
        ))

    def __str__(self) -> str:
        return f'{self.__class__.__name__}\n{json.dumps(self._json, ensure_ascii=False, indent=4)}'


class DumpFileSystemCallback(FileSystemCallback):
    def __init__(self, filename_base: str) -> None:
        super().__init__()
        self._filepath = pathlib.Path(Config.dest_base) / f'{filename_base}_filesystem.json'
        self._json: dict[str, list[str]] = {}

    async def __aenter__(self) -> DumpFileSystemCallback:
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        Log.info(f'[{self.__class__.__name__}] Saving to {self._filepath}')
        self._filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(self._filepath, 'wt', encoding=UTF8) as outfile:
            json.dump(self._json, outfile, ensure_ascii=False, indent=4, cls=PathJSONEncoder)
            outfile.write('\n')

    def execute(self, root_id: str, ftree) -> None:
        self._json.update({root_id: list(ftree)})

    def __str__(self) -> str:
        return f'{self.__class__.__name__}\n{json.dumps(self._json, ensure_ascii=False, indent=4)}'


def create_callbacks() -> tuple[set[DownloadParamsCallback], set[FileSystemCallback]]:
    return create_before_download_callbacks(), create_after_scan_callbacks()


def create_before_download_callbacks() -> set[DownloadParamsCallback]:
    callbacks = set[DownloadParamsCallback]()
    if Config.dump_links:
        callbacks.add(DumpLinksCallback(make_base_filename()))
    return callbacks


def create_after_scan_callbacks() -> set[FileSystemCallback]:
    callbacks = set[FileSystemCallback]()
    if Config.dump_structure:
        callbacks.add(DumpFileSystemCallback(make_base_filename()))
    return callbacks


def make_base_filename() -> str:
    base_name = sanitize_filename(Config.links[0].replace(SITE_PRIMARY, '').replace(SLASH, '_')) if Config.links else ''
    return f'mediafire_{base_name}_{datetime_str_nfull()}'

#
#
#########################################
