#!/usr/bin/env python3
"""Run the friends' server under supervision: crash restart, hang detection,
hourly backups, a daily restart and a graceful stop.

The builder (build_play_server.py) installs this file into the server folder
next to start-supervised.bat, which is the normal way to run it:

    start-supervised.bat            (or: py -3 -I supervisor.py)

It owns the Java process and its stdin, so it is also the server console: type
any server command and it is passed through. Lines starting with "!" are for the
supervisor itself:

    !backup    take a backup now          !restart   save, stop and start again
    !dump      thread dump into logs/     !status    state, players, next jobs
    !stop      stop the server and exit   (plain `stop` and Ctrl+C do the same)

The same lines can be dropped into the file `supervisor.inbox` in the server
folder (one per line); the supervisor runs and deletes it within a second. A
file named `stop.flag` stops everything. Both work from a remote shell or a
synced folder, where there is no console to type into.

WHY EACH PART EXISTS (docs/design/server-readiness.md, gap 1):

- Restart on crash. Two Legends crashes are accepted as unfixable, so the
  server will die sooner or later; without this it stays down until the host
  notices. Three crashes in 15 minutes stops the loop: a crash on a bad chunk
  needs a person, not a fourth restart.
- Hang detection. 1.7.10 has no tick watchdog (max-tick-time came in 1.8). The
  supervisor sends `list` every minute. Console commands run on the main
  thread, so an answer proves the server is still ticking. No answer within 90 s
  means the tick is stuck: take a jstack thread dump, kill, restart.
- Backups. save-off, save-all, wait for "Saved the world", then wait until no
  region file has changed for 10 s (1.7.10 drains chunk writes on a background
  IO thread after the message). Copy the world, then save-on in a `finally`.
  The zip is written from that copy afterwards, so saving is off only for as
  long as a plain file copy takes.
- Daily restart. Nobody has measured how the heap grows over days with players.
  A restart at a quiet hour costs nothing and caps it.
- Graceful stop. Closing the console window kills Java within seconds, which is
  not enough to save ~30 dimensions. Java runs here in its own process group
  and hidden console, so Ctrl+C or closing this window reaches only the
  supervisor, which sends `stop` and waits for the save.

WINDOWS NOTES. No mkfifo and no pkill: a Windows JVM cannot read an MSYS fifo,
and pkill does not reach it. Java gets a plain pipe and is killed by its PID.
Commands go to the pipe as bytes with no BOM; PowerShell's piping adds one and
the server answers "Unknown command".

Configuration is `supervisor.json` next to this file (the builder writes the
defaults and keeps your edits across rebuilds). The Discord webhook URL goes
there or in the environment variable QF_DISCORD_WEBHOOK, never in the repo.
Standard library only; Python 3.8 or newer.
"""
import argparse, collections, datetime, json, os, queue, re, shutil, signal, socket
import subprocess, sys, threading, time, traceback, urllib.request, zipfile

IS_WIN = os.name == "nt"

DEFAULTS = {
    # The Java command. Empty means: read it from start.bat (or start.sh), so
    # the flags the builder chose are the ones that run.
    "command": [],
    "level_name": "",                    # empty: read from server.properties
    "boot_timeout_s": 900,               # no "Done (" by then: treat as a hang
    "boot_stall_s": 300,                 # no console output at all for this long while booting
    "probe_interval_s": 60,              # how often `list` is sent
    "probe_timeout_s": 90,               # no answer by then: hung
    "stop_timeout_s": 300,               # `stop` that prints nothing for this long is hung
    "crash_limit": 3,                    # this many crashes ...
    "crash_window_min": 15,              # ... in this many minutes stops the loop
    "backoff_s": [10, 30, 60, 120],      # wait before restart n (last value repeats)
    "backup_dir": "backups",
    "backup_interval_min": 60,
    "backup_only_when_active": True,     # skip an hourly backup if nobody was online since the last
    "backup_format": "zip",              # "zip" or "dir" (a plain copy; faster, bigger)
    "keep_hourly": 24,
    "keep_daily": 7,
    "save_timeout_s": 600,               # save-all must report "Saved the world" by then
    "quiet_s": 10,                       # region files unchanged this long before copying
    "restart_at": "05:00",               # daily restart, local time; "" turns it off
    "restart_warnings_min": [10, 5, 1],
    "jstack": "",                        # empty: look for a jstack matching the java
    "discord_webhook": "",               # or env QF_DISCORD_WEBHOOK
    "alert_on_join": False,
}

