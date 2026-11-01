#!/bin/sh
# Concatenate rendered segments, burn captions, add the mix, encode the deliverable.
set -e
FX=${FX_ROOT:-/tmp/fx}
OUT=${1:-/home/user/ihatethsd/feedback-video/FEEDBACK.mp4}
mkdir -p "$(dirname "$OUT")"
cd "$FX"
ls segs/seg_*.mp4 | grep -v part | sort > $FX/seglist.raw
n=$(wc -l < $FX/seglist.raw)
echo "segments: $n"
sed "s#^#file '$FX/#; s#\$#'#" $FX/seglist.raw > $FX/seglist.txt
ffmpeg -v error -y -f concat -safe 0 -i $FX/seglist.txt -i $FX/mix.wav \
  -vf "ass=$FX/captions.ass" -map 0:v -map 1:a \
  -c:v libx264 -preset slow -crf 21 -maxrate 4500k -bufsize 9000k -pix_fmt yuv420p -r 24 \
  -c:a aac -b:a 192k -movflags +faststart -shortest "$OUT"
ffprobe -v error -show_entries format=duration,size -of default=nw=1 "$OUT"
