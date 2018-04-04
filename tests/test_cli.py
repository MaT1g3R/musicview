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

from copy import deepcopy
from pathlib import Path
from sqlite3 import connect

from tests import FULL_DATA, HERE, SONGS, SONG_COUNT, SPAM, export, get_files

Path.home = lambda: Path(__file__).parent / 'test_home'
from shutil import rmtree

import pytest
from click.testing import CliRunner

from musicview import cli
from musicview.cli import DEFAULT_CONFIG_HOME, CONF_FILE, Ctx

import toml


class TestSetup:
    tmp_dir = HERE / 'tmp'
    conf = deepcopy(Ctx.default_config)
    no_update_conf = deepcopy(conf)
    no_update_conf['general']['check for updates'] = False

    @pytest.fixture()
    def runner(self):
        yield CliRunner()
        try:
            rmtree(Path.home())
        except OSError:
            pass

    @pytest.fixture()
    def env_runner(self):
        runner = CliRunner()
        with export({'MUSICVIEW_CONFIG_HOME': str(self.tmp_dir)}):
            yield runner
        rmtree(self.tmp_dir)

    def test_setup_auto_update(self, runner: CliRunner):
        result = runner.invoke(cli, ['list'], input='y\ry')
        assert not result.exit_code
        assert DEFAULT_CONFIG_HOME.is_dir()
        with open(DEFAULT_CONFIG_HOME / 'musicview.toml') as f:
            assert toml.load(f) == self.conf

    def test_setup_no_update(self, runner: CliRunner):
        result = runner.invoke(cli, ['list'], input='y\rn')
        assert not result.exit_code
        assert DEFAULT_CONFIG_HOME.is_dir()
        with open(DEFAULT_CONFIG_HOME / 'musicview.toml') as f:
            assert toml.load(f) == self.no_update_conf

    def test_setup_envar(self, env_runner: CliRunner):
        result = env_runner.invoke(cli, ['list'], input='y\ry')
        assert not result.exit_code
        assert self.tmp_dir.is_dir()
        with open(self.tmp_dir / 'musicview.toml') as f:
            assert toml.load(f) == self.conf

    def test_setup_abort(self, runner: CliRunner):
        result = runner.invoke(cli, ['list'], input='n')
        assert result.output.strip().endswith('Aborted!')
        assert not DEFAULT_CONFIG_HOME.is_dir()

    def test_setup_abort_exists(self, env_runner: CliRunner):
        self.tmp_dir.mkdir()
        result = env_runner.invoke(cli, ['list'], input='n')
        assert result.output.strip().endswith('Aborted!')
        assert not list(self.tmp_dir.iterdir())


class TestEmpty:

    @pytest.fixture()
    def runner(self):
        DEFAULT_CONFIG_HOME.mkdir(parents=True)
        (DEFAULT_CONFIG_HOME / CONF_FILE).write_text(toml.dumps(Ctx.default_config))
        yield CliRunner()
        rmtree(Path.home())

    def test_list(self, runner: CliRunner):
        result = runner.invoke(cli, ['list'])
        assert not result.exception
        assert not result.exit_code
        assert result.output.strip() == 'There are currently no music libraries!'

    def test_new(self, runner: CliRunner):
        result = runner.invoke(cli, ['new', 'tmp', str(SONGS)])
        assert not result.exit_code
        with open(DEFAULT_CONFIG_HOME / CONF_FILE) as f:
            cfg = toml.load(f)
        assert cfg['library paths'] == {'tmp': str(SONGS)}
        with connect(str(DEFAULT_CONFIG_HOME / 'tmp.db')) as conn:
            cur = conn.cursor()
            cur.execute("SELECT path FROM library;")
            res = cur.fetchall()
        assert len(res) == SONG_COUNT
        assert set(Path(p) for p, in res) == set(get_files(SONGS))

    def test_new_fail(self, runner: CliRunner):
        result = runner.invoke(cli, ['new', 'tmp', str(SPAM)])
        assert result.exit_code
        assert f'Could not find any music files under "{SPAM}"!' in result.output

    def test_update(self, runner: CliRunner):
        result = runner.invoke(cli, ['update', 'foo'])
        assert result.exit_code
        assert result.output.strip() == 'Library "foo" does not exist!'

    def test_delete(self, runner: CliRunner):
        result = runner.invoke(cli, ['delete', 'spam'])
        assert result.exit_code
        assert result.output.strip() == 'Library "spam" does not exist!'

    def test_play(self, runner: CliRunner):
        result = runner.invoke(cli, ['play', 'spam'])
        assert result.exit_code
        assert result.output.strip() == 'Library "spam" does not exist!'


class TestOne:
    @pytest.fixture()
    def runner(self):
        DEFAULT_CONFIG_HOME.mkdir(parents=True)
        (DEFAULT_CONFIG_HOME / CONF_FILE).write_text(toml.dumps(Ctx.default_config))
        runner = CliRunner()
        res = runner.invoke(cli, ['new', 'full data', str(FULL_DATA)])
        assert res.exit_code == 0
        yield runner
        rmtree(Path.home())

    def test_list(self, runner: CliRunner):
        result = runner.invoke(cli, ['list'])
        assert not result.exception
        assert not result.exit_code
        assert 'full data' in result.output

    def test_new(self, runner: CliRunner):
        result = runner.invoke(cli, ['new', 'tmp', str(SONGS)])
        assert not result.exit_code
        with open(DEFAULT_CONFIG_HOME / CONF_FILE) as f:
            cfg = toml.load(f)
        assert cfg['library paths'] == {'full data': str(FULL_DATA), 'tmp': str(SONGS)}
        with connect(str(DEFAULT_CONFIG_HOME / 'tmp.db')) as conn:
            cur = conn.cursor()
            cur.execute("SELECT path FROM library;")
            res = cur.fetchall()
        assert len(res) == SONG_COUNT
        assert set(Path(p) for p, in res) == set(get_files(SONGS))

    def test_new_fail(self, runner: CliRunner):
        result = runner.invoke(cli, ['new', 'tmp', str(SPAM)])
        assert result.exit_code
        assert f'Could not find any music files under "{SPAM}"!' in result.output
        with open(DEFAULT_CONFIG_HOME / CONF_FILE) as f:
            cfg = toml.load(f)
        assert cfg['library paths'] == {'full data': str(FULL_DATA)}

    def test_new_exists(self, runner: CliRunner):
        result = runner.invoke(cli, ['new', 'full data', str(SPAM)])
        assert result.exit_code
        assert f'Library with name full data already exists!' in result.output
        with open(DEFAULT_CONFIG_HOME / CONF_FILE) as f:
            cfg = toml.load(f)
        assert cfg['library paths'] == {'full data': str(FULL_DATA)}

    def test_update(self, runner: CliRunner):
        result = runner.invoke(cli, ['update', 'full data'])
        assert result.exit_code == 0
        assert result.output.strip()

    def test_delete(self, runner: CliRunner):
        result = runner.invoke(cli, ['delete', 'full data'], input='y')
        assert result.exit_code == 0
        assert 'full data deleted' in result.output.strip()

    def test_play(self, runner: CliRunner):
        result = runner.invoke(cli, ['play', 'full data'], input='q')
        assert result.exit_code == -1
        assert not result.output
