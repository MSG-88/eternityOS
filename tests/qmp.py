#!/usr/bin/env python3
"""Tiny QMP client for the visual tests: screendump (as PNG) and send-key.

Usage:
  qmp.py SOCK screendump OUT.png
  qmp.py SOCK keys "eternity" Enter          # types text, then named keys
  qmp.py SOCK key ret                        # one QEMU key name (ret, down, tab, ...)
  qmp.py SOCK click X Y [left|right]         # absolute pointer click at screen pixel (usb-tablet)
  qmp.py SOCK dblclick X Y
  qmp.py SOCK wait-ready
"""
import json
import socket
import sys
import time

from PIL import Image

KEYMAP = {" ": "spc", ".": "dot", "-": "minus", "/": "slash", ",": "comma", "_": ("shift", "minus"),
          ":": ("shift", "semicolon"), "'": "apostrophe", "=": "equal", "?": ("shift", "slash"),
          "!": ("shift", "1"), "@": ("shift", "2"), ";": "semicolon", "\n": "ret",
          "#": ("shift", "3"), "$": ("shift", "4"), "%": ("shift", "5"), "^": ("shift", "6"),
          "&": ("shift", "7"), "*": ("shift", "8"), "(": ("shift", "9"), ")": ("shift", "0"),
          "+": ("shift", "equal"), '"': ("shift", "apostrophe"), "<": ("shift", "comma"),
          ">": ("shift", "dot"), "|": ("shift", "backslash"), "\\": "backslash",
          "[": "bracket_left", "]": "bracket_right", "{": ("shift", "bracket_left"),
          "}": ("shift", "bracket_right"), "`": "grave_accent", "~": ("shift", "grave_accent")}
NAMED = {"Enter": "ret", "Tab": "tab", "Down": "down", "Up": "up", "Esc": "esc", "Space": "spc",
         "Left": "left", "Right": "right", "Backspace": "backspace", "Delete": "delete",
         "Ctrl-Alt-T": ("ctrl", "alt", "t"), "Ctrl-A": ("ctrl", "a"),
         "Alt-N": ("alt", "n"), "Alt-B": ("alt", "b"), "Alt-I": ("alt", "i"), "Alt-D": ("alt", "d"),
         "Alt-F4": ("alt", "f4"),
         "Super-Space": ("meta_l", "spc"), "Super-L": ("meta_l", "l"), "Super-Enter": ("meta_l", "ret"), "Super-Q": ("meta_l", "q")}
SCREEN_W, SCREEN_H = 1280, 800   # the virtio-vga mode the tests screenshot at


class QMP:
    def __init__(self, path, timeout=30):
        self.s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.s.settimeout(timeout)
        deadline = time.time() + timeout
        while True:
            try:
                self.s.connect(path)
                break
            except OSError:
                if time.time() > deadline:
                    raise
                time.sleep(0.5)
        self.f = self.s.makefile("rwb", buffering=0)
        self._read()  # greeting
        self.cmd("qmp_capabilities")

    def _read(self):
        while True:
            line = self.f.readline()
            if not line:
                raise RuntimeError("QMP closed")
            msg = json.loads(line)
            if "event" in msg:
                continue
            return msg

    def cmd(self, name, **args):
        self.f.write((json.dumps({"execute": name, "arguments": args}) + "\n").encode())
        r = self._read()
        if "error" in r:
            raise RuntimeError(r["error"])
        return r.get("return")

    def keys(self, names, hold=60):
        self.cmd("send-key", keys=[{"type": "qcode", "data": n} for n in names], **{"hold-time": hold})
        time.sleep(0.08)

    def type_text(self, text):
        for ch in text:
            if ch in KEYMAP:
                k = KEYMAP[ch]
                self.keys(list(k) if isinstance(k, tuple) else [k])
            elif ch.isupper():
                self.keys(["shift", ch.lower()])
            else:
                self.keys([ch])

    def click(self, x, y, button="left"):
        """Click at pixel (x, y) through an absolute pointer (needs -device usb-tablet)."""
        ax = int(x * 32767 / SCREEN_W)
        ay = int(y * 32767 / SCREEN_H)
        move = [{"type": "abs", "data": {"axis": "x", "value": ax}},
                {"type": "abs", "data": {"axis": "y", "value": ay}}]
        self.cmd("input-send-event", events=move)
        time.sleep(0.15)
        self.cmd("input-send-event", events=[{"type": "btn", "data": {"down": True, "button": button}}])
        time.sleep(0.1)
        self.cmd("input-send-event", events=[{"type": "btn", "data": {"down": False, "button": button}}])
        time.sleep(0.2)

    def screendump(self, out_png):
        ppm = out_png + ".ppm"
        self.cmd("screendump", filename=ppm)
        time.sleep(0.5)
        Image.open(ppm).convert("RGB").save(out_png)


def main():
    sock, action = sys.argv[1], sys.argv[2]
    q = QMP(sock)
    if action == "screendump":
        q.screendump(sys.argv[3])
    elif action == "keys":
        for arg in sys.argv[3:]:
            if arg in NAMED:
                k = NAMED[arg]
                q.keys(list(k) if isinstance(k, tuple) else [k])
            else:
                q.type_text(arg)
    elif action == "key":
        q.keys(sys.argv[3:])
    elif action == "click":
        q.click(int(sys.argv[3]), int(sys.argv[4]), sys.argv[5] if len(sys.argv) > 5 else "left")
    elif action == "dblclick":
        q.click(int(sys.argv[3]), int(sys.argv[4])); q.click(int(sys.argv[3]), int(sys.argv[4]))
    elif action == "wait-ready":
        pass
    else:
        sys.exit("unknown action " + action)


if __name__ == "__main__":
    main()
