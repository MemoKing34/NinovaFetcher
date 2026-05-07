import hashlib
import sys
from dataclasses import dataclass
from enum import Enum, auto
from getpass import getpass
from pathlib import Path
from typing import NamedTuple, Optional

if sys.version_info >= (3, 11):
    from enum import ReprEnum, StrEnum
    from typing import Self
else:
    from typing_extensions import Self
    class ReprEnum(Enum):
        """
        Only changes the repr(), leaving str() and format() to the mixed-in type.
        """
    
    class StrEnum(str, ReprEnum):
        """
        Enum where members are also (and must be) strings
        """

        def __new__(cls, *values):
            "values must already be of type `str`"
            if len(values) > 3:
                raise TypeError('too many arguments for str(): %r' % (values, ))
            if len(values) == 1:
                # it must be a string
                if not isinstance(values[0], str):
                    raise TypeError('%r is not a string' % (values[0], ))
            if len(values) >= 2:
                # check that encoding argument is a string
                if not isinstance(values[1], str):
                    raise TypeError('encoding must be a string, not %r' % (values[1], ))
            if len(values) == 3:
                # check that errors argument is a string
                if not isinstance(values[2], str):
                    raise TypeError('errors must be a string, not %r' % (values[2]))
            value = str(*values)
            member = str.__new__(cls, value)
            member._value_ = value
            return member

from pwinput import pwinput


class FileClass(StrEnum):
    SINIF = 'sinif'
    DERS = 'ders'
    ODEV = 'odev'

@dataclass
class Course:
    name: str
    crn: str
    url: str
    estimated_size: int = 0
    downloaded_size: int = 0

    @property
    def folder_name(self) -> str:
        return f'{self.name} [{self.crn}]'
    
    @classmethod
    def from_folder_name(cls, folder_name: str, url: str) -> Self:
        # e.g. folder_name = 'BIL 112E [24925]'
        name, crn = folder_name.split('[')
        crn = crn[:-1]
        return cls(name, crn, url)

@dataclass
class NinovaPath:
    name: str
    url: str
    icon: str
    estimated_size: Optional[int]
    datetime: Optional[str]
    parent: Optional[Self]
    course: Optional[Course]
    file_class: Optional[FileClass]
    path: Optional[Path] = None

    @property
    def hash(self) -> str:
        return hashlib.sha256(f"{self.name!s}{self.datetime!s}{self.url!s}{self.file_class!s}".encode()).hexdigest()


def hidden_prompt_func(prompt: str) -> str:
    try:
        return pwinput(prompt)
    except Exception:
        return getpass(prompt)

def convert_size_to_int(size: str) -> int:
    # take a string like '5 MB', '140 KB' or '387 Bayt'
    # and convert them into relevant byte strings
    if not size:
        return 0
    _list = size.split()
    int_size = int(_list[0])
    if _list[1].upper() == 'TB':
        int_size *= 1024
        _list[1] = 'GB'
    if _list[1].upper() == 'GB':
        int_size *= 1024
        _list[1] = 'MB'
    if _list[1].upper() == 'MB':
        int_size *= 1024
        _list[1] = 'KB'
    if _list[1].upper() == 'KB':
        int_size *= 1024
        _list[1] = 'Bayt'
    return int_size