#!/usr/bin/env python3
#from __future__ import annotations
import json
import logging
import multiprocessing as mp
import os
import re
import sys
from pathlib import Path
from typing import Any, TypeAlias
from unittest import case

import dotenv
import requests
import click
from bs4 import BeautifulSoup, element
from pwinput import pwinput
from rich.logging import RichHandler
from rich.progress import Progress, SpinnerColumn, TimeElapsedColumn

from .helper import Course, FileClass, NinovaPath, hidden_prompt_func, convert_size_to_int
from .storage import Storage
from . import __version__

BASE_URL = "https://ninova.itu.edu.tr"
SINIF_DOSYALARI_URL_EXTENSION = "/SinifDosyalari"
DERS_DOSYALARI_URL_EXTENSION = "/DersDosyalari"
ODEVLER_URL_EXTENSION = "/Odevler"
if sys.version_info >= (3, 12):
    type PathList = list[Path | 'PathList']
else:
    PathList: TypeAlias = list[Path | 'PathList']

DOTENV_PATH: Path = Path(".env")

# from yt-dlp
# Templates for internet shortcut files, which are plain text files.
DOT_URL_LINK_TEMPLATE = '''\
[InternetShortcut]
URL={url}
'''

DOT_WEBLOC_LINK_TEMPLATE = '''\
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
\t<key>URL</key>
\t<string>{url}</string>
</dict>
</plist>
'''

DOT_DESKTOP_LINK_TEMPLATE = '''\
[Desktop Entry]
Encoding=UTF-8
Name={filename}
Type=Link
URL={url}
Icon=text-html
'''

LINK_TEMPLATES = {
    'url': DOT_URL_LINK_TEMPLATE,
    'desktop': DOT_DESKTOP_LINK_TEMPLATE,
    'webloc': DOT_WEBLOC_LINK_TEMPLATE,
}

log = logging.getLogger(__name__)


def sanitize_filename(filename: str, force: bool = False) -> str:
    # replaces unsupported chars with #
    # again thanks to yt-dlp
    REPL = '#'
    if sys.platform != 'win32' and not force:
        return filename.replace('/', REPL)
    return re.sub(r'[/<>:"\|\\?\*]|[\s.]$', REPL, filename)


