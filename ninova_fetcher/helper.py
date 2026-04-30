import hashlib
from dataclasses import dataclass
from enum import StrEnum, auto
from getpass import getpass
from pathlib import Path
from typing import NamedTuple, Self

from pwinput import pwinput


class FileClass(StrEnum):
    SINIF = auto()
    DERS = auto()
    ODEV = auto()

class Course(NamedTuple):
    name: str
    crn: str
    url: str

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
    datetime: str | None
    parent: Self | None
    course: Course | None
    file_class: FileClass | None
    path: Path | None = None

    @property
    def hash(self) -> str:
        return hashlib.sha256(f"{self.name!s}{self.datetime!s}{self.url!s}{self.file_class!s}".encode()).hexdigest()


def hidden_prompt_func(prompt: str) -> str:
    try:
        return pwinput(prompt)
    except Exception:
        return getpass(prompt)