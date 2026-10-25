#!/bin/bash
# Build 12 was folded into build 13 (the Eternity session chain carries the hardware and Claude
# Code work too). The build 11 resume chain still execs this file when out/build12.go appears,
# so it hands over to the build 13 chain. Log: /srv/eternity-build/out/build13-run.log.
exec bash /mnt/c/Users/muthu.MSG/Documents/Claude/eternity-08/tools/dev/chain-build13.sh
