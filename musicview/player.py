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
from subprocess import DEVNULL, Popen
from threading import Condition, RLock, Thread
from time import sleep

from .db import next_song
from .misc import format_time
from .cli import get_connection


class Player:
    """
    Music player class
    """

    def __init__(self, data, name, ffplay, conn, stdscr):
        """
        Args:
            data: path to music library
            name: name of the music library
            ffplay: ffplay binary
            conn: database connection
            stdscr: curses screen
        """
        self.ffplay = ffplay
        self.data = data
        self.name = name
        self.conn = conn
        self.stdscr = stdscr
        self.height, self.width = stdscr.getmaxyx()

        self.cur_song = None
        self.cur_fav = False
        self.cur_count = 0
        self.time_elapsed = 0

        self.stopped = False
        self.paused = True

        self.playing_proc = None
        self.ui_thread = None

        self.db_lock = RLock()
        self.cv = Condition()

    def _play(self) -> Popen:
        """
        Return a subprocess to play the current song
        Returns:
            a subprocess to play the current song
        """
        return Popen(
            [self.ffplay, '-nodisp', '-autoexit', self.cur_song.path],
            stderr=DEVNULL
        )

    def ui(self):
        """
        UI control, meant to be ran in another thread
        """
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

    def progress(self):
        """
        Progress bar control, meant to be ran in another thread
        """
        while True:
            if self.stopped:
                return
            with self.cv:
                while self.paused:
                    self.cv.wait()
                self.display()
                sleep(1)
                self.time_elapsed += 1
                if self.time_elapsed > self.cur_song.length:
                    self.play_next()

    def play_next(self):
        """
        Play the next song
        """
        self.playing_proc.kill()

    def toggle(self):
        """
        Toggle play/pause status
        """
        if self.paused:
            self.playing_proc.send_signal(signal.SIGCONT)
            with self.cv:
                self.cv.notify()
        else:
            self.playing_proc.send_signal(signal.SIGSTOP)
        self.paused = not self.paused
        self.display()

    def start(self):
        """
        Start the music player
        """
        ui = Thread(target=self.ui, name='ui', daemon=True)
        self.ui_thread = ui
        ui.start()
        progress = Thread(target=self.progress, name='progress', daemon=True)
        progress.start()
        while True:
            self.paused = True
            if self.stopped:
                return
            with self.cv:
                self.time_elapsed = 0
            with self.db_lock:
                self.cur_song, (self.cur_fav, self.cur_count) = next_song(self.conn)
                self.cur_count += 1
            self.display()
            with self._play() as proc:
                self.playing_proc = proc
                self.paused = False
                with self.cv:
                    self.cv.notify()

    def favourite(self, conn):
        """
        Toggle the favourite status of the current song
        Args:
            conn: connection to the sqlite database
        """
        with self.db_lock:
            conn.execute(
                'UPDATE library SET favourite=? WHERE path=?',
                (not self.cur_fav, self.cur_song.path)
            )
            conn.commit()
        self.cur_fav = not self.cur_fav
        self.display()

    def display(self):
        """
        Display text on screen
        """
        length = self.cur_song.length
        total_time = self.cur_song.format_time()
        cur_time = format_time(self.time_elapsed)
        self.stdscr.addstr(0, 1, '[paused]' if self.paused else '[playing]')
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
                self.cur_song.format() +
                ['Favourite: {}'.format(bool(self.cur_fav)),
                 'Play count: {}\n'.format(self.cur_count)]
            )
        )
        self.stdscr.refresh()
