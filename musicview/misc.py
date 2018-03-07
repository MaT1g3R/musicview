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

from pathlib import Path
from subprocess import DEVNULL, PIPE, run


def format_time(seconds):
    """
    Format time in secods into human readable string
    Args:
        seconds: time in seconds
    Returns:
        The time formatted
    """
    mins, secs = divmod(seconds, 60)
    return '{}:{:02d}'.format(int(mins), round(secs))


def get_supported_formats(ffplay):
    """
    Get formats supported by `ffplay`
    Args:
        ffplay: Path to ffplay binary

    Returns:
        Generator of supported formats
    """
    proc = run([ffplay, '-formats'], stderr=DEVNULL, stdout=PIPE)
    for line in proc.stdout.decode().splitlines():
        line = line.strip().split()
        if len(line) >= 3 and line[0].startswith('D'):
            yield from line[1].split(',')


def get_songs(path: Path, formats):
    """
    Recursively get songs under path
    Args:
        path: path to the music directory
        formats: set of supported audio formats
    Returns:
        Generator of all song paths under path
    """
    for sub in path.iterdir():
        if sub.is_file():
            if sub.suffix.lstrip('.') in formats:
                yield sub.absolute()
        elif sub.is_dir():
            yield from get_songs(sub, formats)
