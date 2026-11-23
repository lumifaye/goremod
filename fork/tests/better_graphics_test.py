"""Exercise the actual optional lighting block and release/target wiring."""
from pathlib import Path
import subprocess
import tempfile
ROOT = Path(__file__).resolve().parents[2]
for platform in ('PC', 'Android'):
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
vrbase = ROOT/'VR/src/pc'
assert 'configBetterGraphics                 = false;' in (vrbase/'configfile.c').read_text()
assert '"Experimental Better Graphics", &configBetterGraphics' in (vrbase/'djui/djui_panel_display.c').read_text()
vr = (vrbase/'gfx/gfx_opengl.c').read_text()
assert '(configVrNormalMaps || configBetterGraphics) && texture->has_normal' in vr
assert 'opengl_normal_maps_state = configVrNormalMaps || configBetterGraphics;' in vr
for path in ('WiiU/src/pc/configfile.c','WiiU/src/pc/djui/djui_panel_display.c','WiiU/src/pc/gfx/gfx_pc.c'):
    assert 'configBetterGraphics' not in (ROOT/path).read_text()
workflow=(ROOT/'.github/workflows/build-fork.yml').read_text()
assert 'name: Windows (flat screen and VR)' in workflow and '  pcvr:\n' not in workflow
assert 'python3 fork/apply.py vr game' in workflow and 'Realism64-Windows-VR-and-Flatscreen.zip Realism64' in workflow
assert 'needs.pcvr' not in workflow
assert 'configVrAutoStart                    = false' in (ROOT/'VR/src/pc/configfile.c').read_text()
print('VR normal maps, flat default, unified Windows packaging, console exclusion: ok')

