"""Unit tests for ledger math. Spends nothing.   py -3.10 -I tools/ops/test_ledger.py"""
import datetime as dt, os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ledger

TZ = dt.timezone.utc
NOW = dt.datetime(2026, 10, 15, 12, 0, tzinfo=TZ)


def rec(lane, cost, day=15, month=10):
    return {"time": dt.datetime(2026, month, day, 9, 0, tzinfo=TZ).isoformat(), "lane": lane, "cost_usd": cost}


class T(unittest.TestCase):
    def test_daily_allowances(self):
        self.assertAlmostEqual(ledger.daily_allowance("continuity"), 3.0)
        self.assertAlmostEqual(ledger.daily_allowance("batch"), 50 / 30)
        self.assertAlmostEqual(ledger.daily_allowance("automation"), 20 / 30)
        self.assertIsNone(ledger.daily_allowance("reserve"))

    def test_prices_and_batch_discount(self):
        self.assertAlmostEqual(ledger.estimate_cost("opus", 1_000_000, 1_000_000), 24.0)
        self.assertAlmostEqual(ledger.estimate_cost("sonnet", 1_000_000, 100_000, batch=True), 1.5)
        self.assertAlmostEqual(ledger.estimate_cost("haiku", 0, 0, cache_read=1_000_000, cache_write=1_000_000), 0.135)

    def test_summarize_month_and_day(self):
        rs = [rec("continuity", 2.0), rec("continuity", 1.0, day=3), rec("continuity", 9.0, month=9)]
        s = ledger.summarize(rs, NOW)["continuity"]
        self.assertAlmostEqual(s["month_spent"], 3.0)
        self.assertAlmostEqual(s["today_spent"], 2.0)
        self.assertAlmostEqual(s["today_remaining"], 1.0)
        self.assertAlmostEqual(s["month_remaining"], 87.0)
        self.assertAlmostEqual(s["projected_month_end"], round(3.0 / 14.5 * 31, 2))

    def test_check_daily_monthly_reserve(self):
        rs = [rec("continuity", 2.5)]
        self.assertTrue(ledger.check("continuity", 0.5, records=rs, now=NOW)[0])
        ok, code, _ = ledger.check("continuity", 0.51, records=rs, now=NOW)
        self.assertEqual((ok, code), (False, 2))
        big = [rec("automation", 19.9, day=2)]
        self.assertEqual(ledger.check("automation", 0.2, records=big, now=NOW)[1], 3)
        self.assertEqual(ledger.check("reserve", 1, records=[], now=NOW)[1], 4)
        self.assertTrue(ledger.check("reserve", 39, reserve=True, records=[], now=NOW)[0])
        self.assertEqual(ledger.check("reserve", 41, reserve=True, records=[], now=NOW)[1], 3)
        self.assertEqual(ledger.check("nope", 1, records=[], now=NOW)[1], 5)

    def test_headroom(self):
        self.assertAlmostEqual(ledger.headroom("continuity", [rec("continuity", 1.0)], NOW), 2.0)

    def test_record_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "l.jsonl")
            ledger.record("batch", "t", "sonnet", 0.1234567, 10, 5, run_id="r1", path=p)
            self.assertTrue(ledger.has_record("r1", "t", p))
            self.assertFalse(ledger.has_record("r1", "other", p))
            r = ledger.read_records(p)[0]
            self.assertEqual((r["cost_usd"], r["model"]), (0.123457, "claude-sonnet-5-5"))


if __name__ == "__main__":
    unittest.main()
