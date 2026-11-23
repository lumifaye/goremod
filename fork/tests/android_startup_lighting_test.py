"""Check Android startup ordering and exercise the inverse-transpose helper."""
from pathlib import Path
import subprocess, tempfile
root=Path(__file__).resolve().parents[2]
a=root/'Android'
main=(a/'src/pc/pc_main.c').read_text()
activity=(a/'platform/app/src/main/java/com/maniscat2/sm64coopdx/sm64coopdxActivity.java').read_text()
assert main.index('android_startup_message("awaitStartupOverlay"') < main.index('SDL_AndroidCopyAssetFilesToDir(basedir)')
assert main.index('render_early_loading_screen("Checking your ROM') < main.index('android_startup_message("hideStartupOverlay"')
assert 'startupDrawn.await(2, TimeUnit.SECONDS)' in activity and 'runOnUiThread' in activity
assert 'if (mLayout == null || mBrokenLibraries) return;' in activity
pc=(a/'src/pc/gfx/gfx_pc.c').read_text(); gl=(a/'src/pc/gfx/gfx_opengl.c').read_text()
for token in ('canEnhanceNormals', 'gfx_enhanced_world_normal(enhancedModel', 'want_enhanced_lighting', 'attributes < 8', 'cm->enhanced_lighting', 'v_arr[i]->enhanced_normal'):
    assert token in pc, token
for token in ('aWorldNormal', 'vWorldNormal', 'float normalLen2', 'float envRim', 'if (shadow_receiver && enhanced_lighting)'):
    assert token in gl, token
program=r'''
#include <assert.h>
#include <math.h>
#include "gfx_enhanced_lighting.h"
int main(void) {
    float m[4][4]={{2,0,0,0},{0,1,0,0},{0,0,1,0},{0,0,0,1}};
    float n[3]={1,1,0}, o[3];
    assert(gfx_enhanced_world_normal(m,n,o));
    assert(fabsf(o[0]-0.4472136f)<0.0001f && fabsf(o[1]-0.8944272f)<0.0001f);
    m[0][0]=-2; assert(gfx_enhanced_world_normal(m,n,o) && o[0]<0 && o[1]>0);
    m[0][0]=0; assert(!gfx_enhanced_world_normal(m,n,o));
}
'''
with tempfile.TemporaryDirectory() as tmp:
    exe=str(Path(tmp)/'test')
    subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-fsanitize=undefined','-I',str(a/'src/pc/gfx'),'-x','c','-','-lm','-o',exe],input=program.encode(),check=True)
    subprocess.run([exe],check=True)
print('Android pre-copy activity handoff and per-pixel lighting wiring: ok')
