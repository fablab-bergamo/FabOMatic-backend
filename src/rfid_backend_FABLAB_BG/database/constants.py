from enum import Enum


class USER_LEVEL(Enum):
    """This class maps to the Board c++ FabUser.UserLevel int value"""

    INVALID = 0
    NORMAL = 1
    ADMIN = 2

DEFAULT_TIMEOUT_MINUTES = 24*60