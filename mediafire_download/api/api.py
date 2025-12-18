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
import random
import re
import sys
import warnings
from asyncio import Semaphore, create_task, gather, sleep
from collections.abc import Callable
from gzip import BadGzipFile, GzipFile
from inspect import get_annotations
from io import BytesIO
from typing import Literal, TypeAlias

from aiofile import async_open
from aiohttp import (
    ClientConnectorError,
    ClientPayloadError,
    ClientResponse,
    ClientResponseError,
    ClientSession,
    ClientTimeout,
    TCPConnector,
)
from aiohttp_socks import ProxyConnector
from bs4 import BeautifulSoup

from mediafire_download.util import UAManager, compose_link_v15

from .containers import (
    APIFileInfoResponse,
    APIFolderContentResponse,
    APIFolderInfoResponse,
    APIResponse,
    DownloadParams,
    FileInfo,
    FilePathMapping,
    FileSystemMapping,
    FolderInfo,
    ParsedUrl,
)
from .defs import API_VERSION, CONNECT_RETRY_DELAY, SITE_API, UTF8, DownloadMode, Mem
from .exceptions import MediafireErrorCodes, RequestError, ValidationError
from .filters import Filter, any_filter_matching
from .logging import Log, set_logger
from .options import MediafireOptions
from .request_queue import RequestQueue

__all__ = ('Mediafire',)

APIContentTypes: TypeAlias = Literal['files', 'folder', 'folders']

re_mediafire_file = re.compile(r'\W(\w{14,})\W')
re_mediafire_folder = re_mediafire_file


