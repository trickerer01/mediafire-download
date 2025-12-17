# coding=UTF-8
"""
Author: trickerer (https://github.com/trickerer, https://github.com/trickerer01)
"""
#########################################
#
#

from collections.abc import Iterable


def assert_nonempty(container: Iterable, message='') -> Iterable:
    assert container, message
    return container

#
#
#########################################
