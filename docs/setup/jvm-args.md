Quest Forge — Prism JVM arguments (Java 8 only)
================================================
Paste the EXTRA ARGS block into Prism.
Set the memory slider (or -Xmx) from the RAM preset that matches THIS Mac.
Do not use both a 6G slider and a 4G -Xmx. Pick one heap size.

How much RAM does this Mac have?
  Apple menu (, top-left) → About This Mac → look at Memory.
  8 GB  → use PRESET A
  16 GB → use PRESET B
  Never set 16G Xmx on an 8 GB Mac. The machine will freeze.

------------------------------------------------
PRESET A — M1 with 8 GB RAM
------------------------------------------------
Prism → Edit instance → Settings → Java
  Max memory: 4096 MiB
  Min memory: 1024 MiB

------------------------------------------------
PRESET B — M1 with 16 GB RAM
------------------------------------------------
Prism → Edit instance → Settings → Java
  Max memory: 6144 MiB
  Min memory: 2048 MiB

Do not go above 6144 on a 16 GB Mac for this 1.7.10 pack.
Do not use 7168 / 8192 / 16384.

------------------------------------------------
EXTRA JVM ARGS  (same for both presets — paste ALL of this)
------------------------------------------------
-Djava.net.preferIPv4Stack=true -Dfml.ignoreInvalidMinecraftCertificates=true -Dfml.ignorePatchDiscrepancies=true -Dlog4j2.formatMsgNoLookups=true -XX:MaxPermSize=256M -XX:+UseG1GC -XX:MaxGCPauseMillis=50 -XX:G1HeapRegionSize=16M -XX:ParallelGCThreads=4 -XX:ConcGCThreads=1 -XX:+UseSplitVerifier -XX:+FailOverToOldVerifier -XX:+UseCompressedOops -XX:+DisableExplicitGC -XX:-HeapDumpOnOutOfMemoryError

Notes:
  MaxPermSize=256M is REQUIRED on Java 8. Do not delete it.
  The two FML ignore* flags are REQUIRED so the patched Forge splash jar can load.
  Java 17/21 will reject MaxPermSize and will not run Forge 1.7.10.

------------------------------------------------
Java executable Prism must use
------------------------------------------------
Typical Temurin 8 x64 path after the .pkg install:

  /Library/Java/JavaVirtualMachines/temurin-8.jdk/Contents/Home/bin/java

If that folder name differs, in Terminal:

  /usr/libexec/java_home -v 1.8

Paste the printed path + /bin/java into Prism’s Java setting.
It MUST be 1.8.x (Java 8). Not 11, 17, 21, or 25.
It MUST be the x64 / Intel build (the .pkg whose name contains x64, not aarch64).
