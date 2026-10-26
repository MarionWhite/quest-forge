#!/usr/bin/env python3
"""API-credit ledger for the Quest Forge harness.

$200/month of Anthropic API credits, split into lanes. Every API spend (api_run.py, batch.py)
appends one JSON line to ops/api-ledger.jsonl; this tool reads it back.

    py -3.10 -I tools/ops/ledger.py status [--json]
    py -3.10 -I tools/ops/ledger.py check LANE EST_USD [--reserve]    # exit 0 ok, non-zero = refuse
    py -3.10 -I tools/ops/ledger.py add LANE TASK MODEL COST [--run-id ID]   # manual correction

The API key is read only from ~/.qf/anthropic.key (see load_key); it is never logged.
"""
import argparse, calendar, datetime as dt, json, os, sys, uuid

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LEDGER = os.environ.get("QF_LEDGER") or os.path.join(REPO, "ops", "api-ledger.jsonl")
# C:\Users\a2dsu\.qf\anthropic.key on the PC, ~/.qf/anthropic.key on the Mac
KEY_FILE = os.path.join(os.path.expanduser("~"), ".qf", "anthropic.key")

# Monthly budgets, USD. Daily allowance = monthly / 30 (continuity: $90 -> $3/day).
LANES = {"continuity": 90.0, "batch": 50.0, "automation": 20.0, "reserve": 40.0}
NEEDS_FLAG = {"reserve"}  # only spendable with --reserve; no daily allowance
DAYS_PER_MONTH_FOR_DAILY = 30.0

# Per-million-token prices (USD) from the claude-api skill (cached 2026-10-06).
# Opus 5.5 / Sonnet 5.5 cache reads are $0.20 per the skill; Haiku 5.5 read is taken as 0.1x input.
# Cache writes (5 min) are 1.25x input.
PRICES = {
    "claude-opus-5-5":   {"in": 4.00, "out": 20.00, "cache_read": 0.20, "cache_write": 5.00},
    "claude-sonnet-5-5": {"in": 2.00, "out": 10.00, "cache_read": 0.20, "cache_write": 2.50},
    "claude-haiku-5-5":  {"in": 0.10, "out": 0.50,  "cache_read": 0.01, "cache_write": 0.125},
}
MODEL_IDS = {"opus": "claude-opus-5-5", "sonnet": "claude-sonnet-5-5", "haiku": "claude-haiku-5-5"}
BATCH_DISCOUNT = 0.5


def daily_allowance(lane):
    return None if lane in NEEDS_FLAG else LANES[lane] / DAYS_PER_MONTH_FOR_DAILY


def model_id(name):
    return MODEL_IDS.get(name, name)


def estimate_cost(model, input_tokens=0, output_tokens=0, cache_read=0, cache_write=0, batch=False):
    """Own estimate from token counts. Only a fallback: prefer the cost the API/CLI reports."""
    p = PRICES.get(model_id(model))
    if p is None:
        raise ValueError("no price for model %r" % model)
    usd = (input_tokens * p["in"] + output_tokens * p["out"]
           + cache_read * p["cache_read"] + cache_write * p["cache_write"]) / 1e6
    return round(usd * (BATCH_DISCOUNT if batch else 1.0), 6)


def load_key():
    """Return the API key from the key file. Exits with a clear message if absent. Never prints the key."""
    try:
        with open(KEY_FILE, "r", encoding="utf-8-sig") as f:
            key = f.read().strip()
    except OSError:
        sys.exit("No API key: %s does not exist. The owner has not created it yet "
                 "(one line, the Anthropic API key, nothing else). No global env var is set." % KEY_FILE)
    if not key:
        sys.exit("API key file %s is empty." % KEY_FILE)
    return key


def key_present():
    return os.path.isfile(KEY_FILE)


def scrub(text, key):
    return text.replace(key, "[key]") if key and text else text


def now_local():
    return dt.datetime.now().astimezone()


def read_records(path=None):
    path = path or LEDGER
    out = []
    if not os.path.exists(path):
        return out
    with open(path, "r", encoding="utf-8") as f:
        for ln, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except ValueError:
                print("ledger: skipping malformed line %d" % ln, file=sys.stderr)
    return out


def record(lane, task, model, cost_usd, input_tokens=0, output_tokens=0, cache_read_tokens=0,
           cache_write_tokens=0, run_id=None, path=None, when=None, source="reported"):
    if lane not in LANES:
        raise ValueError("unknown lane %r (lanes: %s)" % (lane, ", ".join(LANES)))
    rec = {
        "time": (when or now_local()).isoformat(timespec="seconds"),
        "lane": lane, "task": task, "model": model_id(model),
        "input_tokens": int(input_tokens), "output_tokens": int(output_tokens),
        "cache_read_tokens": int(cache_read_tokens), "cache_write_tokens": int(cache_write_tokens),
        "cost_usd": round(float(cost_usd), 6), "cost_source": source,
        "run_id": run_id or uuid.uuid4().hex[:12],
    }
    path = path or LEDGER
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(rec, separators=(",", ":")) + "\n")
    return rec


