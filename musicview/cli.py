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

from curses import wrapper
from functools import partial
from pathlib import Path
from shutil import which
from sys import stderr

import click

from .db import get_connection, init_db, update_db
from .player import Player

data_opt = click.option(
    '-d', '--data', default=Path.home() / '.musicview', type=Path,
    help='Path to directory containing data and config files'
)

path_opt = click.option(
    '-p', '--path', default=Path.cwd(), type=Path,
    help='Path to the directory of your music library.'
)

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


def check_path(path):
    """
    Check if a path is a valid directory
    Args:
        path: the path to check
    """
    if not path.is_dir():
        print('{} is not a valid directory!'.format(path), file=stderr)
        exit(1)


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


@click.group(context_settings=CONTEXT_SETTINGS)
@click.pass_obj
def cli(obj):
    """musicview, (re)discover your music library"""
    ffplay = which('ffplay')
    ffmpeg = which('ffmpeg')
    if not ffplay or not ffmpeg:
        print('ffmpeg/ffplay not found!', file=stderr)
        exit(1)

    obj['ffplay'] = ffplay
    obj['ffmpeg'] = ffmpeg


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
    ffmpeg = obj['ffmpeg']

    init, conn = get_connection(data, name, False)
    with conn:
        if init:
            init_db(path, conn, ffmpeg, ffplay)
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
    ffmpeg = obj['ffmpeg']

    if not name in map(lambda p: p.name.rstrip('.db'), data.iterdir()):
        print('Library "{}" does not exist!'.format(name), file=stderr)
        exit(1)

    _, conn = get_connection(data, name, True)
    with conn:
        update_db(path, conn, ffmpeg, ffplay)


cli.add_command(list_)
cli.add_command(play)
cli.add_command(delete)
cli.add_command(update)
