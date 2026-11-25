#!/usr/bin/env python3
"""Run one bounded harness task as headless Claude Code (`claude -p`) on API credits.

    py -3.10 -I tools/ops/api_run.py --lane continuity --model sonnet --task r008-shader \
        --checkpoint r008-shader                      # resume ops/checkpoints/r008-shader.md
    py -3.10 -I tools/ops/api_run.py --lane automation --model haiku --task triage "did X finish?"
    py -3.10 -I tools/ops/api_run.py --lane batch ...   # (batch lane is for batch.py; allowed but unusual)

    --brief ops/briefs/x.md | --prompt-file F | PROMPT   what to do (briefs may be combined with PROMPT)
    --checkpoint NAME      "resume from ops/checkpoints/NAME.md, do the next step, checkpoint, exit"
    --est-usd N            estimate used for the ledger check (default 1.00)
    --max-usd N            hard cap for this run, passed to claude --max-budget-usd (default 5.00,
                           and never more than the remaining $50/day or $200/month across all lanes)
    --reserve              accepted and ignored (no lane needs approval since 2026-10-26)
    --dry-run              print the plan (command, ledger check) and exit; no key needed, no spend

    Overflow (subscription nearly or fully used):
    --when-subscription-limited   only run if the subscription is known to be limited; otherwise exit 0
                                  doing nothing. Continuity lane only (auto-overflow is approved there,
                                  within the shared daily cap). "Known limited" = the 5-hour session OR the
                                  weekly limit is at or above --limit-pct (default 90, the owner's choice
                                  2026-10-26: switch at 90 % so 10 % of the subscription stays in reserve),
                                  or the marker file ~/.qf/subscription-limited exists and has not expired,
                                  or --probe says so.
    --limit-pct N                 the usage threshold, percent (default 90; env QF_LIMIT_PCT).
    --usage                       print the subscription's current usage and whether it counts as limited.
    --mark-limited [ISO_TIME]     write the marker (default: expires in 5 h). Call it when a subscription
                                  session reports it hit the limit; then call api_run with
                                  --when-subscription-limited --checkpoint NAME to carry on.
    --clear-limited               remove the marker.
    --probe                       with --when-subscription-limited: run a trivial subscription call
                                  (key NOT passed) and treat a "limit reached" reply as limited.

The key is read only from ~/.qf/anthropic.key and put only in the child's environment.
Permission mode: dontAsk + an explicit allowlist (see ALLOWED), never bypassPermissions.
"""
import argparse, datetime as dt, glob, json, os, shutil, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ledger

REPO = ledger.REPO
MARKER = os.path.join(os.path.dirname(ledger.KEY_FILE), "subscription-limited")

# dontAsk: anything not allowed is denied silently, so an unattended run can never stall on a prompt
# or wander outside the list. bypassPermissions is NOT used: the harness rules (live game never written,
# no client launches, no pushes) rely on tool-level limits as well as on the prompt.
PERMISSION_MODE = "dontAsk"
ALLOWED = ("Read,Glob,Grep,Edit,Write,"
           "Bash(py -3.10 -I tools/*),Bash(git status*),Bash(git diff*),Bash(git log*),"
           "Bash(git add *),Bash(git commit *)")
DENIED = ("Bash(py -3.10 -I tools/trial/trial.py install*),Bash(git push*),"
          "Bash(py -3.10 -I tools/renderq/renderq.py *--busy-ok*)")

LIMIT_WORDS = ("usage limit", "limit reached", "rate limit", "you've hit your", "quota")

# Subscription usage, as Claude Code's /usage shows it. Read with the owner's own Claude Code login
# (~/.claude/.credentials.json); the token is sent only to api.anthropic.com, never printed, logged or
# passed to the child. The endpoint is undocumented: any failure means "unknown" and the marker/probe
# rules still apply. An expired token is not refreshed here (that would rotate the owner's login).
USAGE_URL = "https://api.anthropic.com/api/oauth/usage"
CREDENTIALS = os.path.join(os.path.expanduser("~"), ".claude", ".credentials.json")
DEFAULT_LIMIT_PCT = float(os.environ.get("QF_LIMIT_PCT") or 90)


def subscription_usage():
    """{"session": (pct, resets_at), "weekly": (pct, resets_at)} or None if it cannot be read."""
    import urllib.request
    try:
        with open(CREDENTIALS, "r", encoding="utf-8") as f:
            o = json.load(f).get("claudeAiOauth") or {}
        tok = o.get("accessToken")
        exp = o.get("expiresAt")
        if not tok or (isinstance(exp, (int, float)) and exp / 1000.0 < dt.datetime.now().timestamp()):
            return None
        req = urllib.request.Request(USAGE_URL, headers={
            "Authorization": "Bearer " + tok, "anthropic-beta": "oauth-2025-04-20",
            "User-Agent": "quest-forge-api-run"})
        with urllib.request.urlopen(req, timeout=20) as r:
            d = json.load(r)
    except Exception:
        return None
    out = {}
    for key, name in (("five_hour", "session"), ("seven_day", "weekly")):
        w = d.get(key) or {}
        if isinstance(w.get("utilization"), (int, float)):
            out[name] = (float(w["utilization"]), w.get("resets_at"))
    return out or None


