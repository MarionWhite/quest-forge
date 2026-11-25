#!/usr/bin/env python3
"""Check the host PC's settings for running the friends' server, pass/fail per line.

    host_check.py                                   # defaults: C:\\qfs\\friends, play hours 17-02
    host_check.py --server C:\\qfs\\friends --play-hours 17-02 --syncthing-folder C:\\qf-world

What it checks and why (docs/setup/hosting-a-server.md, "The host machine"):

- Sleep and hibernation off on AC power (powercfg). A sleeping PC is a server
  that is down and a world saved mid-write.
- Windows Update active hours cover the play hours (registry). Outside active
  hours Windows may reboot for an update, which kills the server mid-save; the
  daily restart at 05:00 is the hour a reboot should land in.
- An inbound firewall rule allowing TCP on the server's port (server.properties).
  Without it, friends outside the LAN never reach the server even with the
  router forwarding the port.
- Syncthing running, with the share that carries the backup mirror connected
  to another device (its REST API, key from its config.xml). No connection
  means the mirror never leaves the machine.
- The census PAUSE file, if a balance campaign is running (run_campaign.py):
  census nodes compete for the clocks the server tick needs.
- The server's Java (a JDK with jstack, for hang dumps), free disk for backups,
  and whether the supervisor has a Discord webhook and a status publisher.
- Port forwarding cannot be checked from inside: the LAN and public addresses
  are printed with the router step, marked MANUAL.

Exit code 1 if anything FAILs. Reads only; changes nothing.
"""
import argparse, glob, json, os, re, shutil, socket, subprocess, sys, urllib.request
import xml.etree.ElementTree as ET

try:
    import winreg
except ImportError:
    winreg = None

RESULTS = []


def report(status, what, detail="", fix=""):
    RESULTS.append((status, what, detail, fix))


def ps(cmd):
    res = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", cmd],
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=60)
    return res.stdout


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


def powercfg_ac(subgroup, setting):
    """The AC value (seconds) of a power setting in the current scheme, or None."""
    try:
        out = subprocess.run(["powercfg", "/query", "SCHEME_CURRENT", subgroup, setting],
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True).stdout
    except OSError:
        return None
    m = re.search(r"Current AC Power Setting Index: 0x([0-9a-fA-F]+)", out)
    return int(m.group(1), 16) if m else None


