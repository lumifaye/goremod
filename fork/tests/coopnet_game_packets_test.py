"""Compile the actual game packet modules with a small simulated game context.

Uses native little-endian C, not Wii U CPU emulation. Sends are simulated; the
separate CoopNet integration test covers real sockets and ICE.
"""
from pathlib import Path
from coopnet_packet_fixture import prepare
import subprocess
import tempfile
ROOT = Path(__file__).resolve().parents[2]
for platform in ('PC', 'Android', 'VR', 'WiiU'):
    source = ROOT / platform / 'src/pc/network/packets'
    with tempfile.TemporaryDirectory() as folder:
        tmp = Path(folder)
        includes, packet_dir = prepare(tmp, source)
        exe = tmp / 'test'
        subprocess.run(['cc','-std=gnu11','-O1','-Wall','-I'+str(includes),'-I'+str(tmp/'network'),
                        str(ROOT/'fork/tests/coopnet_game_packets_test.c'),
                        *(str(packet_dir/name) for name in ('packet_read_write.c','packet_reliable.c','packet_ordered.c')),
                        '-o',str(exe)], check=True)
        subprocess.run([str(exe)],check=True)
    print(platform, 'game-packet flow passed', flush=True)
