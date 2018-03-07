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

from itertools import chain
from pathlib import Path
from sqlite3 import Connection, connect
from sys import stderr
from typing import Tuple

from halo import Halo
from tqdm import tqdm

from .misc import get_songs, get_supported_formats
from .song import MetaData, song_metadata


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


def update_db(path: Path, conn: Connection, ffmpeg: str, ffplay: str):
    """
    Update the database
    Args:
        path: path to the music library
        conn: database connection
        ffmpeg: ffmpeg binary
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
    with tqdm(songs, total=len(songs), desc='Updating...', unit='songs') as bar:
        for song in bar:
            metadata = song_metadata(ffmpeg, song)
            if not metadata:
                continue
            assert metadata.length
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


def init_db(path: Path, conn: Connection, ffmpeg: str, ffplay: str):
    """
    Initialize the database
    Args:
        path: path to the music directory
        conn: sqlite3 connection
        ffmpeg: ffmpeg binary
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
    update_db(path, conn, ffmpeg, ffplay)


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
