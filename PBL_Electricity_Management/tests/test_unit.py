"""unittest entry point for the Python test cases (Module 1 unit cases, Module 2 API and integration cases).

    python -m unittest -v tests.test_unit
"""
import unittest

from . import api_cases, engine_cases


class DetectionEngineTests(unittest.TestCase):
    """Module 1 - unit tests of app/engine.py"""

    def test_cases(self):
        for c in engine_cases.CASES:
            with self.subTest(c["id"] + " " + c["scenario"]):
                self.assertEqual(c["expected"], c["run"]())


class DashboardApiAndIntegrationTests(unittest.TestCase):
    """Module 2 API tests and integration tests through the running server"""

    def test_cases(self):
        for c in api_cases.CASES:
            with self.subTest(c["id"] + " " + c["scenario"]):
                self.assertEqual(c["expected"], c["run"]())


if __name__ == "__main__":
    unittest.main()
