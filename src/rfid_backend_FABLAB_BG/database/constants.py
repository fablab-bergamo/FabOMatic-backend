"""This module contains constants used in the database module"""

from enum import Enum


class USER_LEVEL(Enum):
    """This class maps to the Board c++ FabUser.UserLevel int value"""

    INVALID = 0
    NORMAL = 1
    ADMIN = 2


DEFAULT_TIMEOUT_MINUTES = 24 * 60
DEFAULT_GRACE_PERIOD_MINUTES = 2
