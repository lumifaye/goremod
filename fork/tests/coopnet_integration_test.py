"""Real local coordinator, staged baseline and branch CoopNet, ICE and UDP.

Runs both host directions. This is a native Linux test, not Wii U emulation;
its small request/response loop models retransmission, not the full game.
"""
from pathlib import Path
import socket
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
BASE = 'fdfff4b17e812e6caa2724ce82bbcb4b796452c5'

def build(tree, out):
    common = tree / 'WiiU/third_party/coopnet/common'
    juice = tree / 'WiiU/third_party/libjuice/src'
    inc = tree / 'WiiU/third_party/coopnet/lib/include'
    objects = []
    for src in juice.glob('*.c'):
        obj = out / (src.stem + '.o'); objects.append(obj)
        subprocess.run(['cc', '-O1', '-std=gnu11', '-DJUICE_ENABLE_LOCALHOST_ADDRESS=1', '-I', str(juice), '-I', str(inc / 'juice'), '-c', str(src), '-o', str(obj)], check=True)
    subprocess.run(['c++', '-O1', '-std=gnu++17', '-pthread', '-I', str(common), '-I', str(inc), str(ROOT / 'fork/tests/coopnet_integration.cpp'), *map(str, common.glob('*.cpp')), *map(str, objects), '-lm', '-o', str(out / 'coopnet')], check=True)
    return out / 'coopnet'

def run(server, host, guest):
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
            if (g.returncode or h.returncode or 'DROP_FIRST_REQUEST' not in output[1]
                    or 'COMPLETE_RECEIVED' not in output[1] or 'DROP_FIRST_RESPONSE' not in output[2]
                    or 'RESPONSE_RECEIVED' not in output[2]):
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
