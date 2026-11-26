import json
import math
import unittest

from _load import load, example

ue = load("founder-cfo", "unit_economics")


def spec():
    with open(example("founder-cfo", "example.json"), encoding="utf-8") as fh:
        return json.load(fh)


class UnitEconomics(unittest.TestCase):
    def test_example_reproduces_the_plan(self):
        a = ue.analyse(spec())
        self.assertAlmostEqual(a["contribution"], 4.76, places=2)
        self.assertEqual(round(a["margin_at_plan"] * 100), 38)
        self.assertEqual(math.ceil(a["breakeven_per_day"]), 186)
        self.assertEqual(round(a["year1_profit"]), 93926)
        self.assertEqual(a["startup"], 25280)
        self.assertEqual(a["payback_month"], 8)
        self.assertEqual(round(a["cash_needed"]), 34092)
        self.assertEqual(a["flags"], [])

    def test_price_below_variable_cost_is_flagged(self):
        s = spec()
        s["price"] = 1.50
        a = ue.analyse(s)
        self.assertTrue(math.isinf(a["breakeven_per_day"]))
        self.assertTrue(any("loses money" in f for f in a["flags"]))

    def test_breakeven_above_capacity_is_flagged(self):
        s = spec()
        s["capacity_per_day"] = 150
        a = ue.analyse(s)
        self.assertTrue(any("capacity is 150" in f for f in a["flags"]))

    def test_what_ifs_move_the_right_way(self):
        base = ue.analyse(spec())
        cheaper = ue.analyse(spec(), price=base["price"] * 0.9)
        fewer = ue.analyse(spec(), volume=0.8)
        self.assertLess(cheaper["year1_profit"], base["year1_profit"])
        self.assertGreater(cheaper["breakeven_per_day"], base["breakeven_per_day"])
        self.assertLess(fewer["year1_profit"], base["year1_profit"])
        self.assertEqual(len(ue.sensitivity(spec())), 4)

    def test_bad_input_is_refused_not_guessed(self):
        s = spec()
        s["ramp_per_day"] = [100] * 11
        with self.assertRaises(ue.NumbersError):
            ue.analyse(s)
        s = spec()
        del s["price"]
        with self.assertRaises(ue.NumbersError):
            ue.analyse(s)
        s = spec()
        s["variable"][0]["cost"] = "lots"
        with self.assertRaises(ue.NumbersError):
            ue.analyse(s)

    def test_report_shows_fractional_daily_break_even(self):
        s = {"price": 100, "unit": "order", "fixed_monthly": [{"cost": 500}],
             "days_per_month": 20, "plan_per_day": 1}
        text = ue.report(s, ue.analyse(s))
        self.assertIn("0.25 orders a day (5.0 a month)", text)
        self.assertRegex(text, r"\| Base plan \| [^|]+ \| 0\.25 \|")

    def test_report_mentions_the_key_numbers(self):
        s = spec()
        text = ue.report(s, ue.analyse(s))
        for needle in ("$4.76", "186 cups a day", "**38%**", "$93,926", "month 8"):
            self.assertIn(needle, text)


if __name__ == "__main__":
    unittest.main()
