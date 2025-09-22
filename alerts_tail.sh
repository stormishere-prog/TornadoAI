#!/data/data/com.termux/files/usr/bin/sh
cd /storage/emulated/0/Download/TornadoAI || exit 1
[ -f alerts/alerts_case.log ] && tail -n 20 alerts/alerts_case.log || echo "no alerts yet"
