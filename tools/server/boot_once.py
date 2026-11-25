"""Boot a built play server once, headless, and stop it when it reports ready.

    py -3.10 -I tools/server/boot_once.py <server dir> <stdout log> [timeout seconds]

For tests that need one boot of a server the builder made (a scratch build, never
the friends' server while it is in use): it reads the java command from the
server's start.bat, runs it with the server directory as working directory and
stdin piped, mirrors stdout into the log, sends `stop` five seconds after the
"Done (" line, and waits for the process to exit. Used on 2026-10-25 to show that
MCHeli registers no aircraft without assets/mcheli (docs/setup/hosting-a-server.md).
A plain pipe, not a fifo: a Windows JVM cannot read an MSYS named pipe, and a
`stop` typed from PowerShell arrives with a BOM and is "Unknown command".
"""
import os, re, subprocess, sys, threading, time

server, log_path = sys.argv[1], sys.argv[2]
timeout = int(sys.argv[3]) if len(sys.argv) > 3 else 600

bat = open(os.path.join(server, 'start.bat'), encoding='utf-8').read()
# "<java>" flags ^\n flags ^\n -jar <forge> nogui
m = re.search(r'^"([^"]+)"(.*?)-jar (\S+) nogui', bat, re.S | re.M)
if not m:
    sys.exit('start.bat: no java line')
java, flags, forge = m.group(1), m.group(2).replace('^', ' ').split(), m.group(3)
cmd = [java] + flags + ['-jar', forge, 'nogui']
print('cmd:', ' '.join(cmd))
os.makedirs(os.path.join(server, 'logs'), exist_ok=True)
log = open(log_path, 'w', encoding='utf-8', errors='replace')
p = subprocess.Popen(cmd, cwd=server, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                     stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace', bufsize=1)
ready = threading.Event()
dead = threading.Event()


def reader():
    try:
        for line in p.stdout:
            log.write(line)
            log.flush()
            if 'Done (' in line:
                ready.set()
    except Exception:
        pass
    dead.set()


threading.Thread(target=reader, daemon=True).start()
t0 = time.time()
while not ready.is_set() and not dead.is_set() and time.time() - t0 < timeout:
    time.sleep(1)
status = 'ready' if ready.is_set() else ('died' if dead.is_set() else 'timeout')
print('server %s after %.0f s' % (status, time.time() - t0))
if ready.is_set():
    time.sleep(5)  # let the world save settle
    try:
        p.stdin.write('stop\n')
        p.stdin.flush()
    except Exception as e:
        print('stop failed:', e)
try:
    p.wait(timeout=180)
except subprocess.TimeoutExpired:
    print('did not exit; killing')
    p.kill()
print('exit code', p.returncode)
log.close()
