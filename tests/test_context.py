"""Offline behavioral tests. Every child has a disposable HOME and fake CLIs."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
HELPER = REPO / 'cf-context/scripts/context.sh'


class ContextTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='cf-context-test-')
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.bin = self.base / 'bin'
        self.bin.mkdir()
        self.root = self.base / 'contexts with spaces'
        self.ctx = self.root / 'cdc'
        (self.ctx / '.cf').mkdir(parents=True)
        self.envfile = self.ctx / 'context.env'
        self.write_env()
        self.config = self.ctx / '.cf/config.json'
        self.write_config()
        self.marker = self.base / 'called.json'
        self.env = {
            'HOME': str(self.base),
            'PATH': str(self.bin) + ':/usr/bin:/bin:/usr/sbin:/sbin',
            'CFCTX_ROOT': str(self.root),
            'TEST_MARKER': str(self.marker),
            'PYTHON_FOR_TEST': os.sys.executable,
        }
        # Resolve jq on hosts where it is only installed by Homebrew.
        os.symlink(shutil.which('jq'), self.bin / 'jq')
        upstream = os.environ.get('CF_CONTEXT_TEST_UPSTREAM')
        if upstream:
            shutil.copyfile(upstream, self.bin / 'cfctx-env')
            (self.bin / 'cfctx-env').chmod(0o755)
        else:
            self.binary('cfctx-env', '''#!/bin/bash
set -eu
[[ "$1" == --list ]] && { echo cdc; exit 0; }
printf 'export CF_HOME=%q\\n' "$CFCTX_ROOT/$1"
(
  source "$CFCTX_ROOT/$1/context.env"
  for var in CF_API CF_ORG CF_SPACE OM_TARGET OM_PASSWORD BOSH_ENVIRONMENT CREDHUB_SERVER; do
    [[ -z "${!var:-}" ]] || printf 'export %s=%q\\n' "$var" "${!var}"
  done
)
''')
        for cli in ('cf', 'om', 'bosh', 'credhub'):
            self.binary(cli, '''#!/bin/bash
exec "$PYTHON_FOR_TEST" -c '
import json, os, sys
from pathlib import Path
Path(os.environ["TEST_MARKER"]).write_text(json.dumps({"args":sys.argv[1:], "env":dict(os.environ)}))
sys.exit(int(os.environ.get("TEST_EXIT", "0")))
' "$@"
''')

    def binary(self, name, text):
        path = self.bin / name
        path.write_text(text)
        path.chmod(0o755)

    def write_env(self, text=None):
        self.envfile.write_text(text if text is not None else '''CF_API=https://api.cdc.example
CF_ORG=team
CF_SPACE=dev
OM_TARGET=https://ops.cdc.example
OM_PASSWORD='secret-$-value'
BOSH_ENVIRONMENT=https://bosh.cdc.example
CREDHUB_SERVER=https://credhub.cdc.example
''')
        self.envfile.chmod(0o600)

    def write_config(self, **updates):
        data = dict(Target='https://api.cdc.example',
                    OrganizationFields={'Name': 'team'},
                    SpaceFields={'Name': 'dev'}, AccessToken='secret-token')
        data.update(updates)
        self.config.write_text(json.dumps(data))

    def call(self, *args):
        return subprocess.run(['/bin/bash', str(HELPER), *args], env=self.env,
                              capture_output=True, text=True, timeout=10)

    def rejected(self, *args):
        result = self.call(*args)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertFalse(self.marker.exists(), 'child ran after failed prerequisite')
        return result

    def test_inspect_only_exposes_identity(self):
        result = self.call('inspect', 'cdc')
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data['name'], 'cdc')
        self.assertEqual(data['cf'], 'https://api.cdc.example')
        self.assertNotIn('secret', result.stdout + result.stderr)
        self.assertFalse(self.marker.exists())

    def test_exact_argv_and_selected_home(self):
        args = ['app', "orders ' worker", '$(touch should-not-exist)', 'a;b', '']
        result = self.call('run', 'cdc', '--', 'cf', *args)
        self.assertEqual(result.returncode, 0, result.stderr)
        child = json.loads(self.marker.read_text())
        self.assertEqual(child['args'], args)
        self.assertEqual(child['env']['CF_HOME'], str(self.ctx.resolve()))
        self.assertEqual(child['env']['OM_PASSWORD'], 'secret-$-value')

    def test_inherited_platform_state_is_removed(self):
        for prefix in ('CF_', 'OM_', 'BOSH_', 'CREDHUB_', 'UAA_'):
            self.env[prefix + 'STALE'] = 'old-foundation'
        self.env['OM_PASSWORD'] = 'old-password'
        result = self.call('run', 'cdc', '--', 'cf', 'apps')
        self.assertEqual(result.returncode, 0, result.stderr)
        child = json.loads(self.marker.read_text())['env']
        self.assertFalse(any(key.endswith('_STALE') for key in child))
        self.assertEqual(child['OM_PASSWORD'], 'secret-$-value')

    def test_missing_endpoint_cannot_inherit_previous_foundation(self):
        self.write_env('CF_API=https://api.cdc.example\n')
        for cli, key in [('om', 'OM_TARGET'), ('bosh', 'BOSH_ENVIRONMENT'),
                         ('credhub', 'CREDHUB_SERVER')]:
            with self.subTest(cli=cli):
                self.env[key] = 'https://old.example'
                self.rejected('run', 'cdc', '--', cli, 'info')

    def test_each_supported_cli_runs(self):
        for cli in ('cf', 'om', 'bosh', 'credhub'):
            with self.subTest(cli=cli):
                result = self.call('run', 'cdc', '--', cli, 'info')
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_child_exit_status_is_preserved_without_retry(self):
        self.env['TEST_EXIT'] = '42'
        self.assertEqual(self.call('run', 'cdc', '--', 'cf', 'apps').returncode, 42)

    def test_failed_partial_export_is_not_evaluated(self):
        self.binary('cfctx-env', '''#!/bin/bash
printf 'touch %q\\n' "$TEST_MARKER"
exit 7
''')
        self.rejected('run', 'cdc', '--', 'cf', 'apps')

    def test_wrong_loaded_home(self):
        self.binary('cfctx-env', '#!/bin/bash\necho "export CF_HOME=/wrong"\n')
        self.rejected('run', 'cdc', '--', 'cf', 'apps')

    def test_target_mismatches(self):
        for change in [dict(Target='https://api.wrong.example'),
                       dict(OrganizationFields={'Name': 'wrong'}),
                       dict(SpaceFields={'Name': 'wrong'})]:
            with self.subTest(change=change):
                self.write_config(**change)
                self.rejected('run', 'cdc', '--', 'cf', 'apps')

    def test_invalid_or_missing_config_does_not_leak_content(self):
        self.config.write_text('secret-token invalid json')
        result = self.rejected('run', 'cdc', '--', 'cf', 'apps')
        self.assertNotIn('secret-token', result.stdout + result.stderr)
        self.config.unlink()
        self.rejected('run', 'cdc', '--', 'cf', 'apps')

    def test_missing_env_and_insecure_permissions(self):
        self.envfile.chmod(0o644)
        self.rejected('inspect', 'cdc')
        self.envfile.unlink()
        self.rejected('run', 'cdc', '--', 'cf', 'apps')

    def test_private_read_only_env_is_supported(self):
        self.envfile.chmod(0o400)
        self.assertEqual(self.call('inspect', 'cdc').returncode, 0)

    def test_invalid_names_and_unknown_context_do_not_create(self):
        for name in ('../cdc', '-x', '.hidden', 'with space', 'cdc\nother', 'typo'):
            with self.subTest(name=name):
                self.rejected('run', name, '--', 'cf', 'apps')
        self.assertEqual([p.name for p in self.root.iterdir()], ['cdc'])

    def test_invalid_interface(self):
        for args in [(), ('inspect',), ('inspect', 'cdc', 'extra'),
                     ('unknown', 'cdc'), ('run', 'cdc', 'cf', 'apps'),
                     ('run', 'cdc', '--', 'bash', '-c', 'true')]:
            with self.subTest(args=args):
                self.rejected(*args)

    def test_installer_copies_runtime_and_references_idempotently(self):
        for _ in range(2):
            result = subprocess.run(['/bin/bash', str(REPO / 'install.sh')],
                                    env=self.env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
        for location in ('.claude/skills', '.cursor/skills-cursor'):
            destination = self.base / location / 'cf-context'
            for source in (REPO / 'cf-context').rglob('*'):
                if source.is_file():
                    self.assertEqual(source.read_bytes(),
                                     (destination / source.relative_to(REPO / 'cf-context')).read_bytes())


if __name__ == '__main__':
    unittest.main(verbosity=2)
