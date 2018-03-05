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
    conn = connect(str(db_file))
    init_db(conn)


def init_db(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS library (
        id INTEGER PRIMARY KEY,
        path VARCHAR NOT NULL ,
        title VARCHAR,
        genre VARCHAR,
        artist VARCHAR,
        length INT,
        favourite  BOOLEAN NOT NULL ,
        listened BOOLEAN NOT NULL DEFAULT 0
        );
        """
    )
    conn.commit()


if __name__ == '__main__':
    main()
