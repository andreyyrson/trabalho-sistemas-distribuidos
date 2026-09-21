import unittest

from server import compare, int_param


class IntParamTest(unittest.TestCase):
    def test_uses_default_when_missing(self):
        self.assertEqual(int_param({}, "docs", 300, 2, 5000), 300)

    def test_rejects_non_integer(self):
        with self.assertRaises(ValueError):
            int_param({"docs": ["abc"]}, "docs", 300, 2, 5000)

    def test_rejects_out_of_range(self):
        with self.assertRaises(ValueError):
            int_param({"docs": ["999999"]}, "docs", 300, 2, 5000)


class CompareTest(unittest.TestCase):
    def test_parallel_result_matches_sequential(self):
        report = compare(n_docs=30, processes=2)
        self.assertTrue(report["results_match"])
        self.assertEqual(report["pairs"], 30 * 29 // 2)


if __name__ == "__main__":
    unittest.main()