class Ninova:
    def __init__(self, downloads_path: Path = None, uploads_path: Path = None):
        self.session = requests.Session()
        self.progress = Progress(SpinnerColumn(), *Progress.get_default_columns(), TimeElapsedColumn())
        self.downloads_path = downloads_path or Path("downloads")
        self.uploads_path = uploads_path or Path("uploads")
        self.downloads_path.mkdir(exist_ok=True)
        self.uploads_path.mkdir(exist_ok=True)
        self.downloads_data = Storage(self.downloads_path / 'ninova.db', self.downloads_path)
        self.uploads_data = {}

    def dump_data(self):
        self.downloads_data.commit()
        self.downloads_data.close()

    def load_data(self):
        pass

    @staticmethod
    def _object_hook(dct: dict[Any, Any]):
        if 'sinif' in dct:
            for file_class in FileClass:
                for lst in dct[file_class]:
                    lst[0] = Path(lst[0])
        return dct

    # Logs in with username and password
    def login(self, username: str, password: str) -> "requests.Session":
        self.progress.log(f"Logging as user {username}...")
        # Finds the required url after some redirects
        response = self.session.get(f"{BASE_URL}/Kampus1", timeout=2)  # For hidden inputs
        login_url = response.url

        # Finds hidden inputs and adds them into the payload for login
        soup_login = BeautifulSoup(response.text, "html.parser")
        login_tokens: "element.ResultSet[element.Tag]" = soup_login.find_all("input")

        payload = {}
        # Fills the payload
        for token in login_tokens:
            match_username = re.search(r".*username.*", token["id"], re.IGNORECASE)
            match_password = re.search(r".*password.*", token["id"], re.IGNORECASE)
            if match_username:
                payload[token["name"]] = username
            elif match_password:
                payload[token["name"]] = password
            elif token.has_attr("value"):
                payload[token["name"]] = token["value"]
        # Logs in
        res_log = self.session.post(login_url, data=payload)
        # Checks if the user is redirected meaning that the credentials are valid
        if not res_log.history:
            raise ConnectionError("Please check your login credentials")
        log.debug("Login successful.")
        return self.session


    def get_courses(self) -> list[Course]:
        """Returns student's courses information with an order of name, crn and
        url

        Example return: [('BIL 112E', '24925', '/Sinif/12667.118786'), ...]

        crn value is also a string because havuz courses don't have a crn value,
        and they return a 'Havuz' value
        """
        response = self.session.get(f"{BASE_URL}/Kampus1")
        soup = BeautifulSoup(response.text, "html.parser")
        def get_info_from_class(tag: "element.Tag") -> Course:
            return Course(tag.find("strong").text, tag.find("a").text.split()[-1], tag.find("a").attrs['href'])
        return [get_info_from_class(tag) for tag in soup.find("ul").children if tag != "\n"]


    def download_course(self, course: Course) -> None:
        path = self.downloads_path / course.folder_name
        path.mkdir(parents=True, exist_ok=True)
        self.progress.log(f"Downloading course {course.name!r} with crn {course.crn}")
        #self.downloads_data[course.folder_name] = {'sinif': [], 'ders': [], 'odev': []}
        self._download(course.url + SINIF_DOSYALARI_URL_EXTENSION, path / "Sınıf Dosyaları", course, 'sinif')
        self._download(course.url + DERS_DOSYALARI_URL_EXTENSION, path / "Ders Dosyaları", course, 'ders')
        self._download_homeworks(course.url + ODEVLER_URL_EXTENSION, path / "Ödevler", course, 'odev')
        self.downloads_data.commit() # Just lets ensure this

    @staticmethod
    def parse_ninova_path(tag: "element.Tag", parent: NinovaPath | None = None, course: Course | None = None, file_class: FileClass | None = None) -> NinovaPath:
        datetime: str | None = None
        estimated_size: int = 0
        if _list := tag.find_all("td"):
            datetime = _list[-1].text.strip()
        if len(_list) > 1:
            estimated_size = convert_size_to_int(_list[-2].text.strip())
        if parent is None:
            course.estimated_size += estimated_size
        return NinovaPath(sanitize_filename(tag.find("a").text.strip()), tag.find("a").attrs["href"], tag.find("img").attrs["src"], estimated_size, datetime, parent, course, file_class)

    @staticmethod
    def create_link_file(folder: Path, filename_without_suffix: str, url: str) -> Path:
        link_type = ('webloc' if sys.platform == 'darwin'
                            else 'desktop' if sys.platform.startswith('linux')
                            else 'url')
        linkpath = folder / (filename_without_suffix + f".{link_type}")
        template_vars = {'url': url}
        if link_type == 'desktop':
            template_vars['filename'] = linkpath.stem
        linkpath.write_text(LINK_TEMPLATES[link_type].format_map(template_vars),
                            encoding='utf-8', newline='\r\n' if link_type == 'url' else '\n')
        return linkpath


    def _download(self, _url: str, download_path: Path, course: Course, file_class: FileClass, parent: NinovaPath | None = None):
        response = self.session.get(BASE_URL + _url)
        soup = BeautifulSoup(response.text, "html.parser")
        download_path.mkdir(parents=False, exist_ok=True)
        try:
            ninova_path_list: list[NinovaPath] = [self.parse_ninova_path(tag, parent, course, file_class) for tag in soup.find("tbody").children if tag != "\n"][1:]
        except AttributeError:
            return
        return self.__download(ninova_path_list, download_path, course, file_class)
        
    def __download(self, ninova_path_list: list[NinovaPath], download_path: Path, course: Course, file_class: FileClass):
        for ninova_path in ninova_path_list:
            log.debug(f"Downloading {ninova_path.name!r}")
            if ninova_path.icon.endswith("folder.png"):
                ninova_path.path = download_path / ninova_path.name
                self._download(ninova_path.url, ninova_path.path, course, file_class, ninova_path)
            elif ninova_path.icon.endswith("link.png"):
                # This means it's a url file, and we have to specify it
                # because on the website its actually not a file
                # it's just a redirect url
                r = self.session.get(BASE_URL + ninova_path.url, allow_redirects=False)
                url_file_content = r.headers.get("Location") if r.is_redirect else r.url
                ninova_path.path = self.create_link_file(download_path, ninova_path.name, url_file_content)
            else:
                try:
                    fake_np: NinovaPath = self.downloads_data.get_file_by_hash(ninova_path.hash)
                    ninova_path.path = fake_np.path
                    if ninova_path.path.exists():
                        log.debug(f"{ninova_path.name!r} found in database not downloading.")
                        filesize = ninova_path.path.stat().st_size
                        continue
                    log.debug(f"{ninova_path.name!r} found in database but file does not exist. Continuing download...")
                except FileNotFoundError:
                    pass
                r = self.session.get(BASE_URL + ninova_path.url)
                _offset = r.headers.get("content-disposition", "").index("filename=") + 9
                filename = r.headers.get("content-disposition", "")[_offset:].encode("iso-8859-9").decode("utf-8")
                filesize = int(r.headers.get("Content-Length", 0))
                if not filename:
                    filename = ninova_path.name
                ninova_path.path = download_path / filename
                ninova_path.path.write_bytes(r.content)
            self.downloads_data.add_ninova_path(ninova_path)
            log.debug(f"Downloaded: {ninova_path.path!r}")

    def _download_homeworks(self, _url: str, download_path: Path, course: Course, file_class: FileClass):
        response = self.session.get(BASE_URL + _url)
        soup = BeautifulSoup(response.text, "html.parser")
        download_path.mkdir(exist_ok=True)
        sayfa_icerik: "element.Tag" = soup.find(attrs={'id': "SayfaIcerik"})
        odevler: list["element.Tag"] = sayfa_icerik.find_all("td")
        try:
            odev_urls = [odev.find("a") for odev in odevler]
        except AttributeError:
            return
        for odev_url in odev_urls:
            if odev_url: # Sometimes odev_url might be None
                self._download_homework(odev_url.attrs['href'], download_path / sanitize_filename(odev_url.text.strip()), course, file_class)

    def _download_homework(self, _url: str, download_path: Path, course: Course, file_class: FileClass):
        response = self.session.get(BASE_URL + _url)
        soup = BeautifulSoup(response.text, "html.parser")
        download_path.mkdir(exist_ok=True)
        title: "element.Tag" = soup.find(attrs={'id': "ctl00_pnlHeader"})
        form2: "element.Tag" = soup.find(attrs={'class': "form2"})
        (download_path / (title.text.strip() + ".odev.txt")).write_text(form2.text.strip(), encoding='utf-8')
        self.create_link_file(download_path, 'Ödevi Yükle.odev', BASE_URL + _url + '/OdevGonder')

        tables: list["element.Tag"] = form2.find_all("table")
        files: list["element.Tag"] = tables[2].find_all("tr")[1:]
        if files:
            ninova_path_list: list[NinovaPath] = [self.parse_ninova_path(tag, None, course, file_class) for tag in files]
            return self.__download(ninova_path_list, download_path, course, file_class)

