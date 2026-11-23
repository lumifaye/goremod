"""Player-only wet sheen: exercise the actual math and display-list wiring."""
from pathlib import Path
import subprocess
import tempfile
root = Path(__file__).resolve().parents[2]
for platform in ('PC', 'Android', 'VR'):
    base = root / platform
    header = (base / 'src/pc/gfx/gfx_wet_sheen.h').read_text()
    renderer = (base / 'src/game/rendering_graph_node.c').read_text()
    gfx = (base / 'src/pc/gfx/gfx_pc.c').read_text()
    assert 'gMarioStates[player].marioObj == currList->owner' in renderer
    assert 'if (playerSheen) gSPPlayerSheen(gDisplayListHead++, true);' in renderer
    assert 'if (playerSheen) gSPPlayerSheen(gDisplayListHead++, false);' in renderer
    assert 'configBetterGraphics && sPlayerSheen && !gFullbright && sHasInverseCameraMatrix' in gfx
    assert 'case G_PLAYER_SHEEN_EXT:' in gfx and 'sPlayerSheen = false;' in gfx
    program = header + r'''
#include <assert.h>
int main(void) {
    float p[3]={0,0,0}, eye[3]={0,0,3}, front[3]={0,0,1}, back[3]={0,0,-1}, zero[3]={0,0,0};
    assert(gfx_wet_sheen(p,front,eye)>0.0f);
    assert(gfx_wet_sheen(p,back,eye)==0.0f);
    assert(gfx_wet_sheen(p,zero,eye)==0.0f);
    assert(gfx_wet_sheen(p,front,p)==0.0f);
    eye[0]=NAN; assert(gfx_wet_sheen(p,front,eye)==0.0f);
    return 0;
}
'''
    with tempfile.TemporaryDirectory() as temp:
        exe = str(Path(temp) / 'test')
        subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-x','c','-', '-lm','-o',exe],input=program.encode(),check=True)
        subprocess.run([exe],check=True)
    print(platform, 'player sheen math and opt-in wiring: ok')
