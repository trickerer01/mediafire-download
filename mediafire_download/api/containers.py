# coding=UTF-8
"""
Author: trickerer (https://github.com/trickerer, https://github.com/trickerer01)
"""
#########################################
#
#

from __future__ import annotations

import pathlib
from typing import Literal, NamedTuple, TypedDict


class FilePermissions(TypedDict):
    value: str  # numeric
    explicit: str  # numeric
    read: str  # numeric
    write: str  # numeric


class FileLinks(TypedDict):
    normal_download: str  # URL


class FileInfo(TypedDict):
    quickkey: str
    filename: str
    ready: Literal['yes', 'no']
    created: str  # date time
    description: str
    size: str  # numeric
    privacy: Literal['public', 'private']
    password_protected: Literal['yes', 'no']
    hash: str
    filetype: str  # Literal?
    mimetype: str  # 'application/x-rar'
    owner_name: str
    flag: str  # numeric
    permissions: FilePermissions
    revision: str  # numeric
    view: str  # numeric
    edit: str  # numeric
    links: FileLinks
    created_utc: str  # ISO timestamp

    # non-parsed fields
    num_in_queue: int


class ActionResponse(TypedDict):
    action: str
    file_info: FileInfo
    result: Literal['Success', 'Failure']
    current_api_version: Literal['1.1', '1.2', '1.3', '1.4', '1.5']


class APIResponse(TypedDict):
    response: ActionResponse


class ParsedUrl(NamedTuple):
    folder_key: str
    file_key: str
    name: str

    @staticmethod
    def default() -> ParsedUrl:
        return ParsedUrl('', '', '')


class DownloadParams(NamedTuple):
    num: int
    num_orig: int
    file_url: str
    output_path: pathlib.Path
    expected_size: int
    file_hash: str

#
#
#########################################
