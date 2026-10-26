"""unittest entry point for the Python test cases (Module 1, Module 2 and integration).

    python -m unittest -v tests.test_all
"""
import unittest

from . import integration_cases, m1_cases, m2_cases


class Module1Tests(unittest.TestCase):
    """Module 1 - Job Posting and Eligibility Verification (unit + API)"""

    def test_cases(self):
        for c in m1_cases.CASES:
            with self.subTest(c["id"] + " " + c["scenario"]):
                self.assertEqual(c["expected"], c["run"]())


class Module2Tests(unittest.TestCase):
    """Module 2 - Job Application and Tracking (unit + API)"""

    def test_cases(self):
        for c in m2_cases.CASES:
            with self.subTest(c["id"] + " " + c["scenario"]):
                self.assertEqual(c["expected"], c["run"]())


class IntegrationTests(unittest.TestCase):
    def test_cases(self):
        for c in integration_cases.CASES:
            with self.subTest(c["id"] + " " + c["scenario"]):
                self.assertEqual(c["expected"], c["run"]())


if __name__ == "__main__":
    unittest.main()
