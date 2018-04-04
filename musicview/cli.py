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

import re
import sys
import urllib.error
import urllib.request
from curses import wrapper
from functools import partial
from os import getenv
from pathlib import Path
from shutil import which
from sqlite3 import connect

import click

import toml
from .__version__ import __title__, __version__
from .db import init_db, update_db
from .player import Player

DEFAULT_CONFIG_HOME = Path.home() / '.musicview'
CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])
CONFIG_ENVAR = 'MUSICVIEW_CONFIG_HOME'
CONF_FILE = 'musicview.toml'

print = click.echo
fprint = partial(click.echo, file=sys.stderr)


class Ctx:
    """
    Context for the cli
    """
    default_config = {
        'general': {
            'check for updates': True,
        },
        'player control': {
            'play/pause': 'p',
            'skip': '>',
            'toggle favourite': 'f',
            'quit': 'q',
        },
        'library paths': {}
    }

    def __init__(self):
        ffplay = which('ffplay')
        ffmpeg = which('ffmpeg')
        if not ffplay or not ffmpeg:
            exit('ffmpeg/ffplay not found!')
        self.ffplay = ffplay
        self.ffmpeg = ffmpeg
        self.config_home = Path(getenv(CONFIG_ENVAR, DEFAULT_CONFIG_HOME))
        if not (self.config_home / CONF_FILE).is_file():
            self.setup()
        self.config = toml.loads((self.config_home / CONF_FILE).read_text())
        if self.config['general']['check for updates']:
            check_update()

    def setup(self):
        """Prompt the user to do some initial setup"""
        click.confirm(
            f"It seems like it's your first time using {__title__}!\n"
            f'Would you like to store configuration and metadata under'
            f' {self.config_home}?\n'
            f'If not, you can set the {CONFIG_ENVAR} environment variable'
            f' to change the location.',
            abort=True
        )
        try:
            self.config_home.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            exit(e)

        check_update = click.confirm(
            'Would you like to automatically check for updates?'
        )
        self.default_config['general']['check for updates'] = check_update
        self.dump_config(self.default_config)
        print(f'Configuration file has been generated at '
              f'{self.config_home / CONF_FILE}')

    def dump_config(self, cfg):
        """
        Dump a config dict
        Args:
            cfg: The config to dump
        """
        with (self.config_home / CONF_FILE).open('w+') as f:
            try:
                toml.dump(cfg, f)
            except OSError as e:
                exit(e)

    def get_libpath(self, name):
        """
        Get library path by name
        Args:
            name: name of the library

        Returns:
            path to the library
        """
        return Path(self.config['library paths'][name])

    def library_exists(self, name):
        """
        Check if a library exists
        Args:
            name: The name for the library

        Returns:
            if the library exists
        """
        return name in map(
            lambda p: p.name.rstrip('.db'), self.config_home.iterdir()
        ) and name in self.config['library paths']

    def delete_lib(self, name):
        """
        Delete a music library
        Args:
            name: Name of the music library
        """
        del self.config['library paths'][name]
        self.dump_config(self.config)

    def new_lib(self, name, path):
        """
        Add a new music library
        Args:
            name: name of the library
            path: path of the library
        """
        assert name not in self.config['library paths']
        self.config['library paths'][name] = path
        self.dump_config(self.config)

    def get_conn(self, name):
        """
        Get a sqlite3 connection
        Args:
            name: name of the library

        Returns:
            the connection
        """
        return connect(str(self.config_home / f'{name}.db'))


pass_context = click.make_pass_decorator(Ctx, ensure=True)


def check_update():
    """Check for updates"""
    url = ('https://raw.githubusercontent.com'
           '/MaT1g3R/musicview/master/musicview/__version__.py')
    try:
        with urllib.request.urlopen(url) as resp:
            text = resp.read().decode()
    except urllib.error.URLError:
        print('Could not check for updates, '
              'are you connected to the internet?')
    else:
        regex = re.compile(r"__version__[\s]*=[\s]*\'(.*)\'")
        head_version = regex.findall(text)[0]
        t = lambda s: tuple(map(int, s.split('.')))
        if t(head_version) > t(__version__):
            print(f'New version ({head_version}) available!')


def play_music(data, name, conn, ffplay, controls, stdscr):
    """
    Play some music!
    Args:
        data: path to the dirctory containg database files
        name: name of the music library
        conn: database connection
        ffplay: ffplay binary
        controls: curses controls keymap
        stdscr: curses screen
    """
    stdscr.clear()
    player = Player(data, name, ffplay, conn, controls, stdscr)
    player.start()


@click.group(context_settings=CONTEXT_SETTINGS)
@pass_context
def cli(ctx):
    """musicview, (re)discover your music library"""
    pass


@click.command(name='list')
@pass_context
def list_(ctx):
    """List existing music libraries"""
    names = ctx.config['library paths']
    if names:
        for name, path in names.items():
            print(f'{name} (at {path})')
    else:
        print('There are currently no music libraries!')


@click.command()
@click.argument('name')
@pass_context
def play(ctx, name):
    """Start playing music"""
    if not ctx.library_exists(name):
        exit(f'Library "{name}" does not exist!')
    controls = {val: key for key, val in ctx.config['player control'].items()}
    with ctx.get_conn(name) as conn:
        wrapper(partial(play_music, ctx.config_home, name, conn, ctx.ffplay, controls))


@click.command()
@click.argument('name')
@pass_context
def delete(ctx, name: str):
    """Delete a music library"""
    if not ctx.library_exists(name):
        exit(f'Library "{name}" does not exist!')
    to_del = ctx.config_home / f'{name}.db'
    click.confirm(f'Delete {name}?', abort=True)
    ctx.delete_lib(name)
    print(f'{name} deleted!')
    try:
        to_del.unlink()
    except OSError as e:
        fprint(e)


@click.command()
@click.argument('name')
@pass_context
def update(ctx, name: str):
    """Update an existing music library"""
    if not ctx.library_exists(name):
        exit(f'Library "{name}" does not exist!')
    with ctx.get_conn(name) as conn:
        update_db(ctx.get_libpath(name), conn, ctx.ffmpeg, ctx.ffplay)


@click.command(short_help='Create a new music library')
@click.argument('name')
@click.argument('path', type=click.Path(exists=True, file_okay=False))
@pass_context
def new(ctx, name, path):
    """
    Create a new music library

    Arguments:

        NAME: Name of the new music library

        PATH: Path of the music library
    """
    if ctx.library_exists(name):
        exit(f'Library with name {name} already exists!')
    path = Path(path).resolve()
    init_db(
        path, ctx.config_home / f'{name}.db', ctx.ffmpeg, ctx.ffplay
    )
    ctx.new_lib(name, str(path))


cli.add_command(list_)
cli.add_command(new)
cli.add_command(update)
cli.add_command(delete)
cli.add_command(play)
