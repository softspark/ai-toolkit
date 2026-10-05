# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit

"""Exercise release resource controls without running gates or Docker."""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

RELEASE_SCRIPT = Path(__file__).resolve().parents[2] / 'scripts/release.sh'
RESOURCE_ARGS = ['--cpus', '1', '--memory', '3g', '--memory-swap', '3g',
                 '--pids-limit', '512']


@pytest.fixture
def release_harness(tmp_path):
    source = RELEASE_SCRIPT.read_text()
    assert source.endswith('main "$@"\n')
    library = tmp_path / 'release-functions.sh'
    library.write_text(source.removesuffix('main "$@"\n'))
    trace = tmp_path / 'commands.jsonl'
    fake = '''import json, os, sys
with open(os.environ['RELEASE_TEST_TRACE'], 'a') as stream:
    stream.write(json.dumps([os.path.basename(sys.argv[0]), *sys.argv[1:]]) + '\\n')
'''
    compile(fake, 'fake-release-command', 'exec')
    for name in ('docker', 'bats', 'npm'):
        binary = tmp_path / name
        binary.write_text(f'#!{sys.executable}\n' + fake)
        binary.chmod(0o700)
    (tmp_path / 'source.tar').touch()
    (tmp_path / 'bats-macos.log').touch()

    def run(command, jobs=None):
        env = dict(os.environ, RELEASE_TEST_TRACE=str(trace))
        env.pop('AI_TOOLKIT_RELEASE_TEST_JOBS', None)
        if jobs is not None:
            env['AI_TOOLKIT_RELEASE_TEST_JOBS'] = jobs
        env['PATH'] = str(tmp_path) + os.pathsep + env['PATH']
        script = (f'source {shlex.quote(str(library))}\n'
                  f'LOG_DIR={shlex.quote(str(tmp_path))}\n'
                  'SOURCE_TAR="$LOG_DIR/source.tar"\n'
                  'json_field() { printf "true\\n"; }\n' + command)
        subprocess.run(['bash', '-n', '-c', script], check=True, env=env)
        result = subprocess.run(['bash', '-c', script], env=env, cwd=tmp_path,
                                text=True, capture_output=True, timeout=5)
        commands = [json.loads(line) for line in trace.read_text().splitlines()] if trace.exists() else []
        return result, commands

    return run


@pytest.mark.parametrize(('jobs', 'expected'), [
    (None, ['npm', 'test']),
    ('1', ['bats', 'tests/']),
    ('2', ['bats', 'tests/', '--jobs', '2', '--no-parallelize-within-files']),
    ('3', ['bats', 'tests/', '--jobs', '3', '--no-parallelize-within-files']),
    ('4', ['npm', 'test']),
])
def test_host_release_runs_complete_suite_with_requested_workers(release_harness, jobs, expected):
    result, commands = release_harness('gate_bats_host', jobs)
    assert result.returncode == 0, result.stderr
    assert commands == [expected]


@pytest.mark.parametrize('jobs', [None, '1', '2', '3', '4'])
def test_linux_release_applies_worker_count_and_all_container_caps(release_harness, jobs):
    result, commands = release_harness(
        'gate_bats_linux\ngate_python_floor\ngate_python_ceiling', jobs)
    assert result.returncode == 0, result.stderr
    runs = [command for command in commands if command[:2] == ['docker', 'run']]
    assert len(runs) == 3
    for command in runs:
        assert command[4:12] == RESOURCE_ARGS
    linux = runs[0]
    selected_jobs = linux[linux.index('-e') + 1].split('=', 1)[1]
    assert selected_jobs == (jobs or '4')
    # Run the actual Linux shell body with filesystem/user operations stubbed.
    body = linux[-1]
    script = '''mkdir() { :; }
tar() { :; }
chown() { :; }
cd() { :; }
runuser() { printf '%s\\n' "$@"; }
''' + body
    subprocess.run(['bash', '-n', '-c', script], check=True)
    result = subprocess.run(['bash', '-euc', script], text=True, capture_output=True,
                            env=dict(os.environ, RELEASE_TEST_JOBS=selected_jobs), timeout=5)
    assert result.returncode == 0, result.stderr
    expected = ['-u', 'tester', '--', 'env', 'HOME=/home/tester', 'bats', 'tests/']
    if selected_jobs != '1':
        expected += ['--jobs', selected_jobs, '--no-parallelize-within-files']
    assert result.stdout.splitlines() == expected


@pytest.mark.parametrize('jobs', ['', '0', '5', '-1', '1.5', '01', 'auto', '1; exit 0'])
def test_invalid_release_workers_fail_before_tools_or_gates(release_harness, jobs):
    result, commands = release_harness(
        'require_tools() { echo UNEXPECTED_TOOL_CHECK; exit 99; }\n'
        'main 1.2.3 --gates-only', jobs)
    assert result.returncode == 1
    assert 'AI_TOOLKIT_RELEASE_TEST_JOBS must be an integer from 1 to 4' in result.stderr
    assert 'UNEXPECTED_TOOL_CHECK' not in result.stdout
    assert not commands
