#!/usr/bin/env python3
"""Zero-token watcher: turns things worth waking up for into lines in ops/inbox.log.

Run every 10 minutes by the scheduled task "QuestForge ops watch" (install with --install-task),
or once by hand. It:
  - finds new GitHub issues titled "Shader Lab feedback: round N" (also Decisions sheets) and runs
    tools/shaders/review/fetch_feedback.py for Shader Lab rounds;
  - flags renderq trouble: C:\\qfb\\renderq\\STALLED, FOCUS-ALERT, or a runner whose heartbeat is stale;
  - notes when a submission finishes.
Each event is one line: "<iso time>\t<kind>\t<text>". The orchestrator reads only new lines
(`watch.py --unread`), so nobody has to sit and poll.

    py -3.10 -I tools/ops/watch.py              # one pass
    py -3.10 -I tools/ops/watch.py --unread     # print events since the last --unread, mark them read
    py -3.10 -I tools/ops/watch.py --install-task [--yes]
"""
import argparse, json, os, re, subprocess, sys, time, urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OPS = os.path.join(REPO, "ops")
INBOX = os.path.join(OPS, "inbox.log")
STATE = os.path.join(OPS, ".watch-state.json")
RQ = r"C:\qfb\renderq"
GH = "https://api.github.com/repos/MarionWhite/quest-forge/issues?state=all&per_page=20&sort=created&direction=desc"


def load_state():
    try:
        with open(STATE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_state(st):
    tmp = STATE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(st, f)
    os.replace(tmp, STATE)


def event(kind, text):
    with open(INBOX, "a", encoding="utf-8") as f:
        f.write(f"{time.strftime('%Y-%m-%dT%H:%M:%S')}\t{kind}\t{text}\n")


def check_issues(st):
    try:
        with urllib.request.urlopen(urllib.request.Request(GH, headers={"User-Agent": "qf-ops-watch"}), timeout=20) as r:
            issues = json.load(r)
    except Exception as e:
        return  # offline or rate-limited: try next pass
    seen = set(st.get("issues", []))
    first_run = not seen and "issues" not in st
    for it in issues:
        n = it["number"]
        if n in seen:
            continue
        seen.add(n)
        if first_run:
            continue  # don't replay history on the first pass
        title = it.get("title", "")
        m = re.search(r"Shader Lab feedback: round (\d+)", title)
        if m and int(m.group(1)) < 1000:
            rnd = int(m.group(1))
            subprocess.run([sys.executable, "-I", os.path.join(REPO, "tools/shaders/review/fetch_feedback.py"),
                            "--round", str(rnd)], cwd=REPO, capture_output=True)
            event("feedback", f"round {rnd} answered (issue #{n}) -> docs/design/shaders/feedback/r{rnd:03d}.json")
        else:
            event("issue", f"#{n} {title}")
    st["issues"] = sorted(seen)


def check_renderq(st):
    alerts = {"STALLED": "renderq STALLED (see C:\\qfb\\renderq\\status.json)",
              "FOCUS-ALERT": "renderq paused: a focus give-back failed"}
    for name, text in alerts.items():
        present = os.path.exists(os.path.join(RQ, name))
        if present and not st.get(name):
            event("alert", text)
        st[name] = present
    try:
        with open(os.path.join(RQ, "status.json"), encoding="utf-8") as f:
            s = json.load(f)
    except (OSError, ValueError):
        return
    beat = s.get("heartbeat") or s.get("updated_at") or 0
    if isinstance(beat, (int, float)) and beat and time.time() - beat > 1800 and not st.get("dead"):
        event("alert", "renderq runner heartbeat is over 30 min old")
        st["dead"] = True
    elif isinstance(beat, (int, float)) and time.time() - beat <= 1800:
        st["dead"] = False
    done = set(st.get("subs_done", []))
    try:
        for name in os.listdir(os.path.join(RQ, "done")):
            if name not in done:
                done.add(name)
                if "subs_done" in st:
                    event("renders", f"submission finished: {name}")
    except OSError:
        pass
    st["subs_done"] = sorted(done)


def unread():
    st = load_state()
    pos = st.get("read_pos", 0)
    try:
        with open(INBOX, encoding="utf-8") as f:
            f.seek(pos)
            out = f.read()
            st["read_pos"] = f.tell()
    except OSError:
        out = ""
    sys.stdout.write(out or "(no new events)\n")
    save_state(st)


def install_task(yes):
    vbs = os.path.join(OPS, "watch.vbs")
    py = sys.executable.replace("python.exe", "pythonw.exe")
    with open(vbs, "w", encoding="utf-8") as f:
        f.write('Set sh = CreateObject("WScript.Shell")\n'
                f'sh.Run """{py}"" -I ""{os.path.abspath(__file__)}""", 0, False\n')
    cmd = ["schtasks", "/Create", "/TN", "QuestForge ops watch", "/SC", "MINUTE", "/MO", "10", "/F",
           "/TR", f'wscript.exe //B //Nologo "{vbs}"']
    print(" ".join(cmd))
    if yes:
        subprocess.run(cmd)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--unread", action="store_true")
    ap.add_argument("--install-task", action="store_true")
    ap.add_argument("--yes", action="store_true")
    a = ap.parse_args()
    if a.unread:
        return unread()
    if a.install_task:
        return install_task(a.yes)
    st = load_state()
    check_issues(st)
    check_renderq(st)
    save_state(st)


if __name__ == "__main__":
    main()
