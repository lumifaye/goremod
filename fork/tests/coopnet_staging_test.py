"""Exercise release source staging for all ports, without a full game build."""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
BASE = 'fdfff4b17e812e6caa2724ce82bbcb4b796452c5'
with tempfile.TemporaryDirectory() as tmp:
    tmp = Path(tmp); mods = tmp / 'mods'; mods.mkdir()
    env = dict(os.environ, MODS_DIR=str(mods))
    for folder, base in (('PC', 'pc'), ('Android', 'android'), ('VR', 'vr'), ('WiiU', 'pc')):
        tree = tmp / folder
        shutil.copytree(ROOT / folder, tree, symlinks=True)
        p = subprocess.run(['python3', str(ROOT / 'fork/apply.py'), base, str(tree)], cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        if p.returncode:
            raise AssertionError(folder + ' staging failed:\n' + p.stdout[-8000:])
        packet = (tree / 'src/pc/network/packets/packet_reliable.c').read_text()
        body = packet[packet.index('void network_forget_all_reliable(void)'):packet.index('void network_forget_all_reliable_from')]
        assert body.count('remove_node_from_list(node);') == 1 and 'remove_node_from_list(head);' not in body
        assert 'ack.addr = p->addr;' in packet
        if folder == 'WiiU':
            # Match the release's subsequent transport replacement exactly.
            archive = subprocess.Popen(['git','archive',BASE,'WiiU/third_party/coopnet','WiiU/third_party/libjuice'], cwd=ROOT, stdout=subprocess.PIPE)
            subprocess.run(['tar','-x','-C',str(tmp)], stdin=archive.stdout, check=True)
            archive.stdout.close()
            assert archive.wait() == 0
            baseline = subprocess.check_output(['git','show',BASE+':WiiU/third_party/coopnet/common/peer.cpp'], cwd=ROOT)
            assert (tree / 'third_party/coopnet/common/peer.cpp').read_bytes() == baseline
            assert 'coopnet_start_join_once' in (tree / 'src/pc/network/coopnet/coopnet.c').read_text()
        print(folder + ' release staging and reliable cleanup: ok', flush=True)
        shutil.rmtree(tree)
