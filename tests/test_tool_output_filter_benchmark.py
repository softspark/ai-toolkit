from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
BENCHMARK_PATH = REPOSITORY_ROOT / "scripts" / "benchmark_output_filter.py"


class OutputFilterBenchmarkTests(unittest.TestCase):
    def test_benchmark_reports_passing_bounded_scenarios(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(BENCHMARK_PATH),
                "--json",
                "--max-input-bytes",
                str(128 * 1024),
            ],
            text=True,
            capture_output=True,
            cwd=REPOSITORY_ROOT,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            check=False,
        )

        self.assertEqual(0, result.returncode, result.stderr)
        report = json.loads(result.stdout)
        self.assertTrue(report["passed"])
        self.assertTrue(report["coldHookEnforced"])
        self.assertGreaterEqual(len(report["scenarios"]), 2)
        cold_hook = report["coldHook"]
        self.assertTrue(cold_hook["passed"])
        self.assertEqual("bash-wrapper", cold_hook["adapter"])
        self.assertTrue(cold_hook["sessionReused"])
        self.assertEqual(100, cold_hook["iterations"])
        self.assertEqual(75.0, cold_hook["maxP95Ms"])
        self.assertGreater(cold_hook["p95Ms"], 0)
        self.assertLess(
            cold_hook["emittedBytes"],
            cold_hook["inputBytes"],
        )
        for scenario in report["scenarios"]:
            self.assertTrue(scenario["passed"])
            self.assertLess(
                scenario["candidateBytes"],
                scenario["inputBytes"],
            )
            self.assertGreaterEqual(scenario["savingsRatio"], 0.3)


if __name__ == "__main__":
    unittest.main()