# Compile the real shader-string helper and inspect both generated tile paths.
# The richer branch must remain opt-in even when normal maps were already on.
start = vr.index('static void append_line(')
end = vr.index('static const char *shader_item_to_str(', start)
helper = vr[start:end]
test = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
HELPER
int main(void) {
    char buf[16384] = {0}; size_t len = 0;
    append_normal_map_shader(buf, &len, 0, true);
    append_normal_map_shader(buf, &len, 1, false);
    assert(len < sizeof(buf));
    assert(strstr(buf, "if (uNormalMap0)") && strstr(buf, "else if (uNormalMap1)"));
    assert(strstr(buf, "if (uBetterGraphics)") && strstr(buf, "vec3 materialLight"));
    assert(strstr(buf, "texel.rgb *= normalMapRelief") && strstr(buf, "texel.rgb += vec3(normalMapSpecular)"));
    assert(strstr(buf, "- key.z") && strstr(buf, "- fill.z") && strstr(buf, "- bounce.z"));
    assert(!strstr(buf, "texel.a ="));
}
'''.replace('HELPER', helper)
with tempfile.TemporaryDirectory() as tmp:
    exe = str(Path(tmp)/'shader_helper')
    subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-x','c','-','-o',exe], input=test.encode(),check=True)
    subprocess.run([exe],check=True)
assert 'uniform bool uBetterGraphics;' in vr
assert 'opengl_better_graphics_state != configBetterGraphics' in vr
assert 'better_changed && opengl_prg->better_graphics_location >= 0' in vr
assert 'gfx_queue_Uniform1i(new_prg->better_graphics_location, configBetterGraphics ? 1 : 0)' in vr
assert 'if (uVrColorFilter != 3)' in vr
print('Enhanced shader generation, toggle propagation and legacy fallback: ok')

# Exercise the exact normal transform used by the renderer, including cases
# that a regular model-matrix multiplication gets wrong.
normal_test = r'''
#include <assert.h>
#include <math.h>
#include "gfx_enhanced_lighting.h"
int main(void) {
    float m[4][4]={{2,0,0,0},{0,1,0,0},{0,0,1,0},{0,0,0,1}};
    float n[3]={1,1,0}, out[3];
    assert(gfx_enhanced_world_normal(m,n,out));
    assert(fabsf(out[0] - 0.4472136f)<0.0001f && fabsf(out[1] - 0.8944272f)<0.0001f);
    assert(fabsf(out[0]*2.0f - out[1]) < 0.0001f); // perpendicular to transformed tangent
    m[0][0]=-2; assert(gfx_enhanced_world_normal(m,n,out));
    assert(out[0] < 0 && out[1] > 0); // mirrored scale
    m[0][0]=0; assert(!gfx_enhanced_world_normal(m,n,out));
    m[0][0]=NAN; assert(!gfx_enhanced_world_normal(m,n,out));
    m[0][0]=1; n[0]=n[1]=n[2]=0; assert(!gfx_enhanced_world_normal(m,n,out));
    float center[3]={0,0,0}, a[3]={-20000,0,0}, b[3]={20000,0,0}, c[3]={0,20000,0};
    assert(gfx_shadow_triangle_in_range(a,b,c,center,10000));
    a[0]=b[0]=c[0]=10001; assert(!gfx_shadow_triangle_in_range(a,b,c,center,10000));
    a[0]=10000; assert(gfx_shadow_triangle_in_range(a,b,c,center,10000));
}
'''
with tempfile.TemporaryDirectory() as tmp:
    exe = str(Path(tmp)/'normal_test')
    subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-fsanitize=undefined', '-I', str(vrbase/'gfx'),'-x','c','-','-lm','-o',exe], input=normal_test.encode(),check=True)
    subprocess.run([exe],check=True)
pcvr = (vrbase/'gfx/gfx_pc.c').read_text()
assert 'v1->enhanced_normal_valid && v2->enhanced_normal_valid && v3->enhanced_normal_valid' in pcvr
assert '(rsp.geometry_mode & G_LIGHTING) && !(rsp.geometry_mode & G_TEXTURE_GEN)' in pcvr
assert 'attributes < 8' in pcvr
assert 'stereo_cache_entry->enhanced_normal_valid = d->enhanced_normal_valid' in pcvr
assert 'd->enhanced_normal_valid = stereo_cache_entry->enhanced_normal_valid' in pcvr
assert 'buf_vbo[buf_vbo_len++] = v_arr[i]->enhanced_normal[axis] / 127.0f' in pcvr
assert 'attribute vec3 aWorldNormal;' in vr and 'varying mediump vec3 vWorldNormal;' in vr
assert 'glGetAttribLocation(shader_program, "aWorldNormal")' in vr
assert 'texel.rgb *= clamp(lighting' in vr
print('World normals, mirrored/nonuniform scales, stereo and GPU data path: ok')

# Run actual shader source generation for many combiner/flag combinations,
# in desktop GLSL and GLES modes, checking production buffer sizes. This tests
# generation, not GPU shader compilation or rendered appearance.
ccsrc = (vrbase/'gfx/gfx_cc.c').read_text()
features = ccsrc[ccsrc.index('void gfx_cc_get_features('):ccsrc.index('void gfx_cc_print(')]
helpers = vr[vr.index('static void append_str('):vr.index('static struct ShaderProgram *gfx_opengl_create_and_load_new_shader(')]
gen = vr[vr.index('    struct CCFeatures ccf = { 0 };', vr.index('static struct ShaderProgram *gfx_opengl_create_and_load_new_shader(')):vr.index("    vs_buf[vs_len] = '\\0';")]
# Large test storage allows reporting a production-size violation before any overwrite.
gen = gen.replace('char vs_buf[8192];','char vs_buf[65536];').replace('char fs_buf[16384];','char fs_buf[65536];')
generator_test = r'''
#include <assert.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#include "gfx_cc.h"
typedef uint8_t u8;
#define SHADER_FLAG_MAX 8
FEATURES
HELPERS
static void test(struct ColorCombiner *cc) {
GEN
    vs_buf[vs_len]=0; fs_buf[fs_len]=0;
    assert(vs_len < 8192 && fs_len < 16384);
    assert((strstr(vs_buf,"attribute vec3 aShadowWorld;") != NULL) == (bool)cc->cm.shadow_receiver);
    assert((strstr(fs_buf,"uniform sampler2D uShadowMap;") != NULL) == (bool)cc->cm.shadow_receiver);
    assert((strstr(vs_buf,"attribute vec3 aWorldNormal;") != NULL) == (bool)cc->cm.enhanced_lighting);
    assert((strstr(fs_buf,"texel.rgb *= clamp(lighting") != NULL) == (bool)cc->cm.enhanced_lighting);
#ifdef USE_GLES
    assert((strstr(vs_buf,"varying mediump vec3 vWorldNormal;") != NULL) == (bool)cc->cm.enhanced_lighting);
    assert((strstr(fs_buf,"varying mediump vec3 vWorldNormal;") != NULL) == (bool)cc->cm.enhanced_lighting);
#else
    assert((strstr(vs_buf,"varying vec3 vWorldNormal;") != NULL) == (bool)cc->cm.enhanced_lighting);
    assert((strstr(fs_buf,"varying vec3 vWorldNormal;") != NULL) == (bool)cc->cm.enhanced_lighting);
#endif
    (void)num_floats;
}
int main(void) {
    unsigned seed=83741;
    for (unsigned i=0;i<4096;i++) {
        struct ColorCombiner c={0}; c.cm.flags=i%512;
        for (int j=0;j<16;j++) { seed^=seed<<13; seed^=seed>>17; seed^=seed<<5; c.shader_commands[j]=seed % (SHADER_NOISE+1); }
        test(&c);
    }
}
'''.replace('FEATURES',features).replace('HELPERS',helpers).replace('GEN',gen)
with tempfile.TemporaryDirectory() as tmp:
    for mode in ([], ['-DUSE_GLES']):
        exe = str(Path(tmp)/'generate')
        subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-fsanitize=undefined','-I',str(vrbase/'gfx'),*mode,'-x','c','-','-o',exe],input=generator_test.encode(),check=True)
        subprocess.run([exe],check=True)
print('Desktop and GLES source generation: 8192 combiner cases, within buffer limits')
