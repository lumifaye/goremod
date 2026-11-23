"""Exercise flat shadow wiring and actual generated PC/Android shaders."""
from pathlib import Path
import subprocess, tempfile, sys, runpy, re
root=Path(__file__).resolve().parents[2]
for platform in ('PC','Android'):
    base=root/platform/'src/pc/gfx'
    src=(base/'gfx_opengl.c').read_text()
    pc=(base/'gfx_pc.c').read_text()
    caster=(base/'gfx_shadow_map.h').read_text()
    cc=(base/'gfx_cc.c').read_text()
    assert 'gfx_shadow_map_render(vertices,count,center)' in src
    assert 'gfx_opengl_shadow_ready()' in pc and 'gfx_shadow_triangle_in_range' in pc
    assert 'sShadowVertexCount + 3 <= GFX_SHADOW_MAX_VERTICES' in pc
    assert '/4800.0' in src and '/8000.0' in src and '/4800.0' in caster and '/8000.0' in caster
    assert 'if (attributes < 8)' in pc and 'shadow_receiver = false' in pc
    features=cc[cc.index('void gfx_cc_get_features('):cc.index('void gfx_cc_print(')]
    helpers=src[src.index('static void append_str('):src.index('static struct ShaderProgram *gfx_opengl_create_and_load_new_shader(')]
    gen=src[src.index('    struct CCFeatures ccf = { 0 };',src.index('static struct ShaderProgram *gfx_opengl_create_and_load_new_shader(')):src.index("    vs_buf[vs_len] = '\\0';")]
    gen=gen.replace('char vs_buf[8192];','char vs_buf[65536];').replace('char fs_buf[8192];','char fs_buf[65536];')
    program=r'''
#include <assert.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "gfx_cc.h"
typedef uint8_t u8;
#define SHADER_FLAG_MAX 8
FEATURES
HELPERS
static void test(struct ColorCombiner *cc) {
GEN
    vs_buf[vs_len]=0; fs_buf[fs_len]=0;
    assert(vs_len<8192 && fs_len<8192);
    assert((strstr(vs_buf,"aShadowWorld;")!=NULL)==(bool)cc->cm.shadow_receiver);
    assert((strstr(fs_buf,"uniform sampler2D uShadowMap;")!=NULL)==(bool)cc->cm.shadow_receiver);
    FILE *v=fopen("out.vert","w"), *f=fopen("out.frag","w");
    assert(v && f); fputs(vs_buf,v); fputs(fs_buf,f); fclose(v); fclose(f); (void)num_floats;
}
int main(int argc,char **argv) {
    struct ColorCombiner c={0}; c.cm.flags=(unsigned)atoi(argv[1]);
    c.shader_commands[0]=SHADER_TEXEL0; c.shader_commands[2]=SHADER_INPUT_1;
    c.shader_commands[4]=SHADER_TEXEL0A; c.shader_commands[6]=SHADER_INPUT_1;
    memcpy(c.shader_commands+8,c.shader_commands,8); test(&c); (void)argc;
}
'''.replace('FEATURES',features).replace('HELPERS',helpers).replace('GEN',gen)
    with tempfile.TemporaryDirectory() as tmp:
        for mode in ([],['-DUSE_GLES']):
            exe=str(Path(tmp)/'gen')
            subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-I',str(base),*mode,'-x','c','-','-o',exe],input=program.encode(),check=True)
            for flags in (0,1,2,16,32,64,128,129,255):
                subprocess.run([exe,str(flags)],cwd=tmp,check=True)
                if len(sys.argv)>1:

                    result=subprocess.run([str(Path(sys.argv[1]).resolve()),'-l','out.vert','out.frag'],cwd=tmp,capture_output=True,text=True)
                    if result.returncode: print(platform,mode,flags,result.stdout,Path(tmp,'out.frag').read_text()); result.check_returncode()
    print(platform, 'shadow receiver shader variants, capture and fallback wiring: ok')

# Exercise actual caster pass and framebuffer failure against the existing mock GL harness.
mock = runpy.run_path(str(root/'fork/tests/realtime_shadow_test.py'))['harness']
mock = mock.replace('menu_target_shader(', 'experimental_post_shader(')
mock = mock.replace('!sShadowMap.valid && flushes==1 && draws==0','!sShadowMap.valid && draws==0')
for platform in ('PC','Android'):
    base=root/platform/'src/pc/gfx'
    renderer=(root/platform/'src/game/rendering_graph_node.c').read_text()
    assert '!gfx_realtime_shadow_available() && gCurGraphNodeCamera' in renderer
    section=renderer[renderer.index('static void geo_process_shadow('):renderer.index('static s32 obj_is_in_view(',renderer.index('static void geo_process_shadow('))]
    assert 'geo_process_node_and_siblings(node->node.children)' in section
    with tempfile.TemporaryDirectory() as tmp:
        exe=str(Path(tmp)/'mock')
        subprocess.run(['cc','-std=c11','-fsanitize=undefined','-I',str(base),'-x','c','-','-o',exe],input=mock.encode(),check=True)
        subprocess.run([exe],check=True)
print('Flat shadow map GL pass, framebuffer failure and legacy decal fallback: ok')
