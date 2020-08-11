from enum import Enum

DEFAULT_PARITY_FILE_COUNT: int = 1
DEFAULT_REDUNDANCY: int = 10
DEFAULT_BLOCK_COUNT: int = 500


class FileStatus(Enum):
    OK = 1
    REPAIRABLE = 2
    FUBAR = 3
    PARITY_DAMAGED = 4  # TODO
    REPAIRED = 5
