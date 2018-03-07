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

from collections import Iterable, namedtuple
from subprocess import DEVNULL, PIPE, run

from mutagen import File, MutagenError

from .misc import format_time


class MetaData(namedtuple('MetaData', ['path', 'title', 'genre', 'artist', 'album', 'length'])):
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
        return ['{}: {}'.format(s, v) for s, v in
                zip(['Title', 'Genre', 'Artist', 'Album', 'Length'], lst)
                if v]


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


def song_metadata(ffmpeg, path: str):
    """
    Get a song's metadata
    Args:
        ffmpeg: ffmpeg binary
        path: path to the song
    Returns:
        The song's metadata
    """

    try:
        tags = File(path, easy=True)
    except MutagenError:
        res = MetaData.empty(path)
    else:
        if not tags:
            res = MetaData.empty(path)
        else:
            get = lambda t, s: t.get(s, t.get(s.upper()))
            title = tag_to_str(get(tags, 'title'))
            genre = tag_to_str(get(tags, 'genre'))
            artist = tag_to_str(get(tags, 'artist'))
            album = tag_to_str(get(tags, 'album'))
            length = tags.info.length
            res = MetaData(path, title, genre, artist, album, length)

    if res.length is None:  # Couldn't read length from mutagen, fallback to ffmpeg
        proc = run([ffmpeg, '-i', path], stdout=DEVNULL, stderr=PIPE)
        err = proc.stderr.decode().splitlines()
        for line in err:
            line = line.strip().lower()
            if line.startswith('duration'):
                try:
                    time = line.split()[1].rstrip(',')
                    hour, minutes, seconds = time.split(':')
                    total = 60 * 60 * int(hour) + 60 * int(minutes) + float(seconds)
                except Exception:
                    return None
                else:
                    return MetaData(*res[:-1], total)
        return None
    else:
        return res