class Mediafire:
    def __init__(self, options: MediafireOptions) -> None:
        # globals
        set_logger(options['logger'])
        # locals
        self._aborted: bool = False
        self._session: ClientSession | None = None
        self._queue_size: int = 0
        self._queue_size_orig: int = 0
        self._parsed: ParsedUrl = ParsedUrl.default()
        # options
        self._dest_base: pathlib.Path = options['dest_base']
        self._retries: int = options['retries']
        self._max_jobs = options['max_jobs']
        self._timeout: ClientTimeout = options['timeout']
        self._nodelay: bool = options['nodelay']
        self._noconfirm: bool = options['noconfirm']
        self._proxy: str = options['proxy']
        self._extra_headers: list[tuple[str, str]] = options['extra_headers']
        self._extra_cookies: list[tuple[str, str]] = options['extra_cookies']
        self._filters: tuple[Filter, ...] = options['filters']
        self._before_download_hooks: tuple[Callable, ...] = options['hooks_before_download']
        self._after_scan_hooks: tuple[Callable, ...] = options['hooks_after_scan']
        self._download_mode: DownloadMode = options['download_mode']
        # ensure correct args
        assert Log
        assert next(reversed(self._dest_base.parents)).is_dir()
        assert isinstance(self._download_mode, DownloadMode)
        assert self._max_jobs > 0

    async def __aenter__(self) -> Mediafire:
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    @property
    def original_url(self):
        return compose_link_v15(self._parsed.folder_key, self._parsed.file_key, self._parsed.name)

    @staticmethod
    def _make_download_params(
        num: int, num_orig: int, file_url: str, output_path: pathlib.Path, expected_size: int, file_hash: str,
    ) -> DownloadParams:
        return DownloadParams(num, num_orig, file_url, output_path, expected_size, file_hash)

    def _before_download(self, *args) -> None:
        pass

    def _after_scan(self, *args) -> None:
        pass

    def abort(self) -> None:
        Log.warn('Aborting...')
        self._aborted = True

    def _make_session(self) -> ClientSession:
        if self._session is not None and not self._session.closed:
            raise ValidationError('Called `make_session` with current session active!')
        use_proxy = bool(self._proxy)
        if use_proxy:
            connector = ProxyConnector.from_url(self._proxy, limit=self._max_jobs)
        else:
            connector = TCPConnector(limit=self._max_jobs)
        session = ClientSession(connector=connector, read_bufsize=Mem.MB, timeout=self._timeout)
        new_useragent = UAManager.select_useragent(self._proxy if use_proxy else None)
        Log.trace(f'[{"P" if use_proxy else "NP"}] Selected user-agent \'{new_useragent}\'...')
        session.headers.update({'User-Agent': new_useragent, 'Content-Type': 'application/json'})
        if self._extra_headers:
            for hk, hv in self._extra_headers:
                session.headers.update({hk: hv})
        if self._extra_cookies:
            for ck, cv in self._extra_cookies:
                session.cookie_jar.update_cookies({ck: cv})
        return session

    async def _wrap_request(self, method: Literal['POST', 'GET'], url: str, **kwargs) -> ClientResponse:
        """Queues request, updating headers/proxies beforehand, and returns the response"""
        if self._session is None or self._session.closed:
            self._session = self._make_session()
        if self._nodelay is False:
            await RequestQueue.until_ready(url)
        if 'timeout' not in kwargs:
            kwargs.update(timeout=self._timeout)
        return await self._session.request(method, url, **kwargs)

    async def _query_api(self, endpoint: str) -> APIResponse | int:
        try_num = 0
        while try_num <= self._retries:
            r: ClientResponse | None = None
            try:
                Log.trace(f'Sending API request: GET => {endpoint}')
                r = await self._wrap_request('GET', endpoint)

                jresp: APIResponse | int = await r.json()

                if not isinstance(jresp, dict):
                    Log.fatal(f'Unknown API response: {jresp!r}')
                    raise RequestError(MediafireErrorCodes.EUNKNOWNRESPONSE)
                elif jresp and 'error' in jresp:
                    raise RequestError(MediafireErrorCodes.ESESSIONTOKEN)
                elif jresp and 'response' in jresp:
                    return jresp
                else:
                    raise RequestError(MediafireErrorCodes.EUNK)
            except Exception as e:
                Log.error(f'_query_api: {sys.exc_info()[0]}: {sys.exc_info()[1]}')
                if isinstance(e, RequestError):
                    if e.code not in (MediafireErrorCodes.EUNK,):
                        break
                if (r is None or r.status != 403) and not isinstance(e, (ClientPayloadError, ClientResponseError, ClientConnectorError)):
                    try_num += 1
                    Log.error(f'_query_api: error #{try_num:d}...')
                if r is not None and not r.closed:
                    r.close()
                if self._aborted:
                    return 0
                if try_num <= self._retries:
                    await sleep(random.uniform(*CONNECT_RETRY_DELAY))
                continue

        Log.error('Unable to connect. Aborting')
        raise ConnectionError

    async def _query_folder_info(
        self, content_type: APIContentTypes, folder_key: str, get_content: bool, chunk_num: int,
    ) -> APIResponse:
        content_selector = 'get_content' if get_content else 'get_info'
        endpoint = (
            f'{SITE_API}/{API_VERSION}/folder/{content_selector}.php?r=utga&content_type={content_type}&filter=all&order_by=name'
            f'&order_direction=asc&chunk={chunk_num}&version={API_VERSION}&folder_key={folder_key}&response_format=json'
        )
        return await self._query_api(endpoint)

    async def _wrap_chunked_api_folder_query(
        self, content_type: APIContentTypes, folder_key: str,
    ) -> APIFolderContentResponse:
        results: APIFolderContentResponse | None = None
        chunk_num = 1
        more_chunks = True
        while more_chunks:
            chunks_result = await self._query_folder_info(content_type, folder_key, True, chunk_num)
            response: APIFolderContentResponse = chunks_result['response']
            if results is not None:
                results.update(**response)
            else:
                results = response
            chunk_num += 1
            more_chunks = response['folder_content'].get('more_chunks', 'no') == 'yes'
        assert results
        return results

    async def _get_folder_folders(self, folder_key: str) -> APIFolderContentResponse:
        return await self._wrap_chunked_api_folder_query('folders', folder_key)

    async def _get_folder_files(self, folder_key: str) -> APIFolderContentResponse:
        return await self._wrap_chunked_api_folder_query('files', folder_key)

    async def _get_folder_info(self, folder_key: str) -> APIFolderInfoResponse:
        api_response = await self._query_folder_info('folder', folder_key, False, 1)
        return api_response['response']

    async def _get_file_info(self) -> APIFileInfoResponse:
        endpoint = f'{SITE_API}/file/get_info.php?quick_key={self._parsed.file_key}&response_format=json'
        response: APIResponse = await self._query_api(endpoint)
        return response['response']

    def _parse_file(self, links_file: pathlib.Path) -> list[DownloadParams]:
        assert links_file.is_file(), f'File \'{links_file}\' not found!'

        with open(links_file, 'rt', encoding=UTF8) as infile:
            json_ = json.load(infile)

        download_param_list: list[DownloadParams] = []
        for _, fdata_or_str in json_.items():
            if isinstance(fdata_or_str, list) and fdata_or_str[0].keys() == get_annotations(DownloadParams).keys():
                file_datas: list[DownloadParams] = fdata_or_str
                download_param_list.extend(self._make_download_params(
                    file_data.num,
                    file_data.num_orig,
                    file_data.file_url,
                    self._dest_base / file_data.output_path,
                    file_data.expected_size,
                    file_data.file_hash,
                ) for file_data in file_datas)
        return download_param_list

    async def download_from_file(self, links_file: pathlib.Path) -> tuple[pathlib.Path, ...]:
        """
        Parse JSON file containing required file matadata gotten from running
        mediafire downloader with '--dump-links' flag and download all the files
        :param links_file: pathlib.Path to JSON file
        :return: processed file paths
        """
        warnings.warn('Entry point \'download_from_file\' is unreliable and should not be used', DeprecationWarning)

        async def proc_download_params(dparams: DownloadParams) -> pathlib.Path:
            self._before_download(dparams)
            return await self._download(dparams)

        donwload_param_list = self._parse_file(links_file)
        Log.info(f'Parsed {links_file.name}: found {len(donwload_param_list):d} files')

        tasks = []
        for download_params in donwload_param_list:
            if self._aborted:
                return ()
            tasks.append(proc_download_params(download_params))

        results: tuple[pathlib.Path | BaseException, ...] = await gather(*tasks)
        Log.info(f'Downloaded {len([c for c in results if isinstance(c, pathlib.Path)])} / {len(tasks)} files')
        return results

    async def _download_folder(self) -> tuple[pathlib.Path, ...]:
        action_response: APIFolderInfoResponse = await self._get_folder_info(self._parsed.folder_key)
        folder: FolderInfo = action_response['folder_info']
        ftree: FileSystemMapping = await self._build_file_system(folder)
        files: FilePathMapping = {p: ftree[p] for p in sorted(ftree, key=lambda p: ftree[p]['created']) if 'filename' in ftree[p]}
        Log.info(f'{folder["name"]}: found {len(files):d} files...')

        for fidx, fpath in enumerate(files):
            files[fpath]['num_in_queue'] = fidx + 1

        self._after_scan(folder, ftree)

        self._queue_size_orig = len(files)
        proc_queue: set[pathlib.PurePosixPath] = self._filter_folder_files(files)
        self._queue_size = len(proc_queue)
        Log.info(f'Saving {self._queue_size:d} / {len(files):d} files...')

        async def download_folder_file_wrapper(index: int, file: FileInfo, file_path: pathlib.Path) -> pathlib.Path:
            download_params = self._make_download_params(
                index, file['num_in_queue'], file['links']['normal_download'], file_path, int(file['size']), file['hash'],
            )
            self._before_download(download_params)
            async with semaphore:
                return await self._download(download_params)

        semaphore = Semaphore(self._max_jobs)
        tasks = []
        idx = 0
        for path, file_or_folder in ftree.items():
            if self._aborted:
                return ()
            if path not in proc_queue:
                Log.trace(f'Skipping excluded node {file_or_folder!s} ({path})...')
                continue
            tasks.append(create_task(download_folder_file_wrapper(idx, file_or_folder, pathlib.Path(path))))
            idx += 1

        results: tuple[pathlib.Path | BaseException, ...] = await gather(*tasks)
        Log.info(f'Downloaded {len([c for c in results if isinstance(c, pathlib.Path)])} / {len(tasks)} files')
        return results

    async def download_url(self, url: str) -> tuple[pathlib.Path, ...]:
        """
        Parse given folder or file URL and download found files
        :param url: mediafire link url
        :return: processed file paths
        """
        self._parsed = self._parse_url(url)
        assert self._parsed.name
        assert self._parsed.folder_key or self._parsed.file_key

        Log.info(f'Processing {"folder" if self._parsed.folder_key else "file"} \'{self._parsed.name}\'...')
        if self._parsed.folder_key and self._parsed.file_key:
            Log.info(f'Pre-selected file {self._parsed.file_key}...')
        if self._parsed.folder_key:
            return await self._download_folder()
        else:
            return await self._download_file(),  # noqa: COM818

    async def _download_file(self) -> pathlib.Path:
        action_response: APIFileInfoResponse = await self._get_file_info()
        assert action_response['result'] == 'Success', f'Result was \'{action_response["result"]}\'!'
        assert action_response['current_api_version'] == API_VERSION, f'Unexpected API version {action_response["current_api_version"]}!'
        file: FileInfo = action_response['file_info']
        file_name = file['filename']
        file_url = file['links']['normal_download']
        file_size = int(file['size'])
        file_hash = file['hash']

        file['num_in_queue'] = 1
        self._queue_size_orig = 1
        self._queue_size = 1
        output_path = self._dest_base / file_name

        if ffilter := any_filter_matching(file, self._filters):
            Log.info(f'File {file_name} was filtered out by {ffilter!s}. Skipped!')
            return output_path

        download_params = self._make_download_params(1, 1, file_url, output_path, file_size, file_hash)
        self._before_download(download_params)
        return await self._download(download_params)

    async def _download(self, params: DownloadParams) -> pathlib.Path:
        if self._download_mode == DownloadMode.SKIP:
            return params.output_path
        if self._aborted:
            return params.output_path
        num = params.num
        num_orig = params.num_orig
        file_url = params.file_url
        output_path = params.output_path
        expected_size = params.expected_size

        touch = self._download_mode == DownloadMode.TOUCH

        if output_path.is_file():
            # TODO: check hash
            existing_size = output_path.stat().st_size
            if not (touch and existing_size == 0):
                size_match_msg = f'({"COMPLETE" if existing_size == expected_size else "MISMATCH!"})'
                exists_msg = f'{output_path} already exists, size: {existing_size / Mem.MB:.2f} MB {size_match_msg}'
                Log.info(exists_msg)
                if self._noconfirm and existing_size == expected_size:
                    return output_path
                ans = 'q'
                while ans not in 'yYnN01':
                    ans = 'y' if self._noconfirm else input(f'{exists_msg}. Overwrite? [y/N]\n')
                    if ans in 'nN0':
                        Log.warn(f'{output_path.name} was skipped')
                        return output_path
                    else:
                        Log.warn(f'Overwriting {output_path.name}...')

        touch_msg = ' <touch>' if touch else ''
        size_msg = '0.00 / ' if touch else ''
        Log.info(f'[{num:d} / {self._queue_size:d}] ([{num_orig:d} / {self._queue_size_orig}])'
                 f' Saving{touch_msg} {output_path.name} => {output_path} ({size_msg}{expected_size / Mem.MB:.2f} MB)...')

        output_path.parent.mkdir(parents=True, exist_ok=True)

        if touch:
            output_path.touch(exist_ok=True)
            return output_path

        try_num = 0
        while try_num <= self._retries:
            r: ClientResponse | None = None
            try:
                async with await self._wrap_request('GET', file_url, headers={'Accept-Encoding': 'gzip'}) as r:
                    r.raise_for_status()
                    content = await r.content.read()
                    if 'Content-Disposition' not in r.headers:
                        if (content_encoding := r.headers.get('Content-Encoding', '')) != 'gzip':
                            raise ValueError(f'Unexcepted content encoding \'{content_encoding}\'')
                        # this can be either raw html or gzip file
                        try:
                            with GzipFile(fileobj=BytesIO(content)) as gzip_file:
                                content = gzip_file.read()
                        except BadGzipFile:
                            pass
                        body = content.decode(UTF8)
                        html = BeautifulSoup(body, 'html.parser')
                        real_url = html.find('a', href=re.compile(r'https://download\d+\..+'))['href']
                        r.close()
                        r = await self._wrap_request('GET', real_url)
                        if r.content_length != expected_size:
                            Log.warn(f'Expected size mismatch at soup URL {real_url}: {r.content_length!s} != {expected_size:d}!')

                    bytes_written = 0
                    i = 0
                    async with async_open(output_path, 'wb') as output_file:
                        async for chunk in r.content.iter_chunked(512 * Mem.KB):
                            await output_file.write(chunk)
                            chunk_size = len(chunk)
                            bytes_written += chunk_size
                            i += 1
                            if try_num and chunk_size:
                                try_num = 0
                            if i % 100 == 1 or bytes_written + 1 * Mem.MB >= expected_size:
                                dwn_progress_str = f'+{chunk_size:d} ({bytes_written / Mem.MB:.2f} / {expected_size / Mem.MB:.2f} MB)'
                                Log.info(f'[{num:d} / {self._queue_size:d}] {output_path.name} chunk {i:d}: {dwn_progress_str}...')
                break
            except Exception as e:
                Log.error(f'{output_path.name}: {sys.exc_info()[0]}: {sys.exc_info()[1]}')
                if (r is None or r.status not in (403,)) and not isinstance(e, (
                   ClientPayloadError, ClientResponseError, ClientConnectorError)):
                    try_num += 1
                    Log.error(f'{output_path.name}: error #{try_num:d}...')
                if r is not None and not r.closed:
                    r.close()
                if try_num <= self._retries:
                    await sleep(random.uniform(*CONNECT_RETRY_DELAY))

        if output_path.is_file():
            total_size = output_path.stat().st_size
            Log.info(f'{output_path.name} {"" if total_size == expected_size else "NOT "}completed ({total_size / Mem.MB:.2f} MB)')
            return output_path

        Log.error(f'FAILED to download {output_path.name}!')
        return pathlib.Path()

    def _filter_folder_files(self, ftree: dict[pathlib.PurePosixPath, FileInfo]) -> set[pathlib.PurePosixPath]:
        proc_queue = set[pathlib.PurePosixPath]()
        file_idx = 0
        enqueued_idx = 0
        for qpath, file in ftree.items():
            if self._aborted:
                break
            file_idx += 1
            if self._parsed.folder_key and self._parsed.file_key:
                do_append = file['quickkey'] == self._parsed.file_key
                if not do_append:
                    Log.trace(f'[{file_idx:d}] File \'{qpath.name}\' is not selected for download, skipped...')
                    continue
            elif self._filters:
                if ffilter := any_filter_matching(file, self._filters):
                    Log.info(f'[{file_idx:d}] File {qpath.name} was filtered out by {ffilter!s}. Skipped!')
                    continue
                do_append = True
            else:
                file_size = int(file['size'])
                ans = 'y' if self._noconfirm else 'q'
                while ans not in 'nNyY10':
                    ans = input(f'[{file_idx:d}] Download {qpath.name} ({file_size / Mem.MB:.2f} MB)? [Y/n]\n')
                do_append = ans in 'yY1'
            if do_append:
                enqueued_idx += 1
                Log.info(f'[{enqueued_idx:d}] {qpath.name} enqueued...')
                proc_queue.add(qpath)
        return proc_queue

    async def _build_file_system(self, root_folder: FolderInfo) -> FileSystemMapping:
        async def build_path_tree(parent_folder: FolderInfo, parent_folder_path: pathlib.PurePosixPath) -> None:
            folder_key = parent_folder['folderkey']
            if int(parent_folder.get('file_count', '0')) > 0:
                files_response: APIFolderContentResponse = await self._get_folder_files(folder_key)
                for file_info in files_response['folder_content'].get('files', []):
                    file_path = parent_folder_path / file_info['filename'].strip()
                    path_mapping[file_path] = file_info
            if int(parent_folder.get('folder_count', '0')) > 0:
                subfolders_response: APIFolderContentResponse = await self._get_folder_folders(folder_key)
                for folder_info in subfolders_response['folder_content'].get('folders', []):
                    folder_path = parent_folder_path / folder_info['name'].strip()
                    path_mapping[folder_path] = folder_info
                    await build_path_tree(folder_info, folder_path)

        root_name = root_folder['name']
        root_path = pathlib.PurePosixPath(self._dest_base.joinpath(root_name.strip()))
        path_mapping: FileSystemMapping = {root_path: root_folder}
        await build_path_tree(root_folder, root_path)

        sorted_mapping: FileSystemMapping = {k: path_mapping[k] for k in sorted(path_mapping)}
        return sorted_mapping

    @staticmethod
    def _parse_url(url: str) -> ParsedUrl:
        folder_lookup1 = '/folder/'
        file_lookup1, file_lookup2 = '/file/', '/file_premium/'
        has_folder = folder_lookup1 in url
        has_file1, has_file2 = file_lookup1 in url, file_lookup2 in url
        folder_key = ''
        file_key = ''
        if has_folder:
            # ex: {SITE}/folder/aoxkjmx3y/awesometitle/
            parts = url.split(folder_lookup1, 1)[1]
            folder_key, name = tuple(parts.split('/')[:2])
        elif has_file1 or has_file2:
            # ex. {SITE}/file/oxteykmx3y/fstaj.rar/file
            url = url.replace(' ', '')
            fmatch = re_mediafire_file.search(url)
            assert fmatch, f'Unable to parse url v2: file id not found in \'{url}\'!'
            parts = url.split(file_lookup1 if has_file1 else file_lookup2, 1)[1]
            file_key, name = tuple(parts.split('/')[:2])
        else:
            raise ValueError(f'Not a valid Mediafire URL \'{url}\'!')
        return ParsedUrl(folder_key, file_key, name)

#
#
#########################################
