# SPDX-License-Identifier: GPL-3.0-or-later
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]


class DeliveryPolicy(unittest.TestCase):
    def test_minimal_apt_containers_install_ca_certificates_before_checkout(self):
        for name in ('checks.yml', 'packages.yml'):
            with self.subTest(workflow=name):
                workflow = (ROOT / '.github/workflows' / name).read_text()
                commands = re.findall(r'run: (apt-get update && apt-get install[^\n]+)', workflow)
                self.assertTrue(commands, 'APT bootstrap must run before checkout')
                for command in commands:
                    self.assertIn('ca-certificates', command.split())
                self.assertLess(workflow.index(commands[0]), workflow.index('uses: actions/checkout@'))

    def test_pre_merge_checks_do_not_build_or_install_packages(self):
        workflow = (ROOT / '.github/workflows/checks.yml').read_text()
        for command in ('tools/build-deb.py', 'tools/build-rpm.py', 'deb-lifecycle.py'):
            self.assertNotIn(command, workflow)

    def test_package_workflow_requires_successful_main_push_checks(self):
        path = ROOT / '.github/workflows/packages.yml'
        self.assertTrue(path.is_file(), 'Post-merge packaging workflow is missing')
        workflow = path.read_text()
        for guard in ('workflow_run:', 'workflows: ["Product checks"]', 'types: [completed]',
                      'branches: [main]', "github.event.workflow_run.conclusion == 'success'",
                      "github.event.workflow_run.event == 'push'",
                      "github.event.workflow_run.head_branch == 'main'",
                      'github.event.workflow_run.head_repository.full_name == github.repository',
                      'ref: ${{ github.event.workflow_run.head_sha }}'):
            self.assertIn(guard, workflow)
        self.assertNotIn('workflow_dispatch:', workflow)
        self.assertNotIn('gh release', workflow)
        self.assertNotIn('contents: write', workflow)

    def test_native_archive_unit_test_is_explicitly_opt_in(self):
        tests = (ROOT / 'tests/unit/test_deb_packaging.py').read_text()
        self.assertIn("os.environ.get('PBI_PACKAGE_BUILD_TESTS') == '1'", tests)

    def test_source_rpm_carries_the_workflow_contract_tests_need(self):
        builder = (ROOT / 'tools/build-rpm.py').read_text()
        self.assertIn("'.github'", builder)


if __name__ == '__main__':
    unittest.main()