def over_threshold(pct):
    """(True/False/None, text). None = usage unknown."""
    u = subscription_usage()
    if not u:
        return None, "subscription usage unknown"
    text = ", ".join("%s %.0f%% (resets %s)" % (k, v[0], (v[1] or "?")[:16]) for k, v in u.items())
    return any(v[0] >= pct for v in u.values()), text


def find_claude(explicit=None):
    cands = [explicit, os.environ.get("CLAUDE_BIN"), shutil.which("claude")]
    for c in cands:
        if c and os.path.exists(c):
            return c
    home = os.path.expanduser("~")
    pats = [os.path.join(home, ".local", "bin", "claude.exe"), os.path.join(home, ".local", "bin", "claude"),
            os.path.join(home, ".*", "extensions", "anthropic.claude-code-*", "resources", "native-binary", "claude*")]
    for pat in pats:
        hits = sorted(glob.glob(pat), key=lambda p: [int(x) if x.isdigit() else 0
                                                     for x in os.path.basename(os.path.dirname(os.path.dirname(os.path.dirname(p)))).replace("-", ".").split(".")])
        hits = [h for h in hits if os.path.isfile(h) and not h.endswith((".map", ".txt"))]
        if hits:
            return hits[-1]
    sys.exit("claude CLI not found. Put it on PATH or set CLAUDE_BIN / --claude.")


def limited_now():
    try:
        with open(MARKER, "r", encoding="utf-8") as f:
            until = dt.datetime.fromisoformat(f.read().strip())
        if until.tzinfo is None:
            until = until.astimezone()
        return ledger.now_local() < until
    except (OSError, ValueError):
        return False


def mark_limited(until):
    os.makedirs(os.path.dirname(MARKER), exist_ok=True)
    if until:
        t = dt.datetime.fromisoformat(until)
        if t.tzinfo is None:
            t = t.astimezone()
    else:
        t = ledger.now_local() + dt.timedelta(hours=5)
    with open(MARKER, "w", encoding="utf-8") as f:
        f.write(t.isoformat(timespec="seconds"))
    print("subscription marked limited until %s" % t.isoformat(timespec="minutes"))


