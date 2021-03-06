******************************************
musicview: (re)discover your music library
******************************************

.. image:: https://badge.fury.io/py/musicview.svg
    :target: https://badge.fury.io/py/musicview

.. image:: https://circleci.com/gh/MaT1g3R/musicview.svg?style=svg
    :target: https://circleci.com/gh/MaT1g3R/musicview

.. image:: https://travis-ci.org/MaT1g3R/musicview.svg?branch=master
    :target: https://travis-ci.org/MaT1g3R/musicview

.. image:: https://codecov.io/gh/MaT1g3R/musicview/branch/master/graph/badge.svg
    :target: https://codecov.io/gh/MaT1g3R/musicview


Motivation
==========
Do you have a massive music library that you have no hope of ever going
through? This tool aims to solve this problem.

What does it do
================
* Provides a very simple curses interface
* Recursively discover all sound files and their metadata under a directory
* Allows tracking multiple different music libraries
* Randomly selects the least played file to play
* Keep track of favourite status

What does it not do
====================
* Replace your music player

Requirements
============
* Python 3.6 or later
* `curses`
    - This should be available on most \*nix operating systems. On Windows you can try WSL
* `ffmpeg <https://ffmpeg.org/>`_
    - On Linux you can obtain them via your package manager
    - On macOS you can install `ffmpeg` using `homebrew <https://brew.sh/>`_ :code:`brew install ffmpeg --with-sdl2`
    - On Windows you can follow the instructions `here <https://ffmpeg.org/download.html>`_

Installation
===============
::

  pip install musicview

Or to install the latest development version, run:

::

  git clone --recursive https://github.com/MaT1g3R/musicview
  cd musicview
  pip install .

Quick Tutorial
================

To use the command line interface
-----------------------------------

::

    $ musicview --help

    Usage: main.py [OPTIONS] COMMAND [ARGS]...

      musicview, (re)discover your music library

    Options:
      -h, --help  Show this message and exit.

    Commands:
      delete  Delete a music library
      list    List existing music libraries
      new     Create a new music library
      play    Start playing music
      update  Update an existing music library

The :code:`play` command will start a simple curses music player.

Setting the configuration home
------------------------------
By default, musicview will store its configuration and data files
under :code:`$HOME/.musicview`, if you would like to change that,
you can set the :code:`MUSICVIEW_CONFIG_HOME` environment variable to
the path you want.

Default curses interface controls
----------------------------------

* :code:`p` play/pause
* :code:`f` toggle favourite status
* :code:`>` skip song
* :code:`q` quit

You can edit those in the :code:`musicview.toml` file under your
configuration home.

TODO
=======
* Tests
* Better looking cueses UI
* asyncio?

License
========
musicview is licensed under the terms of the GNU General Public License,
either version 3 of the License, or (at your option) any later version.

Please see `LICENSE <https://github.com/MaT1g3R/musicview/blob/master/LICENSE>`_ for details
