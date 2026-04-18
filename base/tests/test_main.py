"""
E2E test orchestrator for main.py.

Pattern:
- setUpClass   : create temp dirs, seed fixtures or configure mocks
- tearDownClass: clean up all temp artifacts
- Each test patches external I/O (APIs, DBs, filesystems) and verifies
  orchestration logic through the main() entry point.

Add project-specific E2E tests here as the project grows.
Unit tests live in tests/<domain>/test_<module>.py.
"""

import shutil
import unittest
from pathlib import Path
from unittest.mock import patch


class TestMainE2E(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.test_dir = Path("tests/tmp_e2e")
        cls.test_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def tearDownClass(cls) -> None:
        if cls.test_dir.exists():
            shutil.rmtree(cls.test_dir)

    @patch("src.utils.m_log.setup_logging")
    @patch("src.utils.m_log.f_log_execution")
    @patch("src.utils.m_log.f_log")
    def test_main_runs(self, mock_f_log, mock_execution, mock_setup) -> None:
        """Smoke test: main() executes without raising exceptions."""
        from main import main
        main()
        mock_setup.assert_called_once()
        mock_f_log.assert_called()

    # ---------------------------------------------------------------------------
    # Template: add project-specific E2E tests below.
    #
    # Example pattern for testing orchestration through main():
    #
    #   @patch("src.<domain>.<ExternalDependency>")
    #   @patch("main.<Orchestrator>")
    #   def test_pipeline_e2e(self, mock_orch, mock_dep):
    #       mock_dep.return_value = self.test_dir / "fixture.db"
    #
    #       main()
    #
    #       mock_orch.assert_called_once()
    #       mock_orch.return_value.run.assert_called_once()
    # ---------------------------------------------------------------------------


if __name__ == "__main__":
    unittest.main()
