#!/usr/bin/env python3
"""Makes the Wii U (32-bit, big-endian) form of a sound file that the repository
keeps in the PC (64-bit, little-endian) form.

    wiiu_sound_data.py sequences <sound/sequences_compressed.bin> <out sequences.bin>
    wiiu_sound_data.py bank_sets <sound/bank_sets_compressed>     <out bank_sets>

No ROM and no other project is needed. What changes is only the table at the
start of each file, which the game reads as numbers of the machine it runs on:

  sequences.bin   ALSeqFile: s16 revision, s16 count, then per sequence
                  { pointer offset, s32 length }. The pointer is 8 bytes on PC
                  and 4 on Wii U, so the table shrinks. The sequence data stays
                  at the offsets it has on PC (the gap is left as zeros),
                  because sound/sequences_offsets.h holds those offsets and the
                  game copies the music from the ROM to them when it starts.
  bank_sets       a table of u16 offsets, one per sequence, then bytes.

The sequence data itself (m64) and the bytes after the bank_sets table are read
one byte at a time by the game and are the same on every machine.

sound_data.ctl and sound_data.tbl need no conversion: on this branch
sound/sound_data_compressed.ctl/.tbl are already in the Wii U form (and
sound/samples_offsets.h belongs to them).
"""
import struct
import sys
import zlib


def align(value, to):
    return (value + to - 1) // to * to


def sequences(data):
    revision, count = struct.unpack_from('<hh', data, 0)
    if not 0 < count < 1024:
        raise SystemExit('sequences: not a little-endian 64-bit file (count %d)' % count)
    entries = [struct.unpack_from('<QI', data, 8 + 16 * i) for i in range(count)]
    header = struct.pack('>hh', revision, count)
    for offset, length in entries:
        if offset >= 1 << 32:
            raise SystemExit('sequences: offset 0x%x does not fit in 32 bits' % offset)
        header += struct.pack('>Ii', offset, length)
    header += bytes(align(len(header), 16) - len(header))
    first = min(offset for offset, _ in entries)
    if first < len(header) or first != align(8 + 16 * count, 16):
        raise SystemExit('sequences: unexpected start of data 0x%x' % first)
    return header + bytes(first - len(header)) + data[first:]


def bank_sets(data):
    count = struct.unpack_from('<H', data, 0)[0] // 2
    if not 0 < count < 1024 or 2 * count > len(data):
        raise SystemExit('bank_sets: not a little-endian file')
    table = struct.unpack_from('<%dH' % count, data, 0)
    if any(not 2 * count <= offset < len(data) for offset in table):
        raise SystemExit('bank_sets: an offset points outside the file')
    return struct.pack('>%dH' % count, *table) + data[2 * count:]


def main():
    if len(sys.argv) != 4 or sys.argv[1] not in ('sequences', 'bank_sets'):
        raise SystemExit(__doc__)
    with open(sys.argv[2], 'rb') as f:
        data = zlib.decompress(f.read())
    out = sequences(data) if sys.argv[1] == 'sequences' else bank_sets(data)
    if len(out) != len(data):
        raise SystemExit('%s: size changed (%d -> %d)' % (sys.argv[1], len(data), len(out)))
    with open(sys.argv[3], 'wb') as f:
        f.write(out)


if __name__ == '__main__':
    main()
