#!/bin/zsh
# Runs the Spotify spike on the SAME JVM the Quest Forge pack uses (Oracle 8u162,
# x86_64), so a pass here means a pass in-game. Double-click, or: ./run.command [tls|auth|play|all]
set -e
cd "$(dirname "$0")"

JAVA_HOME=/Library/Java/JavaVirtualMachines/jdk1.8.0_162.jdk/Contents/Home
"$JAVA_HOME/bin/javac" -Xlint:-options SpotifySpike.java
"$JAVA_HOME/bin/java" SpotifySpike "${1:-all}"
