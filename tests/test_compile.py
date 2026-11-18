import json
import os
import shutil
import tempfile
import unittest

from _load import load, example

plan = load("founder-plan", "compile")


class Compile(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        with open(os.path.join(self.d, "idea.md"), "w") as fh:
            fh.write("# Moss Matcha Bar\n\nA walk-in matcha cafe on King St W.\n")

    def tearDown(self):
        shutil.rmtree(self.d)

    def numbers(self, **change):
        with open(example("founder-cfo", "example.json")) as fh:
            s = json.load(fh)
        s.update(change)
        with open(os.path.join(self.d, "numbers.json"), "w") as fh:
            json.dump(s, fh)

    def panel(self, buys, n=100):
        os.makedirs(os.path.join(self.d, "panel"), exist_ok=True)
        with open(os.path.join(self.d, "panel", "results.json"), "w") as fh:
            json.dump({"buys": buys, "passes": n - buys, "answered": n, "buy_rate": buys / float(n)}, fh)

    def test_no_numbers_is_incomplete(self):
        v, text = plan.compile_plan(self.d)
        self.assertEqual(v, "Incomplete")
        self.assertIn("run /founder-cfo", text)

    def test_good_numbers_and_panel_is_profitable(self):
        self.numbers()
        self.panel(40)
        v, text = plan.compile_plan(self.d)
        self.assertEqual(v, "Profitable")
        self.assertTrue(text.startswith("# Moss Matcha Bar · Business plan"))
        self.assertIn("| Profit margin at plan | 38% per cup |", text)
        self.assertIn("40 buy · 60 pass", text)
        self.assertIn("- The buyer panel: run /founder-consumer", text.replace("## Not done yet", ""))

    def test_a_weak_panel_means_not_yet(self):
        self.numbers()
        self.panel(12)
        v, text = plan.compile_plan(self.d)
        self.assertEqual(v, "Not yet")
        self.assertIn("✗ 12 of 100 simulated buyers buy", text)

    def test_losing_money_means_not_yet(self):
        self.numbers(price=3.00)
        v, _ = plan.compile_plan(self.d)
        self.assertEqual(v, "Not yet")

    def test_missing_cost_lists_are_never_profitable(self):
        # the reported bug: no cost lists at all used to compile as Profitable
        with open(os.path.join(self.d, "numbers.json"), "w") as fh:
            json.dump({"business": "x", "unit": "cup", "price": 6.5, "plan_per_day": 100}, fh)
        self.panel(40)
        v, text = plan.compile_plan(self.d)
        self.assertEqual(v, "Incomplete")
        self.assertIn("numbers.json cannot be used", text)

    def test_empty_cost_lists_mean_not_yet(self):
        self.numbers(variable=[], fixed_monthly=[], startup=[])
        self.panel(40)
        v, text = plan.compile_plan(self.d)
        self.assertEqual(v, "Not yet")
        self.assertIn("No costs at all are listed", text)

    def test_broken_files_do_not_crash(self):
        with open(os.path.join(self.d, "numbers.json"), "w") as fh:
            fh.write("{not json")
        v, _ = plan.compile_plan(self.d)
        self.assertEqual(v, "Incomplete")
        self.numbers()
        os.makedirs(os.path.join(self.d, "panel"), exist_ok=True)
        with open(os.path.join(self.d, "panel", "results.json"), "w") as fh:
            fh.write("{}")
        v, text = plan.compile_plan(self.d)
        self.assertEqual(v, "Not yet")
        self.assertIn("panel/results.json cannot be used", text)


if __name__ == "__main__":
    unittest.main()