DONE_RE = re.compile(r"\]: Done \(\d")
LIST_RE = re.compile(r"There are (\d+)/(\d+) players online")
JOIN_RE = re.compile(r"\]: (\S+) joined the game")
SAVED_RE = re.compile(r"Saved the world|Saving failed")
SAVE_OFF_RE = re.compile(r"Turned off world auto-saving|Saving is already turned off")
# With removeErroringEntities / removeErroringTileEntities on (config/forge.cfg),
# Forge logs a full crash report and deletes the entity or machine instead of
# crashing. The server keeps running; the only way back is a backup.
ENTITY_REMOVED_RE = re.compile(r"---- Minecraft Crash Report ----")


def now():
    return time.time()


def stamp(t=None):
    return datetime.datetime.fromtimestamp(t or now()).strftime("%Y%m%d-%H%M%S")


# --------------------------------------------------------------------------
# small helpers

def pid_alive(pid):
    """os.kill(pid, 0) is not a probe on Windows: 0 is CTRL_C_EVENT."""
    if not pid:
        return False
    if IS_WIN:
        import ctypes
        k32 = ctypes.windll.kernel32
        h = k32.OpenProcess(0x1000, False, int(pid))  # PROCESS_QUERY_LIMITED_INFORMATION
        if not h:
            return False
        code = ctypes.c_ulong()
        ok = k32.GetExitCodeProcess(h, ctypes.byref(code))
        k32.CloseHandle(h)
        return bool(ok) and code.value == 259  # STILL_ACTIVE
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def port_in_use(port):
    s = socket.socket()
    s.settimeout(1)
    try:
        return s.connect_ex(("127.0.0.1", port)) == 0
    finally:
        s.close()


def read_properties(path):
    props = {}
    if os.path.exists(path):
        with open(path, encoding="latin-1") as fh:
            for line in fh:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    props[k.strip()] = v.strip()
    return props


def parse_start_script(server_dir):
    """The java command line from start.bat (^ continuations) or start.sh."""
    bat = os.path.join(server_dir, "start.bat")
    sh = os.path.join(server_dir, "start.sh")
    if os.path.exists(bat):
        text = open(bat, encoding="latin-1").read()
        text = re.sub(r"\^\s*\r?\n", " ", text)
    elif os.path.exists(sh):
        text = open(sh, encoding="latin-1").read()
        text = re.sub(r"\\\s*\r?\n", " ", text)
    else:
        raise SystemExit("no start.bat or start.sh in %s, and no \"command\" in supervisor.json"
                         % server_dir)
    for line in text.splitlines():
        if " -jar " in line:
            toks = [t.strip('"') for t in re.findall(r'"[^"]*"|\S+', line.strip())]
            if toks and toks[0] == "exec":
                toks = toks[1:]
            return toks
    raise SystemExit("could not find the java line (with -jar) in the start script")


def java_major(java):
    """8 or 25 (or whatever), from the `release` file of the java's home; 8 when unknown."""
    if not java or not os.path.isabs(java):
        return 8
    try:
        with open(os.path.join(os.path.dirname(os.path.dirname(java)), "release")) as fh:
            m = re.search(r'JAVA_VERSION="(?:1\.)?(\d+)', fh.read())
        return int(m.group(1)) if m else 8
    except OSError:
        return 8


def find_jstack(configured, java):
    """A jstack that can attach to the server's JVM: one from the same major
    version. The java's own bin/ comes first (a JDK, such as the Temurin 25 the
    --java25 build runs on, has it there); a JRE has none, so for Java 8 a
    separate JDK 8 is looked for."""
    if configured:
        return configured if os.path.exists(configured) else None
    exe = "jstack.exe" if IS_WIN else "jstack"
    cands = []
    if java and os.path.isabs(java):
        cands.append(os.path.join(os.path.dirname(java), exe))
    jh = os.environ.get("JAVA_HOME")
    if jh and java_major(os.path.join(jh, "bin", "java")) == java_major(java):
        cands.append(os.path.join(jh, "bin", exe))
    if IS_WIN:
        import glob
        if java_major(java) == 8:
            pats = (r"C:\Program Files\Eclipse Adoptium\jdk-8*\bin\jstack.exe",
                    r"C:\Program Files\Java\jdk1.8*\bin\jstack.exe",
                    r"C:\Program Files\Zulu\zulu-8*\bin\jstack.exe",
                    r"C:\Program Files\Amazon Corretto\jdk1.8*\bin\jstack.exe")
        else:
            v = java_major(java)
            pats = (r"C:\Program Files\Eclipse Adoptium\jdk-%d*\bin\jstack.exe" % v,
                    r"C:\Program Files\Java\jdk-%d*\bin\jstack.exe" % v)
        for pat in pats:
            cands += sorted(glob.glob(pat), reverse=True)
    for c in cands:
        if os.path.exists(c):
            return c
    return shutil.which("jstack")