def probe_limited(claude):
    env = {k: v for k, v in os.environ.items() if k not in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")}
    try:
        p = subprocess.run([claude, "-p", "--model", ledger.MODEL_IDS["haiku"], "--no-session-persistence"],
                           input="Reply with the single word: ok", capture_output=True, text=True,
                           timeout=90, env=env, cwd=REPO)
    except (OSError, subprocess.TimeoutExpired):
        return False
    out = ((p.stdout or "") + (p.stderr or "")).lower()
    return p.returncode != 0 and any(w in out for w in LIMIT_WORDS)


def build_prompt(a):
    parts = []
    if a.brief:
        parts.append("Read CLAUDE.md first, then your brief at %s and carry it out." % a.brief)
    if a.checkpoint:
        parts.append("Resume from ops/checkpoints/%s.md (read CLAUDE.md first). Do the next step only, "
                     "update the checkpoint, and exit. This run has a hard API budget cap: "
                     "do not start work that cannot finish within it, and leave the checkpoint current." % a.checkpoint)
    if a.prompt_file:
        with open(a.prompt_file, "r", encoding="utf-8") as f:
            parts.append(f.read())
    if a.prompt:
        parts.append(a.prompt)
    if not parts:
        sys.exit("Give a PROMPT, --brief, --prompt-file or --checkpoint.")
    return "\n\n".join(parts)


def parse_result(stdout):
    """claude --output-format json prints one result object (older/newer builds may print a list of events)."""
    data = json.loads(stdout)
    if isinstance(data, list):
        data = next((x for x in reversed(data) if isinstance(x, dict) and x.get("type") == "result"), {})
    return data


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):  # agent replies carry non-cp1252 text (arrows, dashes)
        stream.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("prompt", nargs="?")
    ap.add_argument("--lane", choices=list(ledger.LANES))
    ap.add_argument("--model", choices=["opus", "sonnet", "haiku"])
    ap.add_argument("--task")
    ap.add_argument("--brief"); ap.add_argument("--prompt-file"); ap.add_argument("--checkpoint")
    ap.add_argument("--est-usd", type=float, default=1.00)
    ap.add_argument("--max-usd", type=float, default=5.00)
    ap.add_argument("--reserve", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--when-subscription-limited", action="store_true")
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--mark-limited", nargs="?", const="", metavar="ISO_TIME")
    ap.add_argument("--clear-limited", action="store_true")
    ap.add_argument("--limit-pct", type=float, default=DEFAULT_LIMIT_PCT)
    ap.add_argument("--usage", action="store_true")
    ap.add_argument("--claude")
    a = ap.parse_args(argv)

    if a.usage:
        hit, text = over_threshold(a.limit_pct)
        print("%s; threshold %.0f%% -> %s; marker %s" % (
            text, a.limit_pct, {True: "LIMITED (API overflow runs)", False: "not limited",
                                None: "unknown"}[hit], "live" if limited_now() else "absent"))
        return 0
    if a.clear_limited:
        try:
            os.remove(MARKER)
        except OSError:
            pass
        print("subscription limit marker cleared")
        return 0
    if a.mark_limited is not None:
        mark_limited(a.mark_limited or None)
        return 0
    if not (a.lane and a.model and a.task):
        ap.error("--lane, --model and --task are required")

    if a.when_subscription_limited:
        if a.lane != "continuity":
            sys.exit("--when-subscription-limited overflow is approved for the continuity lane only.")
        hit, text = over_threshold(a.limit_pct)
        if not (hit or limited_now() or (a.probe and probe_limited(find_claude(a.claude)))):
            print("subscription not limited (%s; threshold %.0f%%); nothing to do." % (text, a.limit_pct))
            return 0
        print("subscription limited (%s; threshold %.0f%%): running on API credits." % (text, a.limit_pct),
              file=sys.stderr)

    ok, code, msg = ledger.check(a.lane, a.est_usd, a.reserve)
    if not ok:
        print("ledger refuses: " + msg, file=sys.stderr)
        return code
    cap = round(min(a.max_usd, ledger.headroom(a.lane)), 2)
    model = ledger.model_id(a.model)
    prompt = build_prompt(a)
    claude = find_claude(a.claude)
    cmd = [claude, "-p", "--output-format", "json", "--model", model,
           "--permission-mode", PERMISSION_MODE, "--allowedTools", ALLOWED, "--disallowedTools", DENIED,
           "--max-budget-usd", "%.2f" % cap, "--no-session-persistence"]
    if a.dry_run:
        print(msg)
        print("cwd: %s\nmodel: %s  cap: $%.2f  permission-mode: %s" % (REPO, model, cap, PERMISSION_MODE))
        print("cmd: " + " ".join(cmd[:4] + ["..."]))
        print("key file: %s (%s)" % (ledger.KEY_FILE, "present" if ledger.key_present() else "MISSING"))
        print("prompt (stdin, %d chars):\n%s" % (len(prompt), prompt[:600]))
        return 0

    key = ledger.load_key()
    env = dict(os.environ)
    env.pop("ANTHROPIC_AUTH_TOKEN", None)
    env["ANTHROPIC_API_KEY"] = key  # child process only; never exported or logged
    try:
        p = subprocess.run(cmd, input=prompt, capture_output=True, text=True, encoding="utf-8",
                           env=env, cwd=REPO, timeout=3 * 3600)
    except subprocess.TimeoutExpired:
        print("claude run timed out after 3 h; cost unknown, not logged. Check the API console.", file=sys.stderr)
        return 1
    out, err = ledger.scrub(p.stdout or "", key), ledger.scrub(p.stderr or "", key)
    try:
        r = parse_result(out)
    except ValueError:
        print("could not parse claude JSON output (exit %d). stderr:\n%s\nstdout head:\n%s"
              % (p.returncode, err[-1500:], out[:1500]), file=sys.stderr)
        return p.returncode or 1

    u = r.get("usage") or {}
    inp, outp = u.get("input_tokens", 0), u.get("output_tokens", 0)
    cr, cw = u.get("cache_read_input_tokens", 0), u.get("cache_creation_input_tokens", 0)
    if isinstance(r.get("total_cost_usd"), (int, float)):
        cost, src = r["total_cost_usd"], "reported"
    else:
        cost, src = ledger.estimate_cost(model, inp, outp, cr, cw), "estimated"
    rec = ledger.record(a.lane, a.task, model, cost, inp, outp, cr, cw,
                        run_id=r.get("session_id") or None, source=src)
    print(r.get("result") or "")
    print("[api_run] %s: $%.4f (%s) in=%d out=%d cache r/w=%d/%d run=%s%s" % (
        a.lane, cost, src, inp, outp, cr, cw, rec["run_id"], "  ERROR" if r.get("is_error") else ""),
        file=sys.stderr)
    return 1 if r.get("is_error") or p.returncode else 0


if __name__ == "__main__":
    sys.exit(main())