def check_power():
    sleep = powercfg_ac("SUB_SLEEP", "STANDBYIDLE")
    hib = powercfg_ac("SUB_SLEEP", "HIBERNATEIDLE")
    fix = "powercfg /change standby-timeout-ac 0 ; powercfg /change hibernate-timeout-ac 0"
    if sleep is None:
        report("WARN", "Sleep on AC", "powercfg gave no value", fix)
    elif sleep == 0:
        report("PASS", "Sleep on AC", "never")
    else:
        report("FAIL", "Sleep on AC", "after %d min" % (sleep // 60), fix)
    if hib is None:
        report("WARN", "Hibernate on AC", "powercfg gave no value", fix)
    elif hib == 0:
        report("PASS", "Hibernate on AC", "never")
    else:
        report("FAIL", "Hibernate on AC", "after %d min" % (hib // 60), fix)


def check_active_hours(play):
    if not winreg:
        report("WARN", "Windows Update active hours", "not Windows")
        return
    try:
        k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\WindowsUpdate\UX\Settings")
        start = winreg.QueryValueEx(k, "ActiveHoursStart")[0]
        end = winreg.QueryValueEx(k, "ActiveHoursEnd")[0]
    except OSError:
        report("WARN", "Windows Update active hours", "not set (Windows picks them itself)",
               "Settings > Windows Update > Advanced options > Active hours: manual, covering the play hours")
        return
    hours = {(start + i) % 24 for i in range((end - start) % 24 or 24)}
    ps_, pe = play
    play_hours = {(ps_ + i) % 24 for i in range((pe - ps_) % 24 or 24)}
    missing = sorted(play_hours - hours)
    detail = "%02d:00-%02d:00 active; play %02d:00-%02d:00" % (start, end, ps_, pe)
    if missing:
        report("FAIL", "Windows Update active hours", detail + "; a reboot may land at %s" %
               ", ".join("%02d:00" % h for h in missing),
               "Settings > Windows Update > Advanced options > Active hours (at most 18 h); or pause "
               "updates for the season")
    else:
        report("PASS", "Windows Update active hours", detail)


def check_firewall(port):
    out = ps("Get-NetFirewallPortFilter | Where-Object { $_.LocalPort -eq %d -and $_.Protocol -eq 'TCP' } | "
             "ForEach-Object { $_ | Get-NetFirewallRule } | Where-Object { $_.Enabled -eq 'True' -and "
             "$_.Direction -eq 'Inbound' -and $_.Action -eq 'Allow' } | "
             "ForEach-Object { $_.DisplayName + ' [' + $_.Profile + ']' }" % port)
    rules = [l.strip() for l in out.splitlines() if l.strip()]
    fix = ("admin PowerShell: New-NetFirewallRule -DisplayName 'Quest Forge server' -Direction Inbound "
           "-Protocol TCP -LocalPort %d -Action Allow -Profile Any" % port)
    if rules:
        report("PASS", "Firewall allows TCP %d in" % port, "; ".join(rules))
    else:
        report("FAIL", "Firewall allows TCP %d in" % port, "no enabled inbound allow rule", fix)
    # The Java 25 server listening is also a quick way to know a boot finished;
    # here it just tells the owner whether the port test below means anything.
    s = socket.socket()
    s.settimeout(1)
    listening = s.connect_ex(("127.0.0.1", port)) == 0
    s.close()
    report("INFO", "Server listening on %d now" % port, "yes" if listening else "no (start it before an outside test)")


def syncthing_api():
    cfg = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Syncthing", "config.xml")
    if not os.path.exists(cfg):
        return None, None
    try:
        root = ET.parse(cfg).getroot()
        gui = root.find("gui")
        key = gui.findtext("apikey")
        addr = gui.findtext("address") or "127.0.0.1:8384"
        if addr.startswith("0.0.0.0"):
            addr = "127.0.0.1" + addr[7:]
        return "http://" + addr, key
    except (ET.ParseError, AttributeError):
        return None, None


def st_get(base, key, path):
    req = urllib.request.Request(base + path, headers={"X-API-Key": key})
    with urllib.request.urlopen(req, timeout=5) as r:
        return json.load(r)


def check_syncthing(folder, mirror):
    running = "syncthing" in ps("Get-Process syncthing -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Name").lower()
    base, key = syncthing_api()
    if not running:
        report("FAIL", "Syncthing running", "no syncthing.exe process",
               "start Syncthing (it should autostart; the backup mirror leaves the machine through it)")
        return
    if not base or not key:
        report("WARN", "Syncthing API", "no %%LOCALAPPDATA%%\\Syncthing\\config.xml; cannot read the share state")
        return
    try:
        folders = st_get(base, key, "/rest/config/folders")
        conns = st_get(base, key, "/rest/system/connections")["connections"]
    except Exception as e:
        report("WARN", "Syncthing API", "unreachable (%s)" % type(e).__name__)
        return
    want = os.path.normcase(os.path.abspath(folder))
    share = next((f for f in folders if os.path.normcase(os.path.abspath(f["path"])) == want), None)
    if not share:
        report("FAIL", "Syncthing share %s" % folder, "no folder with that path in Syncthing",
               "Syncthing > Add Folder, path %s, share it with the Mac" % folder)
        return
    devs = [d["deviceID"] for d in share.get("devices", [])]
    connected = [d for d in devs if conns.get(d, {}).get("connected")]
    try:
        state = st_get(base, key, "/rest/db/status?folder=" + share["id"]).get("state", "?")
    except Exception:
        state = "?"
    peers = max(0, len(devs) - 1)     # the local device is in its own list
    if connected:
        report("PASS", "Syncthing share %s" % folder, "%d of %d peer(s) connected, state %s" % (len(connected), peers, state))
    else:
        report("FAIL", "Syncthing share %s" % folder, "%d peer(s), none connected (state %s): the mirror stays here" % (peers, state),
               "open Syncthing on the other machine; check both are on a network")
    if mirror:
        inside = os.path.normcase(os.path.abspath(mirror)).startswith(want + os.sep) or \
            os.path.normcase(os.path.abspath(mirror)) == want
        if inside:
            report("PASS", "Backup mirror leaves the machine", "%s is inside the share" % mirror)
        else:
            report("WARN", "Backup mirror leaves the machine", "%s is not inside %s" % (mirror, folder),
                   "point --backup-mirror into the share, or share the mirror folder itself")
    else:
        report("WARN", "Backup mirror", "none configured (supervisor.json backup_mirror)",
               "build with --backup-mirror %s\\server-backups" % folder)


def check_census(campaign):
    out = ps("Get-CimInstance Win32_Process -Filter \"Name like 'py%' or Name like 'python%'\" | "
             "Where-Object { $_.CommandLine -match 'run_campaign' } | Select-Object -ExpandProperty ProcessId")
    pids = [l.strip() for l in out.splitlines() if l.strip()]
    pause = os.path.join(campaign, "PAUSE")
    if not pids:
        report("PASS", "Census campaign", "not running")
    elif os.path.exists(pause):
        report("PASS", "Census campaign", "running (pid %s), PAUSE present" % ", ".join(pids))
    else:
        report("FAIL", "Census campaign", "running (pid %s) without PAUSE: it competes for the clocks" % ", ".join(pids),
               "create %s before a play session" % pause)


def check_java_and_disk(server):
    bat = os.path.join(server, "start.bat")
    java = None
    if os.path.exists(bat):
        m = re.search(r'^"([^"]+java\.exe)"', open(bat, encoding="latin-1").read(), re.M)
        java = m.group(1) if m else None
    if java and os.path.exists(java):
        jstack = os.path.join(os.path.dirname(java), "jstack.exe")
        if os.path.exists(jstack):
            report("PASS", "Server Java", "%s (JDK: hang dumps work)" % java)
        else:
            alt = sorted(glob.glob(r"C:\Program Files\Eclipse Adoptium\jdk-8*\bin\jstack.exe"), reverse=True)
            report("PASS" if alt else "WARN", "Server Java", "%s (a JRE)%s" % (java, "; JDK 8 jstack found" if alt else ""),
                   "" if alt else "install a Temurin JDK of the same major version for hang dumps")
    else:
        report("WARN", "Server Java", "no start.bat java found under %s" % server)
    try:
        free = shutil.disk_usage(server).free
        daily = os.path.join(server, "backups", "daily")
        newest = max((os.path.getsize(os.path.join(daily, f)) for f in os.listdir(daily)), default=0) if os.path.isdir(daily) else 0
        need = max(20e9, 10 * newest)
        report("PASS" if free > need else "FAIL", "Free disk for backups", "%.0f GB free; newest daily %.0f MB" % (free / 1e9, newest / 1e6),
               "" if free > need else "free space or lower keep_hourly/keep_daily")
    except OSError:
        report("WARN", "Free disk for backups", "cannot read %s" % server)


def check_supervisor(server):
    path = os.path.join(server, "supervisor.json")
    cfg = {}
    if os.path.exists(path):
        try:
            cfg = json.load(open(path, encoding="utf-8-sig"))
        except ValueError:
            report("FAIL", "supervisor.json", "not valid JSON", "fix it; the supervisor refuses to start otherwise")
    if cfg.get("discord_webhook") or os.environ.get("QF_DISCORD_WEBHOOK"):
        report("PASS", "Discord alerts", "webhook set")
    else:
        report("WARN", "Discord alerts", "no webhook: crashes and hangs are only in logs/supervisor.log",
               "set discord_webhook in supervisor.json")
    pub = cfg.get("status_publisher") or ""
    report("INFO", "Who's online feed", "publisher %s" % (pub or "off (status.json is written locally only)"))
    return cfg


def check_port_forward(port):
    lan = "?"
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        lan = s.getsockname()[0]
        s.close()
    except OSError:
        pass
    public = "?"
    try:
        public = urllib.request.urlopen("https://api.ipify.org", timeout=5).read().decode().strip()
    except Exception:
        pass
    report("MANUAL", "Router forwards TCP %d" % port, "to %s (this PC); public address %s" % (lan, public),
           "forward TCP %d to %s in the router, then have a friend connect to %s:%d while the server is up"
           % (port, lan, public, port))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--server", default=r"C:\qfs\friends")
    ap.add_argument("--play-hours", default="17-02", help="local hours the friends play, START-END (default 17-02)")
    ap.add_argument("--syncthing-folder", default=r"C:\qf-world", help="the share that carries the backup mirror")
    ap.add_argument("--campaign", default=r"C:\qfs\campaign", help="where run_campaign.py's PAUSE file goes")
    args = ap.parse_args()
    play = tuple(int(x) for x in args.play_hours.split("-"))
    props = read_properties(os.path.join(args.server, "server.properties"))
    port = int(props.get("server-port") or 25565)

    check_power()
    check_active_hours(play)
    check_firewall(port)
    sup = check_supervisor(args.server)
    check_syncthing(args.syncthing_folder, sup.get("backup_mirror") or "")
    check_census(args.campaign)
    check_java_and_disk(args.server)
    check_port_forward(port)

    width = max(len(r[1]) for r in RESULTS)
    for status, what, detail, fix in RESULTS:
        print("%-6s %-*s  %s" % (status, width, what, detail))
        if fix and status in ("FAIL", "WARN", "MANUAL"):
            print("%-6s %-*s  -> %s" % ("", width, "", fix))
    fails = sum(1 for r in RESULTS if r[0] == "FAIL")
    print("\n%d FAIL, %d WARN, %d MANUAL, %d PASS" % (fails, sum(1 for r in RESULTS if r[0] == "WARN"),
                                                    sum(1 for r in RESULTS if r[0] == "MANUAL"),
                                                    sum(1 for r in RESULTS if r[0] == "PASS")))
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
