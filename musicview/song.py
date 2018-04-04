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
from subprocess import DEVNULL, Popen
from time import time
from typing import NamedTuple, Optional

from mutagen import File, MutagenError

from .misc import format_time, get_ffmpeg_duration


class MetaData(NamedTuple):
    path: str
    title: str
    genre: str
    artist: str
    album: str
    length: float

    @classmethod
    def from_path(cls, ffmpeg: str, path: str) -> Optional['MetaData']:
        """
        Get song metadata from path
        Args:
            ffmpeg: ffmpeg binary
            path: path to the song
        Returns:
            Song metadata if able to find its length,
            otherwise None
        """
        get = lambda t, s: t.get(s, t.get(s.upper()))
        try:
            tags = File(path, easy=True) or {}
        except MutagenError:
            tags = {}
        title = tag_to_str(get(tags, 'title'))
        genre = tag_to_str(get(tags, 'genre'))
        artist = tag_to_str(get(tags, 'artist'))
        album = tag_to_str(get(tags, 'album'))
        length = tags.info.length if tags else None
        length = length or get_ffmpeg_duration(ffmpeg, path)
        return cls(path, title, genre, artist, album, length) if length else None

    def format(self) -> list:
        """
        Format self into a pretty printable target,
        with one line per list
        Returns:
            the formatted text
        """
        title = self.title or self.path
        length = format_time(self.length)
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

        self.unpause_time = 0
        self._time_played = 0

    def __bool__(self):
        return self.playing_proc is not None

    @property
    def time_played(self) -> float:
        """Return how long this song has been playing in seconds"""
        if not self:
            return 0
        if self.paused:
            return self._time_played
        else:
            return self._time_played + time() - self.unpause_time

    @property
    def is_done(self) -> bool:
        """Return wether this song is done playing"""
        return self.time_played > self.meta.length

    def toggle_favourite(self, conn):
        """
        Toggle favourite status of this song

        Args:
            conn: Database connection
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
        self.unpause_time = time()
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
            self.unpause_time = time()
        else:
            self.playing_proc.send_signal(signal.SIGSTOP)
            self.paused = True
            self._time_played += time() - self.unpause_time
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
