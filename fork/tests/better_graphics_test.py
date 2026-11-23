"""Exercise the actual optional lighting block and release/target wiring."""
from pathlib import Path
import subprocess
import tempfile
ROOT = Path(__file__).resolve().parents[2]
for platform in ('PC', 'Android', 'VR'):
    base = ROOT / platform / 'src/pc'
    config = (base/'configfile.c').read_text()
    assert 'configBetterGraphics                 = false;' in config
    assert '"better_graphics"' in config
    assert '"Experimental Better Graphics", &configBetterGraphics' in (base/'djui/djui_panel_display.c').read_text()
    source = (base/'gfx/gfx_pc.c').read_text()
    start = source.index('            if (configBetterGraphics && !gFullbright) {')
    end = source.index('\n\n            d->color.r', start)
    block = source[start:end]
    program = '''#include <assert.h>
#include <stdbool.h>
#include <math.h>
typedef float Vec3f[3];
struct Vertex { float ob[3]; };
static bool configBetterGraphics, gFullbright;
static float scale = 1;
static int transforms;
static void gfx_local_to_world_space(Vec3f p, Vec3f n) { (void)p; transforms++; for(int i=0;i<3;i++) n[i]*=scale; }
static void vec3f_normalize(Vec3f v) { float x=sqrtf(v[0]*v[0]+v[1]*v[1]+v[2]*v[2]); for(int i=0;i<3;i++) v[i]/=x; }
static void shade(int nx, int ny, int nz, float *result) {
    struct Vertex vertex = {{0,0,0}}, *v = &vertex;
    float r=100,g=100,b=100;
''' + block + '''
    result[0]=r; result[1]=g; result[2]=b;
}
int main(void) {
    float out[3];
    shade(0,127,0,out); assert(out[0]==100 && transforms==0);
    configBetterGraphics=true; gFullbright=true; shade(0,127,0,out); assert(out[0]==100 && transforms==0);
    gFullbright=false; shade(0,127,0,out); assert(out[0]>100 && out[1]>100 && out[2]>100 && transforms==1);
    float up=out[0]; shade(0,-127,0,out); assert(out[0]==100 && up>out[0]);
    scale=0; shade(0,127,0,out); assert(out[0]==100 && isfinite(out[0]));
}
'''
    with tempfile.TemporaryDirectory() as tmp:
        exe=str(Path(tmp)/'test')
        subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-x','c','-','-lm','-o',exe], input=program.encode(),check=True)
        subprocess.run([exe],check=True)
    print(platform, 'optional lighting and defaults: ok')
vr = (ROOT/'VR/src/pc/gfx/gfx_opengl.c').read_text()
assert '(configVrNormalMaps || configBetterGraphics) && texture->has_normal' in vr
assert 'opengl_normal_maps_state = configVrNormalMaps || configBetterGraphics;' in vr
for path in ('WiiU/src/pc/configfile.c','WiiU/src/pc/djui/djui_panel_display.c','WiiU/src/pc/gfx/gfx_pc.c'):
    assert 'configBetterGraphics' not in (ROOT/path).read_text()
workflow=(ROOT/'.github/workflows/build-fork.yml').read_text()
assert 'name: Windows (flat screen and VR)' in workflow and '  pcvr:\n' not in workflow
assert 'python3 fork/apply.py vr game' in workflow and 'Realism64-Windows.zip Realism64' in workflow
assert 'needs.pcvr' not in workflow
assert 'configVrAutoStart                    = false' in (ROOT/'VR/src/pc/configfile.c').read_text()
print('VR normal maps, flat default, unified Windows packaging, console exclusion: ok')
