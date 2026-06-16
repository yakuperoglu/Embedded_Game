# -*- coding: utf-8 -*-
"""
tools/aseprite_to_png.py
Photos/Sprite-0001.aseprite ve Sprite-0002.aseprite dosyalarini
assets/ship_p1.png (Oyuncu 1) ve assets/ship_p2.png (Oyuncu 2) olarak
disa aktarir. Tam saydam kenarlar kirpilir.

Aseprite'ta gemiyi duzenleyip KAYDETTIKTEN sonra proje kokunden calistir:
    python tools/aseprite_to_png.py

Beklenti: tek kare, 32-bit RGBA, sikistirilmis (compressed) cel.
Oyun bu PNG'leri assets/ klasorunden okur (yoksa ucgen govdeye duser).
"""

import os
import struct
import zlib

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JOBS = [
    (os.path.join(ROOT, "Photos", "Sprite-0001.aseprite"),
     os.path.join(ROOT, "assets", "ship_p1.png")),
    (os.path.join(ROOT, "Photos", "Sprite-0002.aseprite"),
     os.path.join(ROOT, "assets", "ship_p2.png")),
]


def convert(src: str, dst: str) -> None:
    data = open(src, "rb").read()
    depth = struct.unpack("<H", data[12:14])[0]
    if depth != 32:
        raise SystemExit("Sadece 32-bit RGBA destekleniyor (bu: %d-bit)" % depth)
    off = 128
    oldn = struct.unpack("<H", data[off + 6:off + 8])[0]
    newn = struct.unpack("<I", data[off + 12:off + 16])[0]
    nchunks = newn if newn else oldn
    co = off + 16
    cel = None
    for _ in range(nchunks):
        csize, ctype = struct.unpack("<IH", data[co:co + 6])
        if ctype == 0x2005:                       # Cel chunk
            cel = data[co + 6:co + csize]
        co += csize
    if cel is None:
        raise SystemExit("Cel chunk (0x2005) yok: " + src)
    if struct.unpack("<H", cel[7:9])[0] != 2:     # 2 = compressed image
        raise SystemExit("Cel 'compressed image' degil: " + src)
    cw, ch = struct.unpack("<HH", cel[16:20])
    raw = zlib.decompress(cel[20:])               # RGBA, satir-sirali
    surf = pygame.image.frombuffer(raw, (cw, ch), "RGBA").convert_alpha()
    bb = surf.get_bounding_rect()                 # saydam kenarlari kirp
    if bb.width and bb.height:
        surf = surf.subsurface(bb).copy()
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    pygame.image.save(surf, dst)
    print("%s -> %s (%dx%d)" % (os.path.basename(src),
                                os.path.relpath(dst, ROOT),
                                surf.get_width(), surf.get_height()))


def main() -> None:
    pygame.init()
    pygame.display.set_mode((64, 64))
    for src, dst in JOBS:
        if os.path.exists(src):
            convert(src, dst)
        else:
            print("atlandi (bulunamadi):", src)
    pygame.quit()


if __name__ == "__main__":
    main()
