#!/bin/sh
# grab.sh <job_dir> <name>: copy the picture the browser just saved (Chrome writes it as <guid>.tmp first, then <file>.png)
# from the Downloads folder into <job_dir>/images/<name>.png. Run it right after window.__save(...) in the ChatGPT tab.
DL="${DOWNLOADS:-$HOME/Downloads}"
JOB="$1"; NAME="$2"
[ -n "$JOB" ] && [ -n "$NAME" ] || { echo "usage: grab.sh <job_dir> <name>"; exit 2; }
mkdir -p "$JOB/images"
for i in $(seq 1 15); do
  f=$(find "$DL" -maxdepth 1 -newermt "-40 seconds" -type f \( -name "*$NAME*" -o -name "*.tmp" \) -size +300k 2>/dev/null | head -1)
  [ -n "$f" ] && { cp "$f" "$JOB/images/$NAME.png" && echo "saved $NAME from $f"; exit 0; }
  sleep 1
done
echo "not found"; exit 1
