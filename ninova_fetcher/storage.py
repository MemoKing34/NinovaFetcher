import hashlib
import sqlite3
from pathlib import Path

from .helper import FileClass, NinovaPath, Course


class Storage:
    def __init__(self, filename: str | Path, downloads_path: Path):
        self._downloads_path = downloads_path
        self._connection = sqlite3.connect(filename)
        self._cursor = self._connection.cursor()
        self._cursor.execute('CREATE TABLE IF NOT EXISTS files (hash TEXT, name TEXT, filepath TEXT, datetime TEXT, url TEXT, fileclass TEXT);')
        self._connection.commit()

    def add_file(self, hash: str, name: str, filepath: str | Path, datetime: str, url: str, fileclass: FileClass) -> None:
        self._cursor.execute('INSERT INTO files (hash, name, filepath, datetime, url, fileclass) VALUES (?, ?, ?, ?, ?, ?)',
                             (hash, name, str(filepath), datetime, url, fileclass))
        
    def add_ninova_path(self, ninova_path: NinovaPath) -> None:
        return self.add_file(ninova_path.hash, ninova_path.name, ninova_path.path.relative_to(self._downloads_path),
                             ninova_path.datetime, ninova_path.url, ninova_path.file_class)
    
    def get_file_by_hash(self, hash: str) -> NinovaPath:
        # TODO: add cache
        self._cursor.execute('SELECT * FROM files WHERE hash = ?', (hash,))
        if not (rows := self._cursor.fetchall()):
            raise FileNotFoundError(f"File with hash {hash} not found")
        row = rows[0]
        _hash, name, filepath, datetime, url, fileclass = row
        path = Path(filepath)
        folder_name = str(path.parents[-2])
        course_url = f"{'/'.join(url.split('/')[:3])}"
        return NinovaPath(
            name=name,
            url=url,
            icon='',
            datetime=datetime,
            parent=None,
            course=Course.from_folder_name(folder_name, course_url),
            file_class=fileclass,
            path=self._downloads_path / path,
        )

    def close(self):
        try:
            self._cursor.close()
        except Exception:
            pass
        self._connection.close()
        
    def commit(self):
        #self._connection.autocommit
        self._connection.commit()

    def __del__(self):
        self.close()

if __name__ == "__main__":
    import json
    database_path = Path("downloads") / 'ninova.db'
    jsondata_path = Path("downloads") / 'data.json'
    first_time = False
    if not database_path.exists():
        first_time = True
    self = storage = Storage(database_path, database_path.parent)
    if jsondata_path.exists() and first_time:
        with jsondata_path.open() as jfile:
            data: dict[str, dict[FileClass, list[tuple[str, str, str, str]]]] = json.load(jfile)
        for course, value in data.items():
            for fileclass, liste in value.items():
                for chunk in liste:
                    name, filepath, datetime, url = chunk
                    hash = hashlib.sha256(f"{name!s}{datetime!s}{url!s}{fileclass!s}".encode()).hexdigest()
                    storage.add_file(hash, name, filepath, datetime, url, fileclass)
        storage.commit()
        storage.close()
    