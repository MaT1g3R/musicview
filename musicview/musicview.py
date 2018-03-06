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
from collections import Iterable, namedtuple
from curses import wrapper
from functools import partial
from itertools import chain
from pathlib import Path
from shutil import which
from sqlite3 import Connection, connect
from subprocess import DEVNULL, PIPE, Popen, run
from sys import stderr
from threading import RLock, Thread
from typing import Tuple

import click
import progressbar as pg
from halo import Halo
from mutagen import File, MutagenError


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

    def format(self):
        title = self.title or self.path
        if self.length:
            mins, secs = divmod(self.length, 60)
            length = '{}:{:02d}'.format(int(mins), round(secs))
        else:
            length = None
        lst = list(self[1:])
        lst[0] = title
        lst[-1] = length
        return '\n'.join(
            ['{}: {}'.format(s, v) for s, v in
             zip(['Title', 'Genre', 'Artist', 'Album', 'Length'], lst) if v]
        )


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


def song_metadata(path: str):
    """
    Get a song's metadata
    Args:
        path: path to the song
    Returns:
        The song's metadata
    """

    def to_string(tag):
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

    try:
        tags = File(path, easy=True)
    except MutagenError:
        return MetaData.empty(path)
    else:
        if not tags:
            return MetaData.empty(path)
        get = lambda t, s: t.get(s, t.get(s.upper()))
        title = to_string(get(tags, 'title'))
        genre = to_string(get(tags, 'genre'))
        artist = to_string(get(tags, 'artist'))
        album = to_string(get(tags, 'album'))
        length = tags.info.length
        return MetaData(path, title, genre, artist, album, length)


def update_db(path: Path, conn: Connection, ffplay: str):
    """
    Update the database
    Args:
        path: path to the music library
        conn: database connection
        ffplay: ffplay binary
    """
    formats = set(get_supported_formats(ffplay))
    cur = conn.cursor()
    with Halo(text='Getting songs...', spinner='dots'):
        songs = set(map(str, get_songs(path, formats)))
        cur.execute('CREATE TEMP TABLE tmp (path VARCHAR PRIMARY KEY);')
        cur.executemany('INSERT INTO tmp(path) VALUES (?);', ((s,) for s in songs))
        cur.execute('DELETE FROM library WHERE path NOT IN (SELECT path FROM tmp);')
        cur.execute('DROP TABLE tmp;')

    bar = pg.ProgressBar(
        widgets=[
            'Updating...',
            '(',
            pg.Percentage(),
            ' ',
            pg.Counter(),
            '/',
            str(len(songs)),
            ' )',
            pg.Bar(marker='█'),
            '[',
            pg.Timer(),
            ' ',
            pg.AdaptiveETA(),
            ']'
        ]
    )
    for song in bar(songs):
        metadata = song_metadata(song)
        cur.execute('SELECT * FROM library WHERE path=?', (metadata.path,))
        if not cur.fetchone():
            cur.execute(
                """
                INSERT INTO library (path, title, genre, artist, album, length)
                VALUES (?, ?, ?, ?, ?, ?);
                """, metadata
            )
        else:
            cur.execute(
                """
                UPDATE library SET
                title = ?,
                genre = ?,
                artist = ?,
                album = ?,
                length = ?
                WHERE path=?;
                """, tuple(chain(metadata[1:], metadata[:1]))
            )
    conn.commit()
    cur.close()


