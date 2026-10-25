# Build 14 on Hyper-V: live test of the shell, the on-device model and Claude Code

The VM "Eternity08-Test" (Gen 2, Secure Boot with the Microsoft UEFI CA template, 4 vCPU,
dynamic 1-6 GB, 40 GB disk) is recreated from `out\eternity-08-0.1.0-amd64.iso` by
`tools\elevated\scripts\60-build14-vm.ps1` (queue it and `schtasks /run /tn Eternity-Elevated`).
It opens the console window; everything below is visible there as it happens. Keep the other
hand-made VM off: the host has 14 GB and WSL takes 5 GB during a build.

## 1. Boot and session (scripted, `60-build14-vm.ps1`)
GRUB "Eternity 08 Live (Eternity shell)" → splash (the boot-log lines must now be readable
text, not boxes) → greeter → password `eternity` → the presence desktop. Expected: no red
config-error box, no "started without start-hyprland" notice, the Möbius mark animating in the
core, strip at the top, ask bar at the bottom. Screenshots `tests\out\hyperv\b14-*.png`.

## 2. On-device model (scripted, `61-llm-test.ps1`)
Super+Space, question "What hardware is this machine and how much memory does it have?", Enter.
Expected: the answer streams within about 30 s on 4 vCPU (the 2B model if the VM has under
4 GB free, the default 4B model otherwise; the ETERNITY card names the model), the readout shows
first-token time and tok/s. Super+M shows the Monitor's AI panel with tok/s. Screenshots
`tests\out\hyperv\llm-*.png`.

## 3. Claude Code (needs you at the console once)
1. Super+, opens Settings. On the Assistant page, "Who answers": choose **Claude account**
   (or type `/claude` in the ask bar). Click **Sign in with your Claude account**: a terminal
   runs `claude auth login`, which prints a URL and a code.
2. Open that URL in your browser on Windows, sign in to your Claude account, paste the code
   back in the terminal. The terminal says done; close it. Eternity stores nothing itself;
   Claude Code keeps the sign-in in `~/.config/claude` of the live user (gone after reboot
   until persistence lands).
3. Super+Space, ask "Which window manager am I running and what is its version?" Expected:
   the strip and the ask bar show "Claude (your Claude account)", the answer arrives through
   Claude Code with the Eternity tools (it may propose an action; the consent card asks you),
   `/sessions` lists the session, `/model haiku` switches the model, `/ondevice` goes back.
4. Super+M: the Monitor shows the Claude cost line. The Claude Code hook audits every tool call;
   `journalctl --user -b | grep claude-hook` in a terminal (Super+Enter) shows them.

What cannot work in this VM and why: GPU acceleration (software rendering, CPU at 100% while
animating), speakers (no audio device), the install (40 GB disk is there, but install testing
comes after the live test). The 125 % default scale applies to a laptop panel (eDP-1); the
virtual output runs at 100 %.