def has_record(run_id, task, path=None):
    return any(r.get("run_id") == run_id and r.get("task") == task for r in read_records(path))


def summarize(records=None, now=None, path=None):
    """Per-lane month-to-date / today spend, remaining, and projected month-end."""
    records = read_records(path) if records is None else records
    now = now or now_local()
    days_in_month = calendar.monthrange(now.year, now.month)[1]
    elapsed = (now.day - 1) + (now.hour * 3600 + now.minute * 60 + now.second) / 86400.0
    elapsed = max(elapsed, 1.0)  # don't over-project from the first hours of a month
    out = {}
    for lane, budget in LANES.items():
        month = day = 0.0
        for r in records:
            if r.get("lane") != lane:
                continue
            try:
                t = dt.datetime.fromisoformat(r["time"]).astimezone(now.tzinfo)
            except (KeyError, ValueError):
                continue
            if (t.year, t.month) == (now.year, now.month):
                month += r.get("cost_usd", 0.0)
                if t.day == now.day:
                    day += r.get("cost_usd", 0.0)
        allow = daily_allowance(lane)
        out[lane] = {
            "budget": budget, "month_spent": round(month, 4), "month_remaining": round(budget - month, 4),
            "daily_allowance": allow, "today_spent": round(day, 4),
            "today_remaining": None if allow is None else round(allow - day, 4),
            "projected_month_end": round(month / elapsed * days_in_month, 2),
        }
    return out


def check(lane, est_usd, reserve=False, records=None, now=None, path=None):
    """Return (ok, code, message). code: 0 ok, 2 daily, 3 monthly, 4 needs --reserve, 5 unknown lane."""
    if lane not in LANES:
        return False, 5, "unknown lane %r (lanes: %s)" % (lane, ", ".join(LANES))
    if lane in NEEDS_FLAG and not reserve:
        return False, 4, "lane %s needs --reserve (owner-approved spending only)" % lane
    s = summarize(records, now, path)[lane]
    eps = 1e-9
    if s["today_remaining"] is not None and est_usd > s["today_remaining"] + eps:
        return False, 2, "lane %s: est $%.2f exceeds today's remaining $%.2f (allowance $%.2f/day)" % (
            lane, est_usd, max(s["today_remaining"], 0), s["daily_allowance"])
    if est_usd > s["month_remaining"] + eps:
        return False, 3, "lane %s: est $%.2f exceeds month remaining $%.2f (budget $%.0f)" % (
            lane, est_usd, max(s["month_remaining"], 0), s["budget"])
    return True, 0, "ok: lane %s, est $%.2f, today left %s, month left $%.2f" % (
        lane, est_usd, "n/a" if s["today_remaining"] is None else "$%.2f" % s["today_remaining"],
        s["month_remaining"])


def headroom(lane, records=None, now=None, path=None):
    """Largest spend that would still pass check()."""
    s = summarize(records, now, path)[lane]
    caps = [s["month_remaining"]]
    if s["today_remaining"] is not None:
        caps.append(s["today_remaining"])
    return max(0.0, min(caps))


def _fmt(v):
    return "n/a" if v is None else "%.2f" % v


def cmd_status(a):
    s = summarize()
    if a.json:
        print(json.dumps(s, indent=1))
        return 0
    print("API credits, %s (ledger: %s)" % (now_local().strftime("%Y-%m-%d"), os.path.relpath(LEDGER, REPO)))
    print("%-11s %8s %8s %8s | %8s %8s %8s | %9s" % (
        "lane", "budget", "month", "left", "day-cap", "today", "left", "projected"))
    tot = [0.0, 0.0, 0.0]
    for lane, v in s.items():
        print("%-11s %8.2f %8.2f %8.2f | %8s %8.2f %8s | %9.2f%s" % (
            lane, v["budget"], v["month_spent"], v["month_remaining"],
            _fmt(v["daily_allowance"]), v["today_spent"], _fmt(v["today_remaining"]),
            v["projected_month_end"], "  (needs --reserve)" if lane in NEEDS_FLAG else ""))
        tot[0] += v["budget"]; tot[1] += v["month_spent"]; tot[2] += v["projected_month_end"]
    print("%-11s %8.2f %8.2f %8.2f | %28s | %9.2f" % ("total", tot[0], tot[1], tot[0] - tot[1], "", tot[2]))
    return 0


def cmd_check(a):
    ok, code, msg = check(a.lane, a.est_usd, a.reserve)
    print(msg, file=sys.stdout if ok else sys.stderr)
    return code


def cmd_add(a):
    print(json.dumps(record(a.lane, a.task, a.model, a.cost, run_id=a.run_id, source="manual")))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("status"); p.add_argument("--json", action="store_true"); p.set_defaults(fn=cmd_status)
    p = sub.add_parser("check"); p.add_argument("lane"); p.add_argument("est_usd", type=float)
    p.add_argument("--reserve", action="store_true"); p.set_defaults(fn=cmd_check)
    p = sub.add_parser("add"); p.add_argument("lane"); p.add_argument("task"); p.add_argument("model")
    p.add_argument("cost", type=float); p.add_argument("--run-id"); p.set_defaults(fn=cmd_add)
    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