# --------------------------------------------------------------------------
# one run of the server JVM

class Server:
    def __init__(self, sup, cmd, cwd):
        self.sup, self.cmd, self.cwd = sup, cmd, cwd
        self.proc = None
        self.lines = collections.deque(maxlen=5000)   # (seq, time, text)
        self.seq = 0
        self.cond = threading.Condition()
        self.last_output = now()
        self.started_at = None
        self.done = False
        self.stop_sent = False
        self.reader = None

    def start(self):
        flags = 0
        if IS_WIN:
            # Own process group: Ctrl+C in the supervisor's window does not reach
            # Java. Own hidden console: closing that window does not kill it
            # mid-save either.
            flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
        self.proc = subprocess.Popen(self.cmd, cwd=self.cwd, stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                     creationflags=flags, bufsize=0)
        self.started_at = now()
        self.last_output = now()
        self.reader = threading.Thread(target=self._read, daemon=True)
        self.reader.start()
        return self.proc.pid

    def _read(self):
        # This thread must never die. If it stops draining the pipe, Java blocks
        # on its next console write and the server really hangs. That happened
        # in testing, on a Food Plus line with a section sign, when echoing it
        # to a cp1252 console raised UnicodeEncodeError.
        for raw in iter(self.proc.stdout.readline, b""):
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:       # Java writes the platform charset (cp1252)
                text = raw.decode("cp1252", "replace")
            text = text.rstrip("\r\n")
            with self.cond:
                self.seq += 1
                self.lines.append((self.seq, now(), text))
                self.last_output = now()
                if DONE_RE.search(text):
                    self.done = True
                self.cond.notify_all()
            try:
                self.sup.on_line(text)
            except Exception:
                pass
        with self.cond:
            self.cond.notify_all()

    @property
    def pid(self):
        return self.proc.pid if self.proc else None

    def alive(self):
        return self.proc is not None and self.proc.poll() is None

    def mark(self):
        with self.cond:
            return self.seq

    def send(self, line):
        if not self.alive():
            return False
        try:
            self.proc.stdin.write((line + "\n").encode("utf-8"))
            self.proc.stdin.flush()
            return True
        except OSError:
            return False

    def wait_for(self, regex, timeout, after):
        """First line matching regex with seq > after, or None on timeout/exit."""
        end = now() + timeout
        with self.cond:
            while True:
                for seq, _, text in self.lines:
                    if seq > after:
                        m = regex.search(text)
                        if m:
                            return m
                after = self.seq
                left = end - now()
                if left <= 0 or not self.alive():
                    return None
                self.cond.wait(min(left, 1.0))

    def send_stop(self):
        if not self.stop_sent:
            self.stop_sent = self.send("stop")

    def kill(self):
        if self.alive():
            self.proc.kill()
        if self.proc:
            try:
                self.proc.wait(30)
            except subprocess.TimeoutExpired:
                pass


# --------------------------------------------------------------------------

