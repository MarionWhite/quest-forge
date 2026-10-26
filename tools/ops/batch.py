#!/usr/bin/env python3
"""Message Batches helper (50% off, results within 24 h) for bulk independent items.

    py -3.10 -I tools/ops/batch.py submit JOBS.json [--dry-run] [--max-tokens N] [--est-out-tokens N] [--reserve]
    py -3.10 -I tools/ops/batch.py status BATCH_ID
    py -3.10 -I tools/ops/batch.py fetch BATCH_ID OUT_DIR

JOBS.json is a list of objects:
    {"custom_id": "critic-r008-f03",          # 1-64 chars of [A-Za-z0-9_-]; results are keyed by it
     "model": "sonnet",                        # opus | sonnet | haiku (or a full model id)
     "system": "shared instructions...",       # optional; cached (cache_control) so jobs sharing it are cheap
     "user": "the item text",
     "images": ["C:/path/a.png"],              # optional; base64-encoded here, placed before the text
     "max_tokens": 4000}                       # optional (default 4000; thinking counts toward it)

Cost goes into ops/api-ledger.jsonl (lane "batch") at fetch time, from the usage the API reports,
priced at the batch rate (the API reports tokens, not dollars). Safe to run fetch twice.
The key is read only from ~/.qf/anthropic.key and handed to the SDK client directly.
"""
import argparse, base64, json, mimetypes, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ledger

ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
IMG_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif", ".webp": "image/webp"}


def client():
    try:
        import anthropic
    except ImportError:
        sys.exit("anthropic SDK missing: py -3.10 -m pip install anthropic")
    return anthropic.Anthropic(api_key=ledger.load_key())


def load_jobs(path):
    with open(path, "r", encoding="utf-8") as f:
        jobs = json.load(f)
    if not isinstance(jobs, list) or not jobs:
        sys.exit("JOBS.json must be a non-empty list")
    seen = set()
    for j in jobs:
        cid = j.get("custom_id", "")
        if not ID_RE.match(cid):
            sys.exit("bad custom_id %r (1-64 chars of A-Za-z0-9_-)" % cid)
        if cid in seen:
            sys.exit("duplicate custom_id %r" % cid)
        seen.add(cid)
        if not j.get("user") or not j.get("model"):
            sys.exit("job %s needs model and user" % cid)
        if ledger.model_id(j["model"]) not in ledger.PRICES:
            sys.exit("job %s: unknown model %r" % (cid, j["model"]))
    return jobs


def build_params(j, default_max):
    content = []
    for img in j.get("images", []):
        ext = os.path.splitext(img)[1].lower()
        if ext not in IMG_TYPES:
            sys.exit("job %s: unsupported image type %s" % (j["custom_id"], img))
        with open(img, "rb") as f:
            data = base64.standard_b64encode(f.read()).decode("ascii")
        content.append({"type": "image", "source": {"type": "base64", "media_type": IMG_TYPES[ext], "data": data}})
    content.append({"type": "text", "text": j["user"]})
    params = {"model": ledger.model_id(j["model"]), "max_tokens": int(j.get("max_tokens", default_max)),
              "messages": [{"role": "user", "content": content}]}
    if j.get("system"):
        params["system"] = [{"type": "text", "text": j["system"], "cache_control": {"type": "ephemeral"}}]
    return params


def estimate(params, est_out):
    chars = sum(len(b.get("text", "")) for m in params["messages"] for b in m["content"]) \
        + sum(len(b["text"]) for b in params.get("system", []))
    imgs = sum(1 for m in params["messages"] for b in m["content"] if b["type"] == "image")
    tin = chars / 3.5 + imgs * 1600
    return ledger.estimate_cost(params["model"], int(tin), min(est_out, params["max_tokens"]), batch=True)


