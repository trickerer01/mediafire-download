# coding=UTF-8
"""
Author: trickerer (https://github.com/trickerer, https://github.com/trickerer01)
"""
#########################################
#
#

from enum import IntEnum

__all__ = ('MediafireError', 'MediafireErrorCodes', 'RequestError', 'ValidationError')


class MediafireErrorCodes(IntEnum):
    ESUCCESS = 0
    EUNK = -1
    MEDIAFIRE_ERROR_CODE_GENERIC = -255

    def __str__(self) -> str:
        return f'{self.name} ({self.value:d})'


MEDIAFIRE_ERROR_DESCRIPTION: dict[MediafireErrorCodes, tuple[str, str]] = {
    MediafireErrorCodes.EUNK: ('EUNK', 'An internal error has occurred. Please submit a bug report, '),
    # fallback
    MediafireErrorCodes.MEDIAFIRE_ERROR_CODE_GENERIC: ('EGENERIC', 'Unknown error \'%d\''),
}


class MediafireError(Exception):
    """Generic mediafire error"""


class ValidationError(MediafireError):
    """Error in validation stage"""


class RequestError(MediafireError):
    def __init__(self, msg_or_code: str | int | MediafireErrorCodes) -> None:
        if isinstance(msg_or_code, (int, MediafireErrorCodes)):
            self.code = msg_or_code
            if self.code in MEDIAFIRE_ERROR_DESCRIPTION:
                err_name, err_desc = MEDIAFIRE_ERROR_DESCRIPTION[self.code]
            else:
                err = MEDIAFIRE_ERROR_DESCRIPTION[MediafireErrorCodes.MEDIAFIRE_ERROR_CODE_GENERIC]
                err_name = err[0]
                err_desc = err[1] % (self.code if isinstance(self.code, int) else self.code.value)
            self.message = f'{err_name}, {err_desc}'
        else:
            self.code = MediafireErrorCodes.MEDIAFIRE_ERROR_CODE_GENERIC
            self.message = str(msg_or_code)

    def __str__(self) -> str:
        return self.message

    __repr__ = __str__

#
#
#########################################
