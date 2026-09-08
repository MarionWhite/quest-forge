# -*- coding: utf-8 -*-
import ctypes
import sys
from ctypes import wintypes
from pathlib import Path

from PIL import ImageGrab

user32 = ctypes.windll.user32

EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)


def list_windows():
    found = []

    def cb(hwnd, _lparam):
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
    mc = [(h, t) for h, t in wins if t == "Minecraft 1.7.10"]
    if not mc:
        mc = [(h, t) for h, t in wins if "minecraft" in t.lower()]
    print("mc windows", mc)
    bbox = None
    if mc:
        hwnd = mc[0][0]
        user32.ShowWindow(hwnd, 9)  # SW_RESTORE
        user32.SetForegroundWindow(hwnd)
        rect = wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        bbox = (rect.left, rect.top, rect.right, rect.bottom)
        print("rect", bbox)
    try:
        im = ImageGrab.grab(bbox=bbox, all_screens=True) if bbox else ImageGrab.grab(all_screens=True)
    except TypeError:
        im = ImageGrab.grab(bbox=bbox) if bbox else ImageGrab.grab()
    im.save(dest)
    print("saved", dest, im.size)


if __name__ == "__main__":
    main()
