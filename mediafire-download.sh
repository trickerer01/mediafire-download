#!/usr/bin/env sh
exec "${PYTHON:-python3}" -Werror -Xdev "$(dirname "$(realpath "$0")")/mediafire_download/__main__.py" "$@"
