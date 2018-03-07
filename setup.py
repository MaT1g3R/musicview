#!/usr/bin/env python3
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

import json
import sys
from pathlib import Path
from shlex import split
from subprocess import run

from setuptools import setup

if sys.argv[-1] == 'publish':
    run(split('python setup.py sdist bdist_wheel'))
    run(split('twine upload dist/*'))
    exit()

HERE = Path(__file__).parent

lock = json.loads((HERE / 'Pipfile.lock').read_text())
readme = (HERE / 'README.rst').read_text()

about = {}
exec((HERE / 'musicview' / '__version__.py').read_text(), about)

reqs = [
    key + val['version'].replace('==', '>=')
    for key, val in lock['default'].items()
    if key in ('click', 'mutagen', 'halo', 'tqdm')
]

setup(
    name=about['__title__'],
    version=about['__version__'],
    description=about['__description__'],
    long_description=readme,
    author=about['__author__'],
    author_email=about['__author_email__'],
    license=about['__license__'],
    url=about['__url__'],
    py_modules=[
        'main',
    ],
    packages=[
        'musicview',
    ],
    install_requires=reqs,
    package_data={'': ['README.rst', 'LICENSE', 'Pipfile.lock']},
    include_package_data=True,
    python_requires=">=3.5",
    entry_points='''
        [console_scripts]
        musicview=main:main    
    ''',
    classifiers=(
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Environment :: Console :: Curses',
        'Intended Audience :: End Users/Desktop',
        'Natural Language :: English',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: Implementation :: CPython',
        'Topic :: Multimedia :: Sound/Audio',
        'Topic :: Multimedia :: Sound/Audio :: Players',
        'Topic :: Multimedia :: Sound/Audio :: Players :: MP3'
    ),
)
