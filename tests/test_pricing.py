import csv
import os
import tempfile
import unittest

from _load import load

vw = load("founder-pricing", "van_westendorp")


def rows(n=40):
    out = []
    for i in range(n):
        k = i / float(n - 1)
        out.append((2.5 + k, 4.0 + k, 6.0 + 1.5 * k, 7.5 + 2 * k))
    return out


class Pricing(unittest.TestCase):
    def test_points_are_ordered_and_inside_the_answers(self):
        res = vw.analyse(rows())
        p = res["points"]
        for k in ("PMC", "PME", "OPP", "IPP"):
            self.assertIsNotNone(p[k], k)
            self.assertTrue(2.5 <= p[k] <= 9.5, (k, p[k]))
        self.assertLess(p["PMC"], p["PME"])
        self.assertLessEqual(p["PMC"], p["OPP"])
        self.assertLessEqual(p["OPP"], p["PME"])

    def test_out_of_order_and_incomplete_rows_are_dropped(self):
        d = tempfile.mkdtemp()
        path = os.path.join(d, "p.csv")
        with open(path, "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(vw.KEYS)
            for r in rows(10):
                w.writerow(r)
            w.writerow((9, 4, 6, 8))       # too cheap above a bargain: out of order
            w.writerow((3, "", 6, 8))      # incomplete
        got, dropped = vw.read(path)
        self.assertEqual((len(got), dropped), (10, 2))

    def test_decimal_comma_is_not_a_thousands_separator(self):
        self.assertEqual(vw._f("12,50"), 12.5)
        self.assertEqual(vw._f("1,234"), 1234.0)
        self.assertEqual(vw._f("1,234.56"), 1234.56)

    def test_too_few_answers_is_refused(self):
        with self.assertRaises(vw.PricingError):
            vw.analyse(rows(4))

    def test_report_places_the_price(self):
        res = vw.analyse(rows())
        self.assertIn("**inside** the acceptable range", vw.report(res, 0, price=6.5))
        self.assertIn("**above** the acceptable range", vw.report(res, 0, price=40))


if __name__ == "__main__":
    unittest.main()
