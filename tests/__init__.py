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

from contextlib import contextmanager
from os import environ, walk
from pathlib import Path


def get_files(p):
    for dir, __, fs in walk(p):
        for f in fs:
            if f.endswith('.txt'):
                continue
            yield Path(dir) / f


def file_count(p):
    return len(list(get_files(p)))


@contextmanager
def export(envvars):
    try:
        environ.update(envvars)
        yield
    finally:
        for key in envvars:
            del environ[key]


HERE = Path(__file__).parent

SONGS = HERE / 'songs'
HAS_LEN = SONGS / 'has_len'
NO_LEN = SONGS / 'no_len'
FULL_DATA = HAS_LEN / 'full_data'
NON_FULL_DATA = HAS_LEN / 'non_full_data'
SPAM = SONGS / 'spam'

SONG_COUNT = file_count(SONGS)
HAS_LEN_COUNT = file_count(HAS_LEN)
NO_LEN_COUNT = file_count(NO_LEN)
FULL_DATA_COUNT = file_count(FULL_DATA)
NON_FULL_DATA_COUNT = file_count(NON_FULL_DATA)
