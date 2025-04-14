import enum


class ExitCode(enum.IntEnum):
    OK = 0
    COMMAND_LINE_ERROR = 1
    CONFIGURATION_PROBLEM = 2
    UNKNOWN_COMMAND = 3
    MODULE_NOT_FOUND = 4
    ERROR = 5
