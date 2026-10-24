# Dev-session helpers (WSL side, used by the Claude Code sessions)

- `start-chain.sh`: stop any test VM, start `live-loop.sh` and `chain-build-test-install.sh`
  detached inside WSL. Run as `wsl -d Debian -u root -- bash /mnt/c/.../tools/dev/start-chain.sh`.
- `chain-build-test-install.sh`: build + full suite (`build.sh --test`), then the unattended
  install test and a boot of the installed disk; log in `/srv/eternity-build/out/build9-run.log`
  (rename per build), ends with `BUILD9 DONE`.
- `live-loop.sh`: screenshots whichever test VM is running every 30 s into
  `tests/out/install/live.png`; open `live.html` (copy it next to live.png) in a browser.
- `watch-share.sh`: host-side (Git Bash) poller over `\wsl.localhost` that prints new CHECK
  lines and run results; `SKIP_EXISTING=1` starts from the current end of the logs.
- `inst.sh`: host-side wrapper for `tests/run-qemu-install.sh` with WSL retries.
Gotchas: pass `MSYS_NO_PATHCONV=1` from Git Bash; `$VAR` inside `wsl ... bash -c` arrives
empty, so put logic in script files; a Windows reboot kills everything in WSL.
