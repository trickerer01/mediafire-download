# coding=UTF-8
"""
Author: trickerer (https://github.com/trickerer, https://github.com/trickerer01)
"""
#########################################
#
#

import re

HTTP_PREFIX = 'http://'
HTTPS_PREFIX = 'https://'
SITE_PRIMARY = f'{HTTPS_PREFIX}www.mediafire.com'
SITE_API = f'{SITE_PRIMARY}/api'


def compose_link_v15(folder_key: str, file_key: str, name: str) -> str:
    if name and (folder_key or file_key):
        if folder_key:
            link = f'{SITE_PRIMARY}/folder/{folder_key}/{name}/folder'
            if file_key:
                link = f'{link}/file/{file_key}'
        else:  # if file_key
            link = f'{SITE_PRIMARY}/file/{file_key}/{name}/file'
        return link
    # invalid link always
    return ''


def build_regex_from_pattern(expression: str) -> re.Pattern:
    pat_freplacements = {
        '(?:': '\u2044', '?': '\u203D', '*': '\u20F0', '(': '\u2039', ')': '\u203A',
        '.': '\u1FBE', ',': '\u201A', '+': '\u2020', '-': '\u2012',
    }
    pat_breplacements: dict[str, str] = {pat_freplacements[k]: k for k in pat_freplacements}
    pat_breplacements[pat_freplacements['(']] = '(?:'
    chars_need_escaping = list(pat_freplacements.keys())
    del chars_need_escaping[1:3]
    escape_char = '`'
    escape = escape_char in expression
    if escape:
        for fk, wtag_freplacement in pat_freplacements.items():
            expression = expression.replace(f'{escape_char}{fk}', wtag_freplacement)
    for c in chars_need_escaping:
        expression = expression.replace(c, f'\\{c}')
    expression = expression.replace('*', '.*').replace('?', '.').replace(escape_char, '')
    if escape:
        for bk, pat_breplacement in pat_breplacements.items():
            expression = expression.replace(f'{bk}', pat_breplacement)
    return re.compile(rf'^{expression}$')

#
#
#########################################
