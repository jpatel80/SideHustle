"""Tests for scripts/kdp_pricing.py. Run: python3 -m unittest discover -s tests -v"""
import contextlib
import importlib.util
import io
import json
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "kdp_pricing", Path(__file__).resolve().parent.parent / "scripts" / "kdp_pricing.py"
)
kp = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(kp)


class PricingTests(unittest.TestCase):
    def test_trim_class(self):
        self.assertEqual(kp.trim_class((8.5, 11)), "large")
        self.assertEqual(kp.trim_class((6, 9)), "regular")
        self.assertEqual(kp.trim_class((6.14, 9)), "large")

    def test_printing_cost_short_books_are_fixed(self):
        for pages in (24, 64, 104, 110):
            self.assertEqual(kp.printing_cost(pages), 2.84)
        self.assertEqual(kp.printing_cost(64, (6, 9)), 2.30)

    def test_printing_cost_long_books_add_per_page(self):
        self.assertEqual(kp.printing_cost(112), round(1.00 + 112 * 0.017, 2))
        self.assertEqual(kp.printing_cost(200, (6, 9)), round(1.00 + 200 * 0.012, 2))

    def test_page_limits(self):
        with self.assertRaises(ValueError):
            kp.printing_cost(23)
        with self.assertRaises(ValueError):
            kp.printing_cost(829)

    def test_royalty_rate_threshold(self):
        self.assertEqual(kp.royalty_rate(9.98), 0.50)
        self.assertEqual(kp.royalty_rate(9.99), 0.60)
        self.assertEqual(kp.royalty_rate(7.99), 0.50)

    def test_royalty_examples(self):
        # the figures the audit corrected: 7.99 is a 50% price
        self.assertEqual(kp.royalty(7.99, 64), 1.16)   # 3.995 - 2.84 = 1.155
        self.assertEqual(kp.royalty(6.99, 64), 0.66)
        self.assertEqual(kp.royalty(8.99, 64), 1.66)
        self.assertEqual(kp.royalty(9.99, 104), 3.15)

    def test_min_list_price(self):
        self.assertEqual(kp.min_list_price(64), 5.68)          # 2.84 / 0.50
        # a long book whose 50% minimum would be above 9.98 uses the 60% rate
        pages = 300                                             # cost 6.10 -> 12.20 at 50%, 10.17 at 60%
        self.assertEqual(kp.min_list_price(pages), 10.17)
        self.assertGreaterEqual(kp.royalty(kp.min_list_price(pages), pages), 0)

    def test_sales_for_target(self):
        self.assertEqual(kp.sales_for_target(300, 9.99, 104), 96)   # 300 / 3.15
        self.assertEqual(kp.sales_for_target(300, 7.99, 64), 259)   # 300 / 1.16
        self.assertIsNone(kp.sales_for_target(300, 5.00, 64))

    def test_cli_json_and_markdown(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = kp.main(["--pages", "64", "--price", "7.99", "--json"])
        self.assertEqual(code, 0)
        data = json.loads(out.getvalue())
        self.assertEqual(data["rows"][0]["royalty"], 1.16)
        self.assertEqual(data["min_list_price"], 5.68)
        self.assertIn("| $9.99 | 60% | $2.84 | $3.15 |", kp.markdown_table(64))

    def test_cli_rejects_bad_page_count(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(kp.main(["--pages", "10"]), 2)


if __name__ == "__main__":
    unittest.main()
