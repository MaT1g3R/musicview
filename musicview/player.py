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

import curses
from sqlite3 import connect
from threading import Condition, Event, Lock, Thread
from time import sleep

from .db import iter_db
from .misc import format_time
from .song import MetaData


class Player:
    """
    Music player class
    """

    def __init__(self, data, name, ffplay, conn, controls, stdscr):
        """
        Args:
            data: path to music library
            name: name of the music library
            ffplay: ffplay binary
            conn: database connection
            controls: curses controls keymap
            stdscr: curses screen
        """
        self.ffplay = ffplay
        self.controls = controls
        self.data = data
        self.name = name
        self.conn = conn
        self.stdscr = stdscr

        self.cur_song = None

        self.stopped = Event()
        self.db_lock = Lock()
        self.cv = Condition()

        curses.curs_set(0)
        stdscr.clear()

        def get_y():
            running_y = 0
            while True:
                sent = yield
                yield (sent, running_y)
                running_y += sent

        heights = [1, 2, len(MetaData.__annotations__) + 1]
        y = get_y()
        self.playing_win, self.prog_win, self.meta_win = (
            curses.newwin(ncol, self.width, ypos, 0) for
            (ncol, ypos) in (y.send(h) for h, _ in zip(heights, y))
        )

    @property
    def height(self):
        _height, _width = self.stdscr.getmaxyx()
        return _height

    @property
    def width(self):
        _height, _width = self.stdscr.getmaxyx()
        return _width

    def ui(self):
        """UI control, meant to be ran in another thread"""
        conn = connect(str(self.data / f'{self.name}.db'))
        while not self.stopped.is_set():
            cmd = self.controls.get(self.stdscr.getkey())
            if cmd == 'quit':
                self.stopped.set()
                if self.cur_song:
                    self.cur_song.stop()
                self.stdscr.clear()
                conn.close()
                return
            elif not self.cur_song:
                continue
            elif cmd == 'play/pause':
                if self.cur_song.toggle_pause() is False:
                    with self.cv:
                        self.cv.notify()
                self.display_playing()
            elif cmd == 'skip':
                self.cur_song.stop()
            elif cmd == 'toggle favourite':
                with self.db_lock:
                    self.cur_song.toggle_favourite(conn)
                self.display_metadata()

    def progress(self):
        """ Progress bar control, meant to be ran in another thread"""
        while not self.stopped.is_set():
            with self.cv:
                self.cv.wait_for(lambda: self.cur_song and not self.cur_song.paused)
                self.display_progress()
                sleep(1)
                if self.cur_song and self.cur_song.is_done:
                    self.cur_song.stop()

    def start(self):
        """Start the music player """
        ui = Thread(target=self.ui, name='ui')
        ui.start()
        progress = Thread(target=self.progress, name='progress')
        progress.start()

        for song in iter_db(self.conn, self.db_lock):
            if self.stopped.is_set():
                break
            self.cur_song = song
            self.display()
            with self.cur_song.play(self.ffplay):
                with self.cv:
                    self.cv.notify()

        ui.join()
        progress.join()

    def display_progress(self):
        """Display the current seek time/bar of the current song"""
        length = self.cur_song.meta.length
        cur_time = self.cur_song.time_played
        self.prog_win.addstr(
            0, 1, '{}/{}'.format(format_time(cur_time), format_time(length))
        )
        bar_len = self.width - 4
        prog = int(bar_len * cur_time // length) - 1
        if prog < 0:
            prog = 0
        empty = bar_len - prog - 1
        self.prog_win.addstr(1, 1, '|{}{}{}|'.format(prog * '=', '>', empty * ' '))
        self.prog_win.refresh()

    def display_playing(self):
        """Display playing status of the current song"""
        self.playing_win.addstr(0, 1, '[paused]' if self.cur_song.paused else '[playing]')
        self.playing_win.refresh()

    def display_metadata(self):
        """Display metadata infomation of the current song"""
        self.meta_win.addstr(
            0, 1,
            '\n '.join(
                self.cur_song.meta.format() +
                ['Favourite: {}'.format(self.cur_song.fav),
                 'Play count: {}'.format(self.cur_song.listen_count)]
            )
        )
        self.meta_win.refresh()

    def display(self):
        """ Display everything"""
        self.meta_win.clear()
        self.prog_win.clear()
        self.playing_win.clear()
        self.display_playing()
        self.display_progress()
        self.display_metadata()
