# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit

"""The combined CLI preserves every provider's accounts and partial failures."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def configured(tmp_path):
    home, data, project, binary = (tmp_path / name for name in ('home', 'data', 'project', 'bin'))
    for directory in (home, data, project, binary):
        directory.mkdir()
    env = {key: value for key, value in os.environ.items() if key not in (
        'CODEX_HOME', 'CODEX_SQLITE_HOME', 'CLAUDE_CONFIG_DIR', 'CODEX_API_KEY',
        'CODEX_ACCESS_TOKEN', 'OPENAI_API_KEY', 'NO_COLOR',
    )}
    env.update(HOME=str(home), AI_TOOLKIT_HOME=str(data), COLUMNS='100',
               CLAUDE_SWITCH_CONFIG=str(data / 'claude-switch.json'),
               CODEX_SWITCH_CONFIG=str(data / 'codex-switch.json'),
               PATH=str(binary) + os.pathsep + env['PATH'])
    for provider in ('claude', 'codex'):
        default, customer = home / ('.' + provider), home / provider / 'customer'
        default.mkdir()
        customer.mkdir(parents=True)
        (data / f'{provider}-switch.json').write_text(json.dumps({
            'version': 1, 'default': 'default', 'accounts': {'default': None, 'customer': str(customer)},
            'projects': {str(project): 'customer'},
        }))
    # Reviewed fake: bounded local JSON-RPC, no network, account or model requests.
    fake = '''import json, os, sys
from pathlib import Path
home = Path(os.environ['CODEX_HOME'])
for line in sys.stdin:
    request = json.loads(line)
    with (home / 'rpc.log').open('a') as stream:
        stream.write(request['method'] + '\\n')
    if request['method'] == 'initialize':
        response = {'result': {}}
    elif request['method'] == 'account/rateLimits/read':
        if home.name == 'customer':
            response = {'error': {'message': 'Not authenticated SECRET', 'code': -32000}}
        else:
            response = {'result': {'rateLimits': {'limitId': 'codex', 'primary': {
                'usedPercent': 37, 'windowDurationMins': 300, 'resetsAt': 2500000000}}}}
    else:
        continue
    print(json.dumps({'id': request['id'], **response}), flush=True)
'''
    compile(fake, 'fake-llm-status-codex', 'exec')
    (binary / 'codex').write_text(f'#!{sys.executable}\n' + fake)
    (binary / 'codex').chmod(0o700)
    for directory, percentage in ((home / '.claude', 23), (home / 'claude/customer', 58)):
        (directory / 'live-response.json').write_text(json.dumps({
            'five_hour': {'utilization': percentage, 'resets_at': '2090-01-01T00:00:00Z'},
        }))
    # Test-only HTTP boundary replacement; all CLI parsing and provider code is real.
    sitecustomize = '''import json, os
from pathlib import Path
import claude_usage
def request_usage(config_dir, timeout):
    directory = Path(config_dir) if config_dir else Path(os.environ['HOME']) / '.claude'
    with (directory / 'http.log').open('a') as stream:
        stream.write('GET /api/oauth/usage\\n')
    result = json.loads((directory / 'live-response.json').read_text())
    if 'error' in result:
        raise claude_usage.UsageError(result['error'])
    return result
claude_usage.request_usage = request_usage
'''
    compile(sitecustomize, 'llm-status-http-fixture', 'exec')
    (binary / 'sitecustomize.py').write_text(sitecustomize)
    env['PYTHONPATH'] = str(binary) + os.pathsep + str(ROOT / 'scripts')
    return home, data, project, env


def run(configured, *args, entry='toolkit'):
    _, _, project, env = configured
    commands = {
        'python': [sys.executable, str(ROOT / 'scripts/llm_status.py')],
        'toolkit': ['node', str(ROOT / 'bin/ai-toolkit.js'), 'llm-status'],
    }
    return subprocess.run([*commands[entry], *args], env=env, cwd=project,
                          capture_output=True, text=True, timeout=15, check=False)


@pytest.mark.parametrize('entry', ['python', 'toolkit'])
def test_all_accounts_with_same_names_remain_distinct_and_routed(configured, entry):
    home, data, _, _ = configured
    before = {path.name: path.read_bytes() for path in data.glob('*-switch.json')}
    result = run(configured, '--json', entry=entry)
    assert result.returncode == 0, result.stderr
    status = json.loads(result.stdout)
    assert status['account_count'] == 4
    assert set(status['providers']) == {'claude', 'codex'}
    for provider in status['providers'].values():
        assert provider['state'] == 'configured'
        assert provider['selected']['account'] == 'customer'
        assert provider['selected']['source'] == 'project'
        assert [row['name'] for row in provider['accounts']] == ['default', 'customer']
        assert provider['accounts'][1]['selected'] is True
    claude = status['providers']['claude']['accounts'][0]['usage']
    assert claude['windows']['five_hour']['used_percentage'] == 23
    assert status['providers']['codex']['accounts'][0]['usage']['state'] == 'live'
    assert {path.name: path.read_bytes() for path in data.glob('*-switch.json')} == before
    assert len(list(home.rglob('rpc.log'))) == 2
    assert len(list(home.rglob('http.log'))) == 2
    assert not (data / 'claude-usage').exists() and not (data / 'codex-usage').exists()


@pytest.mark.parametrize('provider', ['claude', 'codex'])
def test_missing_provider_keeps_configured_accounts_visible(configured, provider):
    _, data, _, _ = configured
    (data / f'{provider}-switch.json').rename(data / f'{provider}-switch.backup')
    result = run(configured, '--json')
    assert result.returncode == 0, result.stderr
    status = json.loads(result.stdout)
    assert status['account_count'] == 2
    assert status['providers'][provider]['state'] == 'not_configured'
    assert status['providers'][provider]['accounts'] == []


def test_empty_configuration_reports_setup_without_creating_registries(configured):
    _, data, _, _ = configured
    for path in data.glob('*-switch.json'):
        path.rename(path.with_suffix('.backup'))
    result = run(configured)
    assert result.returncode == 0
    assert 'No accounts configured' in result.stdout
    assert 'ai-toolkit claude-switch init' in result.stdout
    assert 'ai-toolkit codex-switch init' in result.stdout
    assert not list(data.glob('*-switch.json'))


@pytest.mark.parametrize('provider', ['claude', 'codex'])
@pytest.mark.parametrize('content', [b'[]', b'{', b'\xff'])
def test_invalid_registry_is_reported_without_hiding_other_provider(configured, provider, content):
    _, data, _, _ = configured
    (data / f'{provider}-switch.json').write_bytes(content)
    result = run(configured, '--json')
    assert result.returncode == 1
    status = json.loads(result.stdout)
    assert status['account_count'] == 2
    assert status['providers'][provider]['state'] == 'error'
    assert status['providers'][provider]['error'] == 'invalid_configuration'
    assert 'Traceback' not in result.stderr


@pytest.mark.parametrize('arguments', [(), ('--refresh',), ('refresh',)])
def test_every_status_form_queries_both_providers_and_keeps_partial_failure(configured, arguments):
    home, data, _, _ = configured
    result = run(configured, *arguments, '--json')
    assert result.returncode == 0, result.stderr
    status = json.loads(result.stdout)
    accounts = status['providers']['codex']['accounts']
    assert accounts[0]['usage']['windows']['five_hour']['used_percentage'] == 37
    assert accounts[1]['usage']['refresh_error'] == 'not_authenticated'
    assert status['providers']['claude']['accounts'][0]['usage']['windows']['five_hour']['used_percentage'] == 23
    assert not (data / 'claude-usage').exists() and not (data / 'codex-usage').exists()
    for directory in (home / '.claude', home / 'claude/customer'):
        assert (directory / 'http.log').read_text().splitlines() == ['GET /api/oauth/usage']
    for directory in (home / '.codex', home / 'codex/customer'):
        assert (directory / 'rpc.log').read_text().splitlines() == [
            'initialize', 'initialized', 'account/rateLimits/read',
        ]
    assert 'SECRET' not in result.stdout + result.stderr


def test_text_display_supports_colors_details_and_refresh_errors(configured):
    result = run(configured, '--refresh', '--verbose', '--color', 'always')
    assert result.returncode == 0, result.stderr
    for expected in ('LLM STATUS', '4 accounts', 'CLAUDE ACCOUNTS', 'CODEX ACCOUNTS',
                     '23%', '37%', 'Config:', 'not_authenticated', '\x1b['):
        assert expected in result.stdout
    configured[3]['NO_COLOR'] = '1'
    result = run(configured, '--color', 'always')
    assert '\x1b[' not in result.stdout
    assert 'Config:' not in result.stdout


def test_new_claude_response_is_fetched_then_failure_never_shows_last_value(configured):
    home, data, _, _ = configured
    response = home / '.claude/live-response.json'
    assert '23%' in run(configured, '--color', 'never').stdout
    response.write_text(json.dumps({'five_hour': {'utilization': 85, 'resets_at': '2090-01-01T00:00:00Z'}}))
    assert '85%' in run(configured, '--refresh', '--color', 'never').stdout
    response.write_text(json.dumps({'error': 'authentication_expired'}))
    result = run(configured, '--color', 'never')
    assert result.returncode == 0
    assert 'authentication_expired' in result.stdout
    assert '85%' not in result.stdout
    assert '37%' in result.stdout
    assert not (data / 'claude-usage').exists()