class Supervisor:
    def __init__(self, server_dir, cfg):
        self.dir = server_dir
        self.cfg = cfg
        self.cmd = cfg["command"] or parse_start_script(server_dir)
        props = read_properties(os.path.join(server_dir, "server.properties"))
        self.port = int(props.get("server-port", "25565") or 25565)
        self.level = cfg["level_name"] or props.get("level-name", "world") or "world"
        self.max_players = props.get("max-players", "?")
        self.jstack = find_jstack(cfg["jstack"], self.cmd[0] if self.cmd else None)
        self.webhook = os.environ.get("QF_DISCORD_WEBHOOK") or cfg["discord_webhook"]
        self.logs = os.path.join(server_dir, "logs")
        os.makedirs(self.logs, exist_ok=True)
        self.logfh = open(os.path.join(self.logs, "supervisor.log"), "a", encoding="utf-8")
        self.requests = queue.Queue()
        self.stop_requested = threading.Event()
        self.server = None
        self.crashes = collections.deque()
        self.players = 0
        self.active_since_backup = False
        self.backup_thread = None
        self.crash_report_seen = None
        self.last_outcome = None
        self.pidfile = os.path.join(server_dir, "supervisor.pid")

    # ---- logging and alerts ------------------------------------------------
    def log(self, msg):
        line = "%s [supervisor] %s" % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), msg)
        print(line, flush=True)
        try:
            self.logfh.write(line + "\n")
            self.logfh.flush()
        except (OSError, ValueError):
            pass

    def alert(self, msg):
        self.log("ALERT: " + msg)
        if not self.webhook:
            return
        body = json.dumps({"content": ("**Quest Forge server:** " + msg)[:1900]}).encode()

        def post():
            try:
                req = urllib.request.Request(self.webhook, data=body, headers={
                    "Content-Type": "application/json",
                    # Discord refuses urllib's default agent.
                    "User-Agent": "QuestForgeSupervisor/1.0"})
                urllib.request.urlopen(req, timeout=10).read()
            except Exception as e:  # never log the URL: it is the secret
                self.log("webhook post failed: %s" % type(e).__name__)
        threading.Thread(target=post, daemon=True).start()

    def on_line(self, text):
        print(text, flush=True)
        m = LIST_RE.search(text)
        if m:
            self.players = int(m.group(1))
            if self.players:
                self.active_since_backup = True
        m = JOIN_RE.search(text)
        if m:
            self.active_since_backup = True
            if self.cfg["alert_on_join"]:
                self.alert("%s joined" % m.group(1))
        if ENTITY_REMOVED_RE.search(text) and self.server and self.server.done:
            # A real crash prints the same header and then exits; the main loop
            # alerts only if the server is still up a few seconds later.
            self.crash_report_seen = now()

    def write_pidfile(self):
        try:
            with open(self.pidfile, "w") as fh:
                json.dump({"supervisor_pid": os.getpid(),
                           "java_pid": self.server.pid if self.server else None,
                           "since": stamp()}, fh)
        except OSError:
            pass

    # ---- requests ----------------------------------------------------------
    def request(self, line):
        self.requests.put(line)

    def console_thread(self):
        if sys.stdin is None:
            return
        try:
            for line in sys.stdin:
                line = line.strip()
                if line:
                    self.request(line)
        except (OSError, ValueError, EOFError):
            pass

    def poll_files(self):
        inbox = os.path.join(self.dir, "supervisor.inbox")
        if os.path.exists(inbox):
            try:
                with open(inbox, encoding="utf-8-sig") as fh:   # tolerate a BOM here
                    lines = [l.strip() for l in fh if l.strip()]
                os.remove(inbox)
            except OSError:
                lines = []
            for l in lines:
                self.log("inbox: %s" % l)
                self.request(l)
        flag = os.path.join(self.dir, "stop.flag")
        if os.path.exists(flag):
            try:
                os.remove(flag)
            except OSError:
                pass
            self.log("stop.flag found")
            self.request("!stop")

    def on_signal(self, signum, frame):
        if self.stop_requested.is_set():
            self.log("already stopping; waiting for the world to save (do not close this window)")
            return
        self.log("signal %s: stopping the server gracefully" % signum)
        self.stop_requested.set()
        # Send `stop` right now, not on the next loop pass: if this is the
        # console window closing, Windows ends this process within seconds, and
        # Java (in its own hidden console) then finishes the save on its own.
        if self.server and self.server.alive():
            self.server.send_stop()

    # ---- main loop -----------------------------------------------------------
    def run(self):
        self.log("starting; dir=%s port=%d level=%s" % (self.dir, self.port, self.level))
        self.log("java: %s" % " ".join(self.cmd))
        self.log("jstack: %s" % (self.jstack or "none found (hang dumps disabled; install a "
                                                 "JDK of the server's Java version)"))
        self.log("discord alerts: %s" % ("on" if self.webhook else "off"))
        if os.path.exists(self.pidfile):
            try:
                other = json.load(open(self.pidfile)).get("supervisor_pid")
            except (OSError, ValueError):
                other = None
            if other and other != os.getpid() and pid_alive(other):
                raise SystemExit("another supervisor (pid %s) is running this server" % other)
        self.write_pidfile()
        # Half-made backups from a supervisor that was killed mid-archive.
        root = os.path.join(self.dir, self.cfg["backup_dir"])
        if os.path.isdir(root):
            for n in os.listdir(root):
                if n.startswith(".staging-"):
                    shutil.rmtree(os.path.join(root, n), ignore_errors=True)
            for sub in ("hourly", "daily"):
                d = os.path.join(root, sub)
                for n in os.listdir(d) if os.path.isdir(d) else []:
                    if n.endswith(".partial"):
                        os.remove(os.path.join(d, n))
        threading.Thread(target=self.console_thread, daemon=True).start()
        try:
            self.loop()
        finally:
            if self.backup_thread:
                self.log("waiting for the backup archive to finish")
                self.backup_thread.join()
            try:
                os.remove(self.pidfile)
            except OSError:
                pass
            self.log("supervisor exited")

    def loop(self):
        while not self.stop_requested.is_set():
            outcome = self.last_outcome = self.run_once()
            if outcome in ("stopped", "fatal"):
                return
            if outcome == "restart":
                continue
            # a crash or a hang
            t = now()
            self.crashes.append(t)
            win = self.cfg["crash_window_min"] * 60
            while self.crashes and self.crashes[0] < t - win:
                self.crashes.popleft()
            if len(self.crashes) >= self.cfg["crash_limit"]:
                self.alert("%d crashes in %d minutes: NOT restarting again. A person needs "
                           "to look at crash-reports/ and logs/." % (len(self.crashes),
                                                                     self.cfg["crash_window_min"]))
                return
            backoff = self.cfg["backoff_s"]
            wait = backoff[min(len(self.crashes) - 1, len(backoff) - 1)]
            self.log("restarting in %d s (crash %d of %d allowed in %d min)"
                     % (wait, len(self.crashes), self.cfg["crash_limit"],
                        self.cfg["crash_window_min"]))
            end = now() + wait
            while now() < end and not self.stop_requested.is_set():
                self.drain_requests_while_down()
                time.sleep(0.5)

    def drain_requests_while_down(self):
        self.poll_files()
        try:
            while True:
                line = self.requests.get_nowait()
                if line.lower() in ("!stop", "stop"):
                    self.stop_requested.set()
                else:
                    self.log("server is down; ignored: %s" % line)
        except queue.Empty:
            pass

    def run_once(self):
        """Start the JVM and supervise it until it exits. Returns 'stopped'
        (asked to stop), 'restart' (planned), 'crash', 'hang' or 'fatal'."""
        if port_in_use(self.port):
            self.alert("port %d is already in use: another server (or an orphaned Java from "
                       "an earlier run) holds it. Not starting." % self.port)
            return "crash"
        self.server = srv = Server(self, self.cmd, self.dir)
        pid = srv.start()
        self.write_pidfile()
        self.log("java started, pid %d" % pid)

        # --- boot ----
        while not srv.done:
            if not srv.alive():
                return self.after_exit(srv, booting=True)
            if self.stop_requested.is_set():
                # `stop` is queued on stdin and runs once the server is up.
                return self.stop_server(srv)
            self.poll_files()
            deferred = []
            try:
                while True:
                    line = self.requests.get_nowait()
                    if line.lower() in ("stop", "!stop"):
                        self.stop_requested.set()
                    else:
                        deferred.append(line)     # run once the server is up
            except queue.Empty:
                pass
            for line in deferred:
                self.requests.put(line)
            if self.stop_requested.is_set():
                continue
            idle = now() - srv.last_output
            if now() - srv.started_at > self.cfg["boot_timeout_s"] or idle > self.cfg["boot_stall_s"]:
                return self.hang(srv, "boot made no progress (%.0f s since the last console line)" % idle)
            time.sleep(0.5)
        self.log("server is up (boot %.0f s)" % (now() - srv.started_at))
        if self.last_outcome in ("crash", "hang"):
            self.alert("server is back up after a %s" % self.last_outcome)

        next_probe = now() + self.cfg["probe_interval_s"]
        next_backup = now() + self.cfg["backup_interval_min"] * 60
        restart_due = self.next_restart_time()
        warned = set()

        while True:
            if not srv.alive():
                return self.after_exit(srv)
            if self.stop_requested.is_set():
                return self.stop_server(srv)
            self.poll_files()
            if self.crash_report_seen and now() - self.crash_report_seen > 10:
                self.crash_report_seen = None
                self.alert("Forge logged a crash report and kept running: an entity or tile "
                           "entity threw and was probably REMOVED (removeErroring* in "
                           "config/forge.cfg). See logs/fml-server-latest.log; the backups "
                           "from before it still have it.")

            # requests from the console or the inbox
            try:
                while True:
                    line = self.requests.get_nowait()
                    r = self.handle(srv, line)
                    if r:
                        return r
            except queue.Empty:
                pass

            # hang probe
            if now() >= next_probe:
                mark = srv.mark()
                srv.send("list")
                if not srv.wait_for(LIST_RE, self.cfg["probe_timeout_s"], mark):
                    if not srv.alive():
                        return self.after_exit(srv)
                    if self.stop_requested.is_set():
                        return self.stop_server(srv)
                    return self.hang(srv, "no answer to `list` in %d s: the main thread is stuck"
                                     % self.cfg["probe_timeout_s"])
                next_probe = now() + self.cfg["probe_interval_s"]

            # hourly backup
            if now() >= next_backup:
                if self.active_since_backup or not self.cfg["backup_only_when_active"]:
                    r = self.backup(srv, "hourly")
                    if r:
                        return r
                else:
                    self.log("hourly backup skipped: nobody online since the last one")
                next_backup = now() + self.cfg["backup_interval_min"] * 60

            # daily restart
            if restart_due:
                left = restart_due - now()
                for w in self.cfg["restart_warnings_min"]:
                    if left <= w * 60 and w not in warned and self.players > 0:
                        warned.add(w)
                        srv.send("say Daily restart in %d minute%s. It takes a couple of minutes."
                                 % (w, "" if w == 1 else "s"))
                if left <= 0:
                    srv.send("say Restarting now.")
                    self.log("daily restart")
                    r = self.backup(srv, "pre-restart")
                    if r:
                        return r
                    r = self.stop_server(srv)
                    return "restart" if r == "stopped" else r
            time.sleep(0.5)

    def handle(self, srv, line):
        cmd = line.lower()
        if cmd in ("stop", "!stop"):
            self.stop_requested.set()
            return self.stop_server(srv)
        if cmd == "!restart":
            srv.send("say Server restarting now (requested by the host).")
            r = self.stop_server(srv)
            return "restart" if r == "stopped" else r
        if cmd == "!backup":
            return self.backup(srv, "manual")
        if cmd == "!dump":
            self.thread_dump(srv, "requested")
            return None
        if cmd == "!status":
            self.log("pid %s, up %.0f min, %d players (last `list`), crashes in window %d, "
                     "next daily restart %s" % (
                         srv.pid, (now() - srv.started_at) / 60, self.players, len(self.crashes),
                         datetime.datetime.fromtimestamp(self.next_restart_time()).strftime(
                             "%Y-%m-%d %H:%M") if self.next_restart_time() else "off"))
            return None
        if cmd.startswith("!"):
            self.log("unknown supervisor command %s (try !backup !restart !dump !status !stop)" % line)
            return None
        srv.send(line)
        return None

    def next_restart_time(self):
        at = self.cfg["restart_at"]
        if not at:
            return None
        h, m = (int(x) for x in at.split(":"))
        n = datetime.datetime.now()
        t = n.replace(hour=h, minute=m, second=0, microsecond=0)
        if t <= n + datetime.timedelta(minutes=1):
            t += datetime.timedelta(days=1)
        # A server started at 04:58 would restart two minutes later; skip to tomorrow
        # if less than an hour of uptime would come before it.
        if (t - n).total_seconds() < 3600:
            t += datetime.timedelta(days=1)
        return t.timestamp()

    # ---- exits ----------------------------------------------------------------
    def after_exit(self, srv, booting=False):
        code = srv.proc.wait()
        if self.stop_requested.is_set():
            self.log("java exited (code %s) after a stop request" % code)
            return "stopped"
        report = self.newest_crash_report(srv.started_at)
        self.alert("server %s (exit code %s)%s" % (
            "died while booting" if booting else "CRASHED", code,
            "; crash report %s" % report if report else "; no crash report written"))
        return "crash"

    def newest_crash_report(self, since):
        d = os.path.join(self.dir, "crash-reports")
        if not os.path.isdir(d):
            return None
        files = [os.path.join(d, f) for f in os.listdir(d)]
        files = [f for f in files if os.path.getmtime(f) >= since - 1]
        if not files:
            return None
        f = max(files, key=os.path.getmtime)
        desc = ""
        try:
            for line in open(f, encoding="utf-8", errors="replace"):
                if line.startswith("Description:"):
                    desc = " (" + line.strip() + ")"
                    break
        except OSError:
            pass
        return os.path.basename(f) + desc

    def thread_dump(self, srv, why):
        if not self.jstack:
            self.log("no jstack; cannot take a thread dump")
            return None
        path = os.path.join(self.logs, "threaddump-%s.txt" % stamp())
        try:
            res = subprocess.run([self.jstack, "-l", str(srv.pid)], stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT, timeout=60)
            with open(path, "wb") as fh:
                fh.write(("# %s, pid %s\n" % (why, srv.pid)).encode())
                fh.write(res.stdout)
            self.log("thread dump (%s, jstack exit %d, %d bytes) -> %s"
                     % (why, res.returncode, len(res.stdout), path))
            return path
        except (subprocess.TimeoutExpired, OSError) as e:
            self.log("jstack failed: %s" % e)
            return None

    def hang(self, srv, why):
        self.alert("server HUNG: %s. Taking a thread dump, then killing pid %s." % (why, srv.pid))
        self.thread_dump(srv, "hang: " + why)
        srv.kill()
        self.log("killed hung server")
        return "hang"

    def stop_server(self, srv):
        """Send `stop` and wait for the exit. A stop that keeps printing is
        still saving; one that goes silent for stop_timeout_s is hung."""
        if self.backup_thread:
            self.backup_thread.join()
        if srv.alive() and not srv.stop_sent:
            self.log("sending stop")
            srv.send_stop()
        sent = now()
        while srv.alive():
            if now() - max(sent, srv.last_output) > self.cfg["stop_timeout_s"]:
                self.alert("`stop` printed nothing for %d s; killing pid %s (the world may lose "
                           "the last minutes)" % (self.cfg["stop_timeout_s"], srv.pid))
                self.thread_dump(srv, "stop timed out")
                srv.kill()
                break
            time.sleep(0.5)
        code = srv.proc.wait()
        self.log("java exited (code %s)" % code)
        return "stopped"

    # ---- backups ------------------------------------------------------------------
    def wait_quiet(self, world):
        """Until no region file has changed for quiet_s (capped at 2 min)."""
        end = now() + 120
        last, stable_since = None, now()
        while now() < end:
            newest = 0
            for root, _, files in os.walk(world):
                for f in files:
                    if f.endswith((".mca", ".mcr", ".dat")):
                        try:
                            newest = max(newest, os.path.getmtime(os.path.join(root, f)))
                        except OSError:
                            pass
            if newest != last:
                last, stable_since = newest, now()
            if now() - stable_since >= self.cfg["quiet_s"] and now() - newest >= self.cfg["quiet_s"]:
                return True
            time.sleep(1)
        return False

    def backup(self, srv, kind):
        """Returns None on success or failure that left the server healthy, or
        an outcome for run_once when the server hung or died during it."""
        if self.backup_thread and self.backup_thread.is_alive():
            self.log("previous backup still archiving; waiting for it")
            self.backup_thread.join()
        world = os.path.join(self.dir, self.level)
        if not os.path.isdir(world):
            self.log("backup skipped: no %s/ yet" % self.level)
            return None
        root = os.path.join(self.dir, self.cfg["backup_dir"])
        ts = stamp()
        staging = os.path.join(root, ".staging-" + ts)
        t0 = now()
        self.log("backup (%s) starting" % kind)
        mark = srv.mark()
        srv.send("save-off")
        if not srv.wait_for(SAVE_OFF_RE, 60, mark):
            return self.after_exit(srv) if not srv.alive() else self.hang(srv, "no answer to save-off")
        try:
            mark = srv.mark()
            srv.send("save-all")
            m = srv.wait_for(SAVED_RE, self.cfg["save_timeout_s"], mark)
            if not m:
                if not srv.alive():
                    return self.after_exit(srv)
                return self.hang(srv, "save-all did not finish in %d s" % self.cfg["save_timeout_s"])
            if "failed" in m.group(0):
                self.alert("backup aborted: the server reported `Saving failed`")
                return None
            t_saved = now()
            if not self.wait_quiet(world):
                self.log("region files kept changing for 2 min; copying anyway")
            t_quiet = now()
            errors = []
            try:
                os.makedirs(staging)
                shutil.copytree(world, os.path.join(staging, self.level),
                                ignore=shutil.ignore_patterns("session.lock"))
                # What the world needs besides itself: the player lists, and the
                # jar and config manifest it is only valid with.
                for name in ("server.properties", "ops.json", "whitelist.json",
                             "banned-players.json", "banned-ips.json", "usercache.json",
                             "BUILT-FROM.txt", "MANIFEST.sha256"):
                    p = os.path.join(self.dir, name)
                    if os.path.exists(p):
                        shutil.copy2(p, staging)
            except shutil.Error as e:
                errors = e.args[0]
            except OSError as e:     # disk full, permissions: the server must stay up
                self.alert("backup FAILED while copying: %s" % e)
                shutil.rmtree(staging, ignore_errors=True)
                return None
            t_copied = now()
        finally:
            srv.send("save-on")
        self.log("backup (%s): saved in %.1f s, files quiet after %.1f s, copied in %.1f s; "
                 "saving back on after %.1f s" % (kind, t_saved - t0, t_quiet - t_saved,
                                                  t_copied - t_quiet, now() - t0))
        if errors:
            self.alert("backup %s copied with %d file errors (first: %s)" % (ts, len(errors),
                                                                            errors[0]))
        self.active_since_backup = self.players > 0
        self.backup_thread = threading.Thread(target=self.finish_backup,
                                              args=(root, staging, ts, kind), daemon=True)
        self.backup_thread.start()
        return None

    def finish_backup(self, root, staging, ts, kind):
        try:
            hourly = os.path.join(root, "hourly")
            daily = os.path.join(root, "daily")
            os.makedirs(hourly, exist_ok=True)
            os.makedirs(daily, exist_ok=True)
            name = "%s-%s" % (self.level, ts)
            if self.cfg["backup_format"] == "zip":
                final = os.path.join(hourly, name + ".zip")
                tmp = final + ".partial"
                with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED, compresslevel=1,
                                     allowZip64=True) as z:
                    for r, _, files in os.walk(staging):
                        for f in files:
                            full = os.path.join(r, f)
                            z.write(full, os.path.relpath(full, staging))
                os.replace(tmp, final)
                shutil.rmtree(staging)
            else:
                final = os.path.join(hourly, name)
                os.replace(staging, final)
            size = (os.path.getsize(final) if os.path.isfile(final) else
                    sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(final) for f in fs))
            self.log("backup (%s) done: %s (%.1f MB)" % (kind, final, size / 1e6))
            # The first backup of each day is also kept as that day's daily.
            day = ts[:8]
            if not any(n.startswith("%s-%s" % (self.level, day)) for n in os.listdir(daily)):
                dst = os.path.join(daily, os.path.basename(final))
                if os.path.isfile(final):
                    try:
                        os.link(final, dst)         # same disk: no second copy
                    except OSError:
                        shutil.copy2(final, dst)
                else:
                    shutil.copytree(final, dst)
                self.log("kept as the daily backup for %s" % day)
            self.rotate(hourly, self.cfg["keep_hourly"])
            self.rotate(daily, self.cfg["keep_daily"])
            free = shutil.disk_usage(root).free
            if free < 3 * size:
                self.alert("backup disk has %.1f GB free, under three backups' worth" % (free / 1e9))
        except Exception:
            self.alert("backup archiving failed: %s" % traceback.format_exc().splitlines()[-1])
            self.log(traceback.format_exc())

    def rotate(self, d, keep):
        entries = sorted(n for n in os.listdir(d)
                         if n.startswith(self.level + "-") and not n.endswith(".partial"))
        for n in entries[:-keep] if keep > 0 else []:
            p = os.path.join(d, n)
            shutil.rmtree(p) if os.path.isdir(p) else os.remove(p)
            self.log("rotated out %s" % p)


