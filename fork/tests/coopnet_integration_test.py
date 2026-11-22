"""Coordinator, ICE and UDP with transport and staged game-packet flows.

Runs both host directions on native Linux, not Wii U hardware or emulation.
The game flow uses real codec, compression, retry/ACK and ordered modules,
but stubs game state, routing, mod-list payload handlers and packet dispatch.
"""
from pathlib import Path
from coopnet_packet_fixture import prepare
import os
import shutil
import socket
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
BASE = 'fdfff4b17e812e6caa2724ce82bbcb4b796452c5'

def build(tree, out, packet_source=None):
    common = tree / 'WiiU/third_party/coopnet/common'
    juice = tree / 'WiiU/third_party/libjuice/src'
    inc = tree / 'WiiU/third_party/coopnet/lib/include'
    objects = []
    for src in juice.glob('*.c'):
        obj = out / (src.stem + '.o'); objects.append(obj)
        subprocess.run(['cc', '-O1', '-std=gnu11', '-DJUICE_ENABLE_LOCALHOST_ADDRESS=1', '-I', str(juice), '-I', str(inc / 'juice'), '-c', str(src), '-o', str(obj)], check=True)
    driver = 'coopnet_integration.cpp'
    if packet_source:
        driver = 'coopnet_game_integration.cpp'
        source = packet_source / 'src/pc/network/packets'
        includes, packet_dir = prepare(out, source)
        # Only the public zlib ABI used by packet.c; use the runtime library so
        # this test also runs in environments without development headers.
        (includes / 'zlib.h').write_text('''typedef unsigned char Bytef;
typedef unsigned long uLong, uLongf;
#define Z_BEST_COMPRESSION 9
#define Z_OK 0
uLong compressBound(uLong);
int compress2(Bytef*, uLongf*, const Bytef*, uLong, int);
int uncompress(Bytef*, uLongf*, const Bytef*, uLong);
''')
        packet_c = (source / 'packet.c').read_text()
        (packet_dir / 'compression.c').write_text('#include "../network.h"\n#include <zlib.h>\n' + packet_c[packet_c.index('static u32 sCompBufferLen'):packet_c.index('void packet_process(')])
        for src in [*(packet_dir / name for name in ('packet_read_write.c', 'packet_reliable.c', 'packet_ordered.c', 'compression.c')), ROOT / 'fork/tests/coopnet_game_wire.c']:
            obj = out / ('game_' + src.stem + '.o'); objects.append(obj)
            subprocess.run(['cc', '-O1', '-std=gnu11', '-I'+str(includes), '-I'+str(out/'network'), '-c', str(src), '-o', str(obj)], check=True)
    subprocess.run(['c++', '-O1', '-std=gnu++17', '-pthread', '-I', str(common), '-I', str(inc), str(ROOT / 'fork/tests' / driver), *map(str, common.glob('*.cpp')), *map(str, objects), '-lm', '-l:libz.so.1', '-o', str(out / 'coopnet')], check=True)
    return out / 'coopnet'

def run(server, host, guest, game=False):
    sock = socket.socket(); sock.bind(('127.0.0.1', 0)); port = str(sock.getsockname()[1]); sock.close()
    with tempfile.TemporaryDirectory() as folder:
        paths = [Path(folder) / str(i) for i in range(3)]
        logs = [p.open('w+') for p in paths]
        procs = []
        try:
            def start(exe, role, log):
                p = subprocess.Popen([str(exe), role, port], stdout=log, stderr=subprocess.STDOUT, cwd=folder)
                procs.append(p); return p
            def await_log(path, marker, process):
                deadline = time.monotonic() + 10
                while time.monotonic() < deadline:
                    if marker in path.read_text(): return
                    if process.poll() is not None: break
                    time.sleep(.02)
                raise AssertionError('did not see ' + marker)
            s = start(server, 'server', logs[0]); await_log(paths[0], 'LISTENING', s)
            h = start(host, 'host', logs[1]); await_log(paths[1], 'JOINED self=1', h)
            g = start(guest, 'guest', logs[2])
            g.wait(timeout=30); h.wait(timeout=5)
            for f in logs: f.flush(); f.seek(0)
            output = [f.read() for f in logs]
            if game:
                ok = ('GAME_DROP_REQUEST' in output[1] and 'GAME_DROP_HEADER' in output[2]
                      and 'GAME_ORDERED_DONE' in output[2])
            else:
                ok = ('DROP_FIRST_REQUEST' in output[1] and 'COMPLETE_RECEIVED' in output[1]
                      and 'DROP_FIRST_RESPONSE' in output[2] and 'RESPONSE_RECEIVED' in output[2])
            if g.returncode or h.returncode or not ok:
                raise AssertionError('\n'.join(output))
            print('host:', output[1].strip().replace('\n', ' | '))
            print('guest:', output[2].strip().replace('\n', ' | '))
        finally:
            for p in procs:
                if p.poll() is None: p.terminate()
            for p in procs:
                try: p.wait(timeout=3)
                except subprocess.TimeoutExpired: p.kill(); p.wait()
            for f in logs: f.close()

with tempfile.TemporaryDirectory() as tmp:
    temp = Path(tmp); baseline = temp / 'baseline'; baseline.mkdir()
    archive = subprocess.Popen(['git', 'archive', BASE, 'WiiU/third_party/coopnet', 'WiiU/third_party/libjuice'], cwd=ROOT, stdout=subprocess.PIPE)
    subprocess.run(['tar', '-x', '-C', str(baseline)], stdin=archive.stdout, check=True); archive.stdout.close()
    if archive.wait(): raise RuntimeError('git archive failed')
    a = temp / 'a'; b = temp / 'b'; a.mkdir(); b.mkdir()
    staged = build(baseline, a); branch = build(ROOT, b)
    print('staged baseline transport on both sides', flush=True); run(branch, staged, staged)
    print('staged Wii U baseline host / branch transport guest', flush=True); run(branch, staged, branch)
    print('branch transport host / staged Wii U baseline guest', flush=True); run(branch, branch, staged)
    mods = temp / 'empty-mods'; mods.mkdir()
    game_trees = {}
    for name, base_name in (('WiiU', 'pc'), ('PC', 'pc'), ('Android', 'android')):
        path = temp / ('staged-' + name)
        shutil.copytree(ROOT / name, path, symlinks=True)
        result = subprocess.run(['python3', str(ROOT / 'fork/apply.py'), base_name, str(path)], cwd=ROOT,
                                env=dict(os.environ, MODS_DIR=str(mods)), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        if result.returncode: raise AssertionError(name + ' staging failed:\n' + result.stdout[-8000:])
        game_trees[name] = path
    c = temp / 'c'; d = temp / 'd'; e = temp / 'e'; c.mkdir(); d.mkdir(); e.mkdir()
    wiiu_game = build(baseline, c, game_trees['WiiU']); pc_game = build(ROOT, d, game_trees['PC'])
    android_game = build(ROOT, e, game_trees['Android'])
    print('real game packet modules: Wii U transport host / PC game packet client', flush=True); run(branch, wiiu_game, pc_game, game=True)
    print('real game packet modules: PC game packet host / Wii U transport client', flush=True); run(branch, pc_game, wiiu_game, game=True)
    print('real game packet modules: Wii U transport host / Android game packet client', flush=True); run(branch, wiiu_game, android_game, game=True)
    print('real game packet modules: Android game packet host / Wii U transport client', flush=True); run(branch, android_game, wiiu_game, game=True)
