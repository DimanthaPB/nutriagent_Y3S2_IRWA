"""Optional Node-based JS regression checks; no frontend packages needed."""
import shutil
import subprocess
import unittest
from pathlib import Path


@unittest.skipUnless(shutil.which("node"), "Node is required for frontend JavaScript checks")
class FrontendTests(unittest.TestCase):
    def check(self, scenario):
        result = subprocess.run([shutil.which("node"), str(Path(__file__).with_name("frontend_regressions.js")), scenario],
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_logout_invalidates_login_and_duplicate_submit_is_ignored(self):
        self.check("stale")

    def test_process_401_clears_session(self):
        self.check("unauthorized")

    def test_rate_limit_and_non_json_errors(self):
        self.check("errors")
