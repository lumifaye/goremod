#!/usr/bin/env python3
"""Wii U: take the day-night skies out of the built-in Day Night Cycle mod.

On the Wii U the game does not draw that mod's own sky object. It hides it and draws the game's
normal sky with the mod's pictures instead (src/game/skybox.c, skybox_wiiu_apply_daynight_override),
so the 18 pictures have to be built into the game as normal skies. The port expected them as
textures/skyboxes/dnc_*.png, which were never published. They are all inside the mod's model file,
mods/day-night-cycle/actors/dnc_skybox_geo.bin, as 256x256 PNG pictures named
dnc_skybox_<sky>_<time>_rgba16. This tool writes them out as dnc_<sky>_<time>.png, which the normal
sky rule (tools/skyconv) then turns into <name>_skybox_ptrlist.

Usage: wiiu_dnc_skyboxes.py <dnc_skybox_geo.bin> <output folder>
"""
import os
import struct
import sys
import zlib

SKIES = ('water', 'wdw', 'cloud_floor', 'ccm', 'ssl', 'clouds')
TIMES = ('night', 'sunrise', 'sunset')
PNG_START = b'\x89PNG\r\n\x1a\n'
PNG_END = b'IEND\xaeB`\x82'
NAME_CHARS = set(b'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_')


def fail(text):
    sys.stderr.write('wiiu_dnc_skyboxes: ' + text + '\n')
    sys.exit(1)


def read_model_file(path):
    data = open(path, 'rb').read()
    if data[:8] == b'DYNOSBIN':  # packed: the unpacked length, then zlib data
        length = struct.unpack('<Q', data[8:16])[0]
        data = zlib.decompress(data[16:])
        if len(data) != length:
            fail('%s: unpacked to %d bytes, the file says %d' % (path, len(data), length))
    return data


def pictures_in(data):
    """Every PNG in the file, by the name written in front of it.

    A picture is stored as: one byte with the length of the name, the name, four bytes with the
    length of the PNG (lowest byte first), the PNG.
    """
    found = {}
    at = data.find(PNG_START)
    while at >= 0:
        if at >= 5:
            length = struct.unpack('<I', data[at - 4:at])[0]
            png = data[at:at + length]
            if length >= 57 and png.endswith(PNG_END):
                for name_length in range(1, 256):
                    start = at - 4 - name_length
                    if start < 1:
                        break
                    name = data[start:at - 4]
                    if not all(c in NAME_CHARS for c in name):
                        break
                    if data[start - 1] == name_length:
                        found[name.decode('ascii')] = png
                        break
        at = data.find(PNG_START, at + 1)
    return found


def main():
    if len(sys.argv) != 3:
        fail('usage: wiiu_dnc_skyboxes.py <dnc_skybox_geo.bin> <output folder>')
    source, folder = sys.argv[1], sys.argv[2]

    pictures = pictures_in(read_model_file(source))
    os.makedirs(folder, exist_ok=True)

    for sky in SKIES:
        for time in TIMES:
            name = 'dnc_skybox_%s_%s_rgba16' % (sky, time)
            png = pictures.get(name)
            if png is None:
                fail('%s has no picture named %s' % (source, name))
            width, height = struct.unpack('>II', png[16:24])
            if (width, height) not in ((256, 256), (248, 248)):
                fail('%s is %dx%d; a sky has to be 256x256 or 248x248' % (name, width, height))
            with open(os.path.join(folder, 'dnc_%s_%s.png' % (sky, time)), 'wb') as out:
                out.write(png)


if __name__ == '__main__':
    main()
