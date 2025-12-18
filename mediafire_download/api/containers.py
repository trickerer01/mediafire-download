# coding=UTF-8
"""
Author: trickerer (https://github.com/trickerer, https://github.com/trickerer01)
"""
#########################################
#
#

from __future__ import annotations

import pathlib
from enum import IntEnum
from typing import Literal, NamedTuple, TypeAlias, TypedDict


class FileFlags(IntEnum):
    OWNED = 1  # owned by the current session user
    PREVIEW = 2  # file is supported for preview
    EDITABLE = 4  # file is editable
    VIRUS = 8  # file is flagged by virus scanner


class FolderFlags(IntEnum):
    OWNED = 1  # owned by the current session user


class Permissions(TypedDict):
    value: str  # numeric
    explicit: str  # numeric
    read: str  # numeric
    write: str  # numeric


class FileLinks(TypedDict):
    view: str  # URL, may be absent, unsupported
    read: str  # URL, may be absent, unsupported
    edit: str  # URL, may be absent, unsupported
    watch: str  # URL, may be absent, unsupported
    listen: str  # URL, may be absent, unsupported
    normal_download: str  # URL
    direct_download: str  # URL, may be absent, unsupported
    streaming: str  # URL, may be absent, unsupported
    download: str  # URL, may be absent, unsupported


class FileInfo(TypedDict):
    quickkey: str
    filename: str
    ready: Literal['yes', 'no']
    created: str  # date time
    description: str
    size: str  # numeric
    privacy: Literal['public', 'private']
    password_protected: Literal['yes', 'no']
    hash: str  # sha256 hash (API 1.5)
    filetype: str  # Literal?
    mimetype: str  # 'application/x-rar'
    owner_name: str
    flag: str  # numeric, see FileFlags
    permissions: Permissions
    revision: str  # numeric
    view: str  # numeric
    edit: str  # numeric
    links: FileLinks
    created_utc: str  # ISO timestamp

    # custom fields
    num_in_queue: int


class FolderFileInfo(FileInfo):
    downloads: str  # numeric, unused
    views: str  # numeric, unused


class FolderInfo(TypedDict):
    folderkey: str
    name: str
    description: str
    created: str  # date time
    privacy: Literal['public', 'private']
    file_count: str  # numeric
    folder_count: str  # numeric
    revision: str  # numeric
    owner_name: str  # unused
    avatar: str  # URL, unused
    flag: str  # numeric, see FolderFlags
    permissions: Permissions
    created_utc: str  # ISO timestamp


class FolderFolderInfo(FolderInfo):
    tags: str  # unused
    dropbox_enabled: Literal['yes', 'no']  # unused


class FolderContent(TypedDict):
    chunk_size: str  # numeric
    content_type: Literal['files', 'folders']
    chunk_number: str  # numeric
    folderkey: str
    files: list[FolderFileInfo]
    folders: list[FolderFolderInfo]
    more_chunks: Literal['yes', 'no']
    revision: str  # numeric


class ActionResponse(TypedDict):
    action: Literal['file/get_info', 'folder/get_info', 'folder/get_contents']
    result: Literal['Success', 'Failure']
    current_api_version: Literal['1.1', '1.2', '1.3', '1.4', '1.5']


class APIFileInfoResponse(ActionResponse):
    file_info: FileInfo


class APIFolderInfoResponse(ActionResponse):
    folder_info: FolderInfo


class APIFolderContentResponse(ActionResponse):
    folder_content: FolderContent


class APIResponse(TypedDict):
    response: APIFileInfoResponse | APIFolderInfoResponse | APIFolderContentResponse


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


FileSystemMapping: TypeAlias = dict[pathlib.PurePosixPath, FileInfo | FolderInfo]
'''Mapping: path -> FileInfo | FolderInfo'''
FilePathMapping: TypeAlias = dict[pathlib.PurePosixPath, FileInfo]
'''Mapping: path -> FileInfo'''

#
#
#########################################