def load_dotenv(dotenv_path: str | Path = DOTENV_PATH) -> bool:
    return dotenv.load_dotenv(dotenv_path, override=True)

def create_dotenv(dotenv_path: str | Path = DOTENV_PATH, **kwargs):
    dotenv.set_key(dotenv_path, "ITU_USERNAME", kwargs.get('username', ''))
    dotenv.set_key(dotenv_path, "ITU_PASSWORD", kwargs.get('password', ''))
    dotenv.set_key(dotenv_path, "SINGLE_THREAD", str(kwargs.get('single_thread', '')))

#monkeypatch
click.termui.hidden_prompt_func = hidden_prompt_func

@click.command()
@click.option('--username', envvar='ITU_USERNAME', prompt=True)
@click.password_option('--password', envvar='ITU_PASSWORD', confirmation_prompt=False)
@click.option('--single-thread/--no-single-thread', default=False, envvar='SINGLE_THREAD', type=bool)
@click.option('-d', '--downloads-path', type=click.Path(exists=False, file_okay=False, path_type=Path), default=Path('downloads'))
@click.option('--uploads-path', type=click.Path(exists=False, file_okay=False, path_type=Path), default=Path('uploads'))
@click.option('-v', '--verbose', count=True)
@click.version_option(__version__, prog_name='NinovaFetcher')
def main(username: str, password: str, single_thread: bool, downloads_path: Path, uploads_path: Path, verbose: int):
    # setup config
    #logging.basicConfig(format="[%(asctime)s] %(levelname)s:%(name)s:%(message)s")
    rich_handler = RichHandler(tracebacks_show_locals=True)
    logging.basicConfig(format="%(message)s", datefmt="[%X]", handlers=[rich_handler])
    if verbose == 1:
        log.setLevel(logging.INFO)
        rich_handler.setLevel(logging.INFO)
    elif verbose == 2:
        import rich.traceback
        log.setLevel(logging.DEBUG)
        rich_handler.setLevel(logging.DEBUG)
        rich.traceback.install(show_locals=True)
    elif verbose >= 3:
        logging.basicConfig(level=logging.DEBUG)
        rich_handler.setLevel(logging.DEBUG)
    ninova = Ninova(downloads_path, uploads_path)
    ninova.load_data()
    with ninova.progress:
        task3 = ninova.progress.add_task("[yellow]Downloading", total=None)
        ninova.login(username, password)
        ninova.progress.log("Download started.")
        courses = ninova.get_courses()
        if True: # TODO: implement multithreading/multiprocessing
            for course in courses:
                ninova.download_course(course)
        else:
            with mp.Pool() as pool:
                pool.map(ninova.download_course, courses)
        ninova.progress.update(task3)
    ninova.dump_data()
    if not DOTENV_PATH.exists():
        create_dotenv(DOTENV_PATH, username=username, password=password, single_thread=single_thread)
    click.echo("Download successfull.")

if __name__ == "__main__":
    load_dotenv(DOTENV_PATH)
    main()