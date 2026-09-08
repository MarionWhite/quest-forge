# -*- coding: utf-8 -*-
import ctypes
import sys
import time
from ctypes import wintypes
from pathlib import Path

from PIL import Image, ImageGrab

user32 = ctypes.windll.user32
EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
HWND_TOPMOST = -1
HWND_NOTOPMOST = -2
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_SHOWWINDOW = 0x0040


def list_windows():
    found = []

    def cb(hwnd, _l):
        if user32.IsWindowVisible(hwnd):
            n = ctypes.create_unicode_buffer(512)
            user32.GetWindowTextW(hwnd, n, 512)
            if n.value:
                found.append((int(hwnd), n.value))
        return True

    user32.EnumWindows(EnumWindowsProc(cb), 0)
    return found


def main():
    dest = Path(sys.argv[1])
    wins = list_windows()
    print("visible", [(t) for h, t in wins if "mine" in t.lower() or "quest" in t.lower() or "java" in t.lower()])
    mc = [(h, t) for h, t in wins if t == "Minecraft 1.7.10"]
    if not mc:
        raise SystemExit("no minecraft window")
    hwnd = mc[0][0]
    user32.ShowWindow(hwnd, 3)  # SW_MAXIMIZE
    time.sleep(0.25)
    user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)
    user32.SetForegroundWindow(hwnd)
    time.sleep(0.35)
    rect = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    bbox = (rect.left, rect.top, rect.right, rect.bottom)
    print("rect", bbox)
    try:
        im = ImageGrab.grab(bbox=bbox, all_screens=True)
    except TypeError:
        im = ImageGrab.grab(all_screens=True)
    user32.SetWindowPos(hwnd, HWND_NOTOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
    im.save(dest)
    print("saved", dest, im.size)


if __name__ == "__main__":
    main()
