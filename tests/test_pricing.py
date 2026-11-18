import csv
import json
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

    def test_decimal_commas_are_read_as_decimals(self):
        cases = {
            "12,50": 12.5, "12,5": 12.5, "12.50": 12.5, "1,250": 1250.0, "1,250.50": 1250.5,
            "1.250,50": 1250.5, "1 250,50": 1250.5, "1 250,50 €": 1250.5, "$12": 12.0, "12 EUR": 12.0,
            "CA$9.99": 9.99, "1.250.000": 1250000.0, 7: 7.0, 7.25: 7.25,
        }
        for text, want in cases.items():
            self.assertAlmostEqual(vw.parse_number(text), want, msg=repr(text))
        for junk in ("lots", "1,2,3", "12,50,00", "", None, True, "1.2.3", "12,5.0"):
            self.assertIsNone(vw.parse_number(junk), repr(junk))
        self.assertAlmostEqual(vw.parse_number("1,250", "comma"), 1.25)
        self.assertAlmostEqual(vw.parse_number("1.250", "comma"), 1250.0)
        self.assertIsNone(vw.parse_number("12,50", "point"))

    def test_answers_folder_with_typed_decimal_commas(self):
        # the reported bug: "12,50" used to become 1250
        d = tempfile.mkdtemp()
        for i, r in enumerate(rows(10)):
            a = {"id": "P%03d" % (i + 1)}
            for k, v in zip(vw.KEYS, r):
                a["price_" + k] = ("%.2f" % v).replace(".", ",")
            with open(os.path.join(d, "P%03d.json" % (i + 1)), "w") as fh:
                json.dump(a, fh)
        got, dropped = vw.read(d)
        self.assertEqual((len(got), dropped), (10, 0))
        self.assertTrue(all(r[3] < 10 for r in got), got)

    def test_semicolon_csv_from_european_excel(self):
        d = tempfile.mkdtemp()
        path = os.path.join(d, "p.csv")
        with open(path, "w", newline="", encoding="utf-8") as fh:
            fh.write(";".join(vw.KEYS) + "\r\n")
            for r in rows(10):
                fh.write(";".join(("%.2f" % v).replace(".", ",") for v in r) + "\r\n")
        got, dropped = vw.read(path)
        self.assertEqual((len(got), dropped), (10, 0))
        self.assertAlmostEqual(got[0][0], 2.5)

    def test_too_few_answers_is_refused(self):
        with self.assertRaises(vw.PricingError):
            vw.analyse(rows(4))

    def test_report_places_the_price(self):
        res = vw.analyse(rows())
        self.assertIn("**inside** the acceptable range", vw.report(res, 0, price=6.5))
        self.assertIn("**above** the acceptable range", vw.report(res, 0, price=40))


if __name__ == "__main__":
    unittest.main()