def init_db(path: Path, conn: Connection, ffplay: str):
    """
    Initialize the database
    Args:
        path: path to the music directory
        conn: sqlite3 connection
        ffplay: ffplay binary
    """
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS library (
        path VARCHAR PRIMARY KEY,
        title VARCHAR,
        genre VARCHAR,
        artist VARCHAR,
        album VARCHAR,
        length REAL,
        favourite BOOLEAN DEFAULT 0 NOT NULL,
        listen_count INT DEFAULT 0
        );
        """
    )
    conn.commit()
    update_db(path, conn, ffplay)


def check_path(path):
    """
    Check if a path is a valid directory
    Args:
        path: the path to check
    """
    if not path.is_dir():
        print('{} is not a valid directory!'.format(path), file=stderr)
        exit(1)


def get_connection(data, name, must_exist) -> Tuple[bool, Connection]:
    """
    Get a database connection
    Args:
        data: path to the data directory
        name: name of the music library
        must_exist: True to assert the database already exists

    Returns:
        Wether the database is newly initialized and the connection
    """
    db_file = data / '{}.db'.format(name)
    init = not db_file.is_file()
    if must_exist and init:
        print('Library {} does not exist!'.format(name), file=stderr)
        exit(1)
    db_file.touch()
    conn = connect(str(db_file))
    return init, conn


def next_song(conn) -> Tuple[MetaData, tuple]:
    """
    Select the next song to play based on play counts
    Args:
        conn: the database connection
    Returns:
        metadata of the next song to play
    """
    cur = conn.cursor()
    cur.execute(
        """
        SELECT * FROM library
        WHERE listen_count=(SELECT min(listen_count) FROM library)
        ORDER BY RANDOM() LIMIT 1
        """
    )
    next = cur.fetchone()
    cur.execute(
        """
        UPDATE library SET 
        listen_count = listen_count + 1
        WHERE path=?
        """, (next[0],)
    )
    conn.commit()
    cur.close()
    return MetaData(*next[:-2]), next[-2:]


class Player:
    def __init__(self, data, name, ffplay, conn, stdscr):
        self.ffplay = ffplay
        self.data = data
        self.name = name
        self.conn = conn
        self.stdscr = stdscr
        self.cur_song = None
        self.cur_fav = False
        self.cur_count = 0
        self.seek = 0
        self.ui_thread = None
        self.lock = RLock()
        self.playing_proc = None
        self.stopped = False

        self.paused = False

    def _play(self):
        return Popen(
            [self.ffplay, self.cur_song.path, '-nodisp', '-autoexit', '-ss', str(self.seek)],
            stderr=DEVNULL,
            close_fds=True
        )

    def ui(self):
        keymap = {'p': 'play', '>': 'skip', 'f': 'favourite', 'q': 'quit'}
        _, conn = get_connection(self.data, self.name, True)
        while True:
            cmd = keymap.get(self.stdscr.getkey())
            if cmd == 'play':
                self.toggle()
            elif cmd == 'skip':
                self.play_next()
            elif cmd == 'favourite':
                self.favourite(conn)
            elif cmd == 'quit':
                self.stopped = True
                self.playing_proc.kill()
                self.stdscr.clear()
                return

    def play_next(self):
        self.playing_proc.kill()

    def toggle(self):
        if self.paused:
            self.playing_proc.send_signal(signal.SIGCONT)
        else:
            self.playing_proc.send_signal(signal.SIGSTOP)
        self.paused = not self.paused
        self.display()

    def start(self):
        ui = Thread(target=self.ui, name='ui', daemon=True)
        self.ui_thread = ui
        ui.start()
        while True:
            if self.stopped:
                return
            self.paused = False
            with self.lock:
                self.cur_song, (self.cur_fav, self.cur_count) = next_song(self.conn)
                self.cur_count += 1
            self.display()
            with self._play() as proc:
                self.playing_proc = proc
                proc.wait()

    def favourite(self, conn):
        with self.lock:
            conn.execute(
                'UPDATE library SET favourite=? WHERE path=?',
                (not self.cur_fav, self.cur_song.path)
            )
            conn.commit()
        self.cur_fav = not self.cur_fav
        self.display()

    def display(self):
        self.stdscr.clear()
        self.stdscr.addstr(
            '\n'.join(
                ['Paused' if self.paused else 'Playing',
                 self.cur_song.format(),
                 'Favourite: {}'.format(bool(self.cur_fav)),
                 'Play count: {}'.format(self.cur_count)]
            )
        )
        self.stdscr.refresh()


def play_music(data, name, conn, ffplay, stdscr):
    """
    Play some music!
    Args:
        data: path to the dirctory containg database files
        name: name of the music library
        conn: database connection
        ffplay: ffplay binary
        stdscr: curses screen
    """
    stdscr.clear()
    player = Player(data, name, ffplay, conn, stdscr)
    player.start()


data_opt = click.option(
    '-d', '--data', default=Path.home() / '.musicview', type=Path,
    help='Path to directory containing data and config files'
)

path_opt = click.option(
    '-p', '--path', default=Path.cwd(), type=Path,
    help='Path to the directory of your music library.'
)


@click.group()
@click.pass_obj
def cli(obj):
    """musicview, (re)discover your music library"""
    ffplay = which('ffplay')
    if not ffplay:
        print('ffplay not found!', file=stderr)
        exit(1)

    obj['ffplay'] = ffplay


@click.command(name='list')
@data_opt
def list_(data: Path):
    """List existing music libraries"""
    check_path(data)
    lst = [
        p.name.rstrip('.db')
        for p in data.iterdir()
        if p.name.endswith('.db')
    ]
    if lst:
        print('\n'.join(lst))
    else:
        print('There are currently no music libraries!')


@click.command()
@path_opt
@data_opt
@click.argument('name')
@click.pass_obj
def play(obj, path: Path, data: Path, name: str):
    """Start playing music"""
    check_path(path)
    data.mkdir(exist_ok=True, parents=True)
    ffplay = obj['ffplay']

    init, conn = get_connection(data, name, False)
    with conn:
        if init:
            init_db(path, conn, ffplay)
        wrapper(partial(play_music, data, name, conn, ffplay))


@click.command()
@data_opt
@click.argument('name')
def delete(data: Path, name: str):
    """Delete a music library"""
    check_path(data)
    to_del = data / '{}.db'.format(name)
    if input('Delete {}? y/n '.format(name)).lower() != 'y':
        print('Delete aborted', file=stderr)
        exit(1)
    try:
        to_del.unlink()
    except OSError as e:
        print(e, file=stderr)
    else:
        print('{} deleted!'.format(name))


@click.command()
@path_opt
@data_opt
@click.argument('name')
@click.pass_obj
def update(obj, path: Path, data: Path, name: str):
    """Update an existing music library"""
    check_path(path)
    ffplay = obj['ffplay']

    if not name in map(lambda p: p.name.rstrip('.db'), data.iterdir()):
        print('Library "{}" does not exist!'.format(name), file=stderr)
        exit(1)

    _, conn = get_connection(data, name, True)
    with conn:
        update_db(path, conn, ffplay)


cli.add_command(list_)
cli.add_command(play)
cli.add_command(delete)
cli.add_command(update)

if __name__ == '__main__':
    cli(obj={})
