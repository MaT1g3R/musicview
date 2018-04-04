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

from sqlite3 import connect
from threading import Condition, RLock, Thread
from time import sleep

from musicview.db import iter_db
from .misc import format_time


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
        self.height, self.width = stdscr.getmaxyx()

        self.cur_song = None
        self.time_elapsed = 0
        self.stopped = False

        self.ui_thread = None

        self.db_lock = RLock()
        self.cv = Condition()

    def ui(self):
        """
        UI control, meant to be ran in another thread
        """
        conn = connect(str(self.data / f'{self.name}.db'))
        while not self.stopped:
            cmd = self.controls.get(self.stdscr.getkey())
            if cmd == 'quit':
                self.stopped = True
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
                self.display()
            elif cmd == 'skip':
                self.cur_song.stop()
            elif cmd == 'toggle favourite':
                with self.db_lock:
                    self.cur_song.toggle_favourite(conn)
                self.display()

    def progress(self):
        """
        Progress bar control, meant to be ran in another thread
        """
        while not self.stopped:
            with self.cv:
                while (not self.cur_song) or self.cur_song.paused:
                    self.cv.wait()
                self.display()
                sleep(1)
                self.time_elapsed += 1
                if self.cur_song and self.time_elapsed > self.cur_song.meta.length:
                    self.cur_song.stop()

    def start(self):
        """
        Start the music player
        """
        ui = Thread(target=self.ui, name='ui')
        self.ui_thread = ui
        ui.start()
        progress = Thread(target=self.progress, name='progress')
        progress.start()
        for song in iter_db(self.conn, self.db_lock):
            if self.stopped:
                break
            with self.cv:
                self.time_elapsed = 0
            self.cur_song = song
            self.display()
            with self.cur_song.play(self.ffplay):
                with self.cv:
                    self.cv.notify()
        ui.join()
        progress.join()

    def display(self):
        """
        Display text on screen
        """
        self.stdscr.clear()
        length = self.cur_song.meta.length
        total_time = format_time(self.cur_song.meta.length)
        cur_time = format_time(self.time_elapsed)
        self.stdscr.addstr(0, 1, '[paused]' if self.cur_song.paused else '[playing]')
        self.stdscr.addstr(
            1, 1, '{}/{}'.format(cur_time, total_time)
        )
        bar_len = self.width - 4
        prog = int(bar_len * self.time_elapsed // length) - 1
        if prog < 0:
            prog = 0
        empty = bar_len - prog - 1
        self.stdscr.addstr(2, 1, '|{}{}{}|'.format(prog * '=', '>', empty * ' '))
        self.stdscr.addstr(
            3, 1,
            '\n '.join(
                self.cur_song.meta.format() +
                ['Favourite: {}'.format(self.cur_song.fav),
                 'Play count: {}\n'.format(self.cur_song.listen_count)]
            )
        )
        self.stdscr.refresh()