def cmd_submit(a):
    jobs = load_jobs(a.jobs)
    params = [(j, build_params(j, a.max_tokens)) for j in jobs]
    est = round(sum(estimate(p, a.est_out_tokens) for _, p in params), 4)
    print("%d jobs, estimated batch cost ~$%.3f (assumes ~%d output tokens/job)" % (len(jobs), est, a.est_out_tokens))
    ok, code, msg = ledger.check("batch", est, a.reserve)
    print(msg, file=sys.stdout if ok else sys.stderr)
    if not ok:
        return code
    if a.dry_run:
        print("dry run: nothing submitted.")
        return 0
    from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
    from anthropic.types.messages.batch_create_params import Request
    reqs = [Request(custom_id=j["custom_id"], params=MessageCreateParamsNonStreaming(**p)) for j, p in params]
    b = client().messages.batches.create(requests=reqs)
    print("batch id: %s  status: %s" % (b.id, b.processing_status))
    print("next: batch.py status %s ; batch.py fetch %s OUT_DIR" % (b.id, b.id))
    return 0


def cmd_status(a):
    b = client().messages.batches.retrieve(a.id)
    c = b.request_counts
    print("%s: %s  processing=%d succeeded=%d errored=%d canceled=%d expired=%d" % (
        b.id, b.processing_status, c.processing, c.succeeded, c.errored, c.canceled, c.expired))
    return 0


def cmd_fetch(a):
    cl = client()
    b = cl.messages.batches.retrieve(a.id)
    if b.processing_status != "ended":
        print("batch %s is still %s; try later." % (a.id, b.processing_status), file=sys.stderr)
        return 3
    os.makedirs(a.out_dir, exist_ok=True)
    results, total, logged = {}, 0.0, 0
    for r in cl.messages.batches.results(a.id):  # any order: key by custom_id
        cid, kind = r.custom_id, r.result.type
        entry = {"status": kind}
        if kind == "succeeded":
            m = r.result.message
            text = "".join(bl.text for bl in m.content if bl.type == "text")
            u = m.usage
            tok = dict(input_tokens=u.input_tokens or 0, output_tokens=u.output_tokens or 0,
                       cache_read=getattr(u, "cache_read_input_tokens", 0) or 0,
                       cache_write=getattr(u, "cache_creation_input_tokens", 0) or 0)
            cost = ledger.estimate_cost(m.model, tok["input_tokens"], tok["output_tokens"],
                                        tok["cache_read"], tok["cache_write"], batch=True)
            entry.update(stop_reason=m.stop_reason, cost_usd=cost, **tok)
            with open(os.path.join(a.out_dir, cid + ".txt"), "w", encoding="utf-8", newline="\n") as f:
                f.write(text)
            if not ledger.has_record(a.id, cid):
                ledger.record("batch", cid, m.model, cost, tok["input_tokens"], tok["output_tokens"],
                              tok["cache_read"], tok["cache_write"], run_id=a.id, source="usage*batch-rate")
                logged += 1
            total += cost
        elif kind == "errored":
            entry["error"] = getattr(r.result.error, "type", "error")
        results[cid] = entry
    with open(os.path.join(a.out_dir, "results.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, indent=1)
    bad = {k: v["status"] for k, v in results.items() if v["status"] != "succeeded"}
    print("%d results in %s, cost $%.4f (%d newly logged to ledger, lane batch)" % (len(results), a.out_dir, total, logged))
    if bad:
        print("not succeeded: %s" % json.dumps(bad), file=sys.stderr)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("submit"); p.add_argument("jobs"); p.add_argument("--dry-run", action="store_true")
    p.add_argument("--max-tokens", type=int, default=4000); p.add_argument("--est-out-tokens", type=int, default=1000)
    p.add_argument("--reserve", action="store_true"); p.set_defaults(fn=cmd_submit)
    p = sub.add_parser("status"); p.add_argument("id"); p.set_defaults(fn=cmd_status)
    p = sub.add_parser("fetch"); p.add_argument("id"); p.add_argument("out_dir"); p.set_defaults(fn=cmd_fetch)
    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
