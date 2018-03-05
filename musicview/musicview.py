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
from sqlite3 import connect

import click


@click.command()
@click.option('--directory', default=Path.cwd(), type=Path,
              help='Root directory of your music library.')
@click.option('--data', default=Path.home() / '.musicview', type=Path,
              help='Path to directory containing data and config files')
@click.argument('name')
def main(directory: Path, data: Path, name: str):
    db_file = data / '{}.db'.format(name)
    db_file.touch()
    conn = connect(str(db_file))
    init_db(conn)


def init_db(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS library (
        id INTEGER PRIMARY KEY,
        path VARCHAR NOT NULL,
        title VARCHAR,
        genre VARCHAR,
        artist VARCHAR,
        length INT,
        favourite BOOLEAN DEFAULT 0 NOT NULL,
        listen_count INT DEFAULT 0
        );
        """
    )
    conn.commit()


if __name__ == '__main__':
    main()
