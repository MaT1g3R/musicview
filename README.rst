*********
musicview
*********

(re)discover your music library

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
* Python 3.5 or later
* `curses`
    - This should be available on most \*nix operating systems. On Windows you can try WSL
* `ffmpeg <https://ffmpeg.org/>`_ or `avconv`
    - On Linux you can obtain them via your package manager
    - On macOS you can install `ffmpeg` using `homebrew <https://brew.sh/>`_ :code:`brew install ffmpeg`
    - On Windows you can follow the instructions `here <https://ffmpeg.org/download.html>`_

Installation
===============
::

  pip install musicview

Or to install the latest development version, run:

::

  git clone https://github.com/MaT1g3R/musicview
  cd music view
  pip install .

Quick Tutorial
================
To use the commandline interface
::

    → musicview --help
    Usage: musicview [OPTIONS] COMMAND [ARGS]...

      musicview, (re)discover your music library

    Options:
      -h, --help  Show this message and exit.

    Commands:
      delete  Delete a music library
      list    List existing music libraries
      play    Start playing music
      update  Update an existing music library


The :code:`play` command will start a simple curses music player.

Curses interface controls (These will be configurable in a future release)

* :code:`p` play/pause
* :code:`f` toggle favourite status
* :code:`>` skip song
* :code:`q` quit

TODO
=======
* Configuration options
* Tests
* Better looking cueses UI
* asyncio?

License
========
musicview is licensed under the terms of the GNU General Public License,
either version 3 of the License, or (at your option) any later version.

Please see `LICENSE <https://github.com/MaT1g3R/musicview/blob/master/LICENSE>`_ for details
