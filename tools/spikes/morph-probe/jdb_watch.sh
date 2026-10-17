#!/bin/bash
# Attach jdb once the probe's world is loaded; on any CrashReport construction,
# print the cause's real stack trace (it lands in the client's stderr log too).
TAG="$1"
C=/c/qfm/client
JDB="/c/Program Files/Eclipse Adoptium/jdk-8.0.504.1-hotspot/bin/jdb"
OUT="$C/logs/jdb-$TAG.txt"
for i in $(seq 1 600); do
  grep -q "heartbeat w=0" "$C/morphprobe.log" 2>/dev/null && break
  sleep 1
done
echo "world loaded, attaching" >> "$OUT"
{
  echo "stop in net.minecraft.crash.CrashReport.func_85057_a"
  echo "stop in net.minecraft.crash.CrashReport.func_71502_e"
  for i in $(seq 1 400); do
    sleep 2
    echo "where"
    echo "print this.field_71513_a"
    echo "eval this.field_71511_b.printStackTrace()"
    echo "print this.field_71511_b"
    echo "print this.field_71511_b.getStackTrace().length"
  done
} | "$JDB" -connect com.sun.jdi.SocketAttach:hostname=127.0.0.1,port=5005 >> "$OUT" 2>&1
