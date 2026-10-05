# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit

"""Execute the composite action's install step without installing any package."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

ACTION = Path(__file__).resolve().parents[2] / 'action.yml'


@pytest.mark.parametrize('version', [
    'latest', '5.1.0', '^5.1.0', '>=5.0.0 <6.0.0',
    '$(printf compromised > injected)', '`printf compromised > injected`',
    'latest; printf compromised > injected', 'latest --prefix unwanted',
])
def test_install_step_passes_version_as_one_literal_npm_argument(tmp_path, version):
    action = ACTION.read_text()
    step = re.search(r'^    - name: Install ai-toolkit\n(.*?)(?=^    - name:|\Z)', action, re.MULTILINE | re.DOTALL)
    assert step is not None
    script = re.search(r'^      run: (.+)$', step[1], re.MULTILINE)
    assert script is not None
    env = dict(os.environ)
    for name in re.findall(r'^        ([A-Z_]+): \$\{\{ inputs\.toolkit-version \}\}$', step[1], re.MULTILINE):
        env[name] = version
    # Emulate GitHub expression expansion, including the unsafe pre-fix form.
    command = script[1].replace('${{ inputs.toolkit-version }}', version)
    binary = tmp_path / 'npm'
    fake = 'import json, sys\nprint(json.dumps(sys.argv[1:]))\n'
    compile(fake, 'fake-npm', 'exec')
    binary.write_text(f'#!{sys.executable}\n' + fake)
    binary.chmod(0o700)
    env['PATH'] = str(tmp_path) + os.pathsep + env['PATH']
    subprocess.run(['bash', '-n', '-c', command], cwd=tmp_path, check=True, env=env)

    result = subprocess.run(['bash', '-c', command], cwd=tmp_path, env=env,
                            text=True, capture_output=True, check=False, timeout=5)

    assert not (tmp_path / 'injected').exists(), 'Version text executed shell code'
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == ['install', '-g', '@softspark/ai-toolkit@' + version]


def test_composite_action_uses_immutable_action_pins():
    uses = re.findall(r'^\s+uses:\s*(\S+)', ACTION.read_text(), re.MULTILINE)
    assert uses
    assert all(re.fullmatch(r'[^@]+@[0-9a-f]{40}', value) for value in uses)
