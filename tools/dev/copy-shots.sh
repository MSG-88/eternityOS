#!/bin/bash
# Copy the offscreen render artifacts from WSL /tmp/e8shell to the Windows temp dir (dev helper).
for s in strip presence bar answer consent consent-pin bar-focused answer-streaming; do
  [ -f /tmp/e8shell/$s/$s.png ] && cp /tmp/e8shell/$s/$s.png /mnt/c/Users/muthu.MSG/AppData/Local/Temp/e8-$s.png
done
ls /mnt/c/Users/muthu.MSG/AppData/Local/Temp/e8-*.png | tr '\n' ' '
