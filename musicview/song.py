#  musicview, (re)discover your music library.
#  Copyright (C) 2018 Peijun Ma
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.

import signal
from collections import Iterable
from subprocess import DEVNULL, PIPE, Popen, run
from typing import NamedTuple

from mutagen import File, MutagenError

from .misc import format_time


class MetaData(NamedTuple):
    path: str
    title: str
    genre: str
    artist: str
    album: str
    length: float

    @classmethod
    def empty(cls, path):
        """
        Return an empty MetaData entry
        Args:
            path: path to the song

        Returns:
            empty MetaData entry
        """
        return cls(path, None, None, None, None, None)

    def format_time(self):
        """
        Format self.length into human readable string
        Returns:
            The time formatted
        """
        if self.length:
            return format_time(self.length)
        else:
            return None

    def format(self) -> list:
        """
        Format self into a pretty printable target,
        with one line per list
        Returns:
            the formatted text
        """
        title = self.title or self.path
        length = self.format_time()
        lst = list(self[1:])
        lst[0] = title
        lst[-1] = length
        return [
            '{}: {}'.format(s, v) for s, v in
            zip(['Title', 'Genre', 'Artist', 'Album', 'Length'], lst)
            if v
        ]


class Song:
    def __init__(self, metadata: MetaData, fav: bool, listen_count: int):
        """
        Initailize this song
        Args:
            metadata: Song metadata
            fav: Song favourited or not
            listen_count: Song listen count
        """
        self.meta = metadata
        self.fav = fav
        self.listen_count = listen_count
        self.playing_proc = None
        self.paused = False

    def __bool__(self):
        return self.playing_proc is not None

    def toggle_favourite(self, conn):
        """
        Toggle favourite status of this song
        Args:
            conn: Database connection
            lock: Database lock
        """
        self.fav = not self.fav
        conn.execute(
            'UPDATE library SET favourite=? WHERE path=?',
            (self.fav, self.meta.path)
        )
        conn.commit()

    def play(self, ffplay) -> Popen:
        """
        Args:
            ffplay: ffplay binary location

        Returns:
            Process that's playing this song
        """
        self.playing_proc = Popen(
            [ffplay, '-nodisp', '-autoexit', self.meta.path],
            stderr=DEVNULL
        )
        return self.playing_proc

    def toggle_pause(self) -> bool:
        """
        (un)pause this song

        Returns:
            wether this song is paused or not
        """
        if self.paused:
            self.playing_proc.send_signal(signal.SIGCONT)
            self.paused = False
        else:
            self.playing_proc.send_signal(signal.SIGSTOP)
            self.paused = True
        return self.paused

    def stop(self):
        """
        Stop playing this song
        """
        if self.playing_proc:
            self.playing_proc.kill()
            self.playing_proc = None


def tag_to_str(tag):
    """
    Function to turn a tag into a string.
    Args:
        tag: the tag value
    Returns: the tag as a string
    """
    if isinstance(tag, str):
        res = tag.strip()
    elif isinstance(tag, Iterable):
        res = ','.join(tag).strip()
    else:
        res = None
    if isinstance(res, str):
        return res or None
    return None