def load_config(server_dir, path):
    cfg = dict(DEFAULTS)
    path = path or os.path.join(server_dir, "supervisor.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8-sig") as fh:
            user = json.load(fh)
        unknown = set(user) - set(DEFAULTS) - {"_comment"}
        if unknown:
            raise SystemExit("unknown keys in %s: %s" % (path, ", ".join(sorted(unknown))))
        cfg.update({k: v for k, v in user.items() if k in DEFAULTS})
    return cfg


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", default=os.path.dirname(os.path.abspath(__file__)),
                    help="server folder (default: the folder this file is in)")
    ap.add_argument("--config", help="config file (default: <dir>/supervisor.json)")
    ap.add_argument("--print-defaults", action="store_true", help="print the default config and exit")
    args = ap.parse_args()
    if args.print_defaults:
        print(json.dumps(DEFAULTS, indent=2))
        return
    server_dir = os.path.abspath(args.dir)
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")   # a cp1252 console cannot print every line
        except (AttributeError, ValueError):
            pass
    sup = Supervisor(server_dir, load_config(server_dir, args.config))
    if IS_WIN:
        # A process started in a new process group (by a scheduler, a launcher,
        # a background shell) inherits "ignore Ctrl+C", and then Ctrl+C here
        # silently does nothing; found in testing. Turn it back on.
        import ctypes
        ctypes.windll.kernel32.SetConsoleCtrlHandler(None, False)
    signal.signal(signal.SIGINT, sup.on_signal)
    signal.signal(signal.SIGTERM, sup.on_signal)
    if hasattr(signal, "SIGBREAK"):          # Ctrl+Break, and the console window closing
        signal.signal(signal.SIGBREAK, sup.on_signal)
    sup.run()


if __name__ == "__main__":
    main()
