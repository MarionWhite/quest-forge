"""Unit tests for ledger math. Spends nothing.   py -3.10 -I tools/ops/test_ledger.py"""
import datetime as dt, os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ledger

TZ = dt.timezone.utc
NOW = dt.datetime(2026, 10, 15, 12, 0, tzinfo=TZ)


def rec(lane, cost, day=15, month=10):
    return {"time": dt.datetime(2026, month, day, 9, 0, tzinfo=TZ).isoformat(), "lane": lane, "cost_usd": cost}


class T(unittest.TestCase):
    def test_caps(self):
        self.assertEqual((ledger.MONTH_CAP, ledger.DAY_CAP), (200.0, 50.0))

    def test_prices_and_batch_discount(self):
        self.assertAlmostEqual(ledger.estimate_cost("opus", 1_000_000, 1_000_000), 24.0)
        self.assertAlmostEqual(ledger.estimate_cost("sonnet", 1_000_000, 100_000, batch=True), 1.5)
        self.assertAlmostEqual(ledger.estimate_cost("haiku", 0, 0, cache_read=1_000_000, cache_write=1_000_000), 0.135)

    def test_summarize_month_and_day(self):
        rs = [rec("continuity", 2.0), rec("batch", 1.5), rec("continuity", 1.0, day=3), rec("continuity", 9.0, month=9)]
        s = ledger.summarize(rs, NOW)
        c, t = s["lanes"]["continuity"], s["total"]
        self.assertAlmostEqual(c["month_spent"], 3.0)
        self.assertAlmostEqual(c["today_spent"], 2.0)
        self.assertAlmostEqual(c["projected_month_end"], round(3.0 / 14.5 * 31, 2))
        self.assertAlmostEqual(t["today_spent"], 3.5)
        self.assertAlmostEqual(t["today_remaining"], 46.5)
        self.assertAlmostEqual(t["month_remaining"], 195.5)

    def test_check_daily_monthly_pooled(self):
        rs = [rec("continuity", 30.0), rec("batch", 19.5)]  # $49.50 today across two lanes
        self.assertTrue(ledger.check("automation", 0.5, records=rs, now=NOW)[0])
        self.assertEqual(ledger.check("automation", 0.51, records=rs, now=NOW)[:2], (False, 2))
        big = [rec("continuity", 45.0, day=d) for d in (2, 3, 4, 5)]  # $180 this month, none today
        self.assertTrue(ledger.check("batch", 20, records=big, now=NOW)[0])
        self.assertEqual(ledger.check("batch", 20.01, records=big, now=NOW)[1], 3)
        self.assertTrue(ledger.check("reserve", 10, records=[], now=NOW)[0])  # no --reserve gate
        self.assertEqual(ledger.check("nope", 1, records=[], now=NOW)[1], 5)

    def test_headroom(self):
        self.assertAlmostEqual(ledger.headroom("continuity", [rec("batch", 1.0)], NOW), 49.0)
        big = [rec("continuity", 45.0, day=d) for d in (2, 3, 4, 5)]
        self.assertAlmostEqual(ledger.headroom("continuity", big + [rec("batch", 5.0)], NOW), 15.0)

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
