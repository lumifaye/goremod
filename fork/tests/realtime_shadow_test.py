"""Compile and exercise the actual shadow pass with a mock GL API."""
from pathlib import Path
import re, subprocess, tempfile
root = Path(__file__).resolve().parents[2]
header = root/'VR/src/pc/gfx/gfx_shadow_map.h'
source = header.read_text()
constants = sorted(set(re.findall(r'\bGL_[A-Z0-9_]+\b', source)))
definitions = '\n'.join(f'#define {name} {i+1}' for i, name in enumerate(constants))
noops = ['glActiveTexture','glAttachShader','glBindAttribLocation','glBindBuffer',
 'glBindFramebuffer','glBindRenderbuffer','glBindTexture','glClear','glClearColor',
 'glColorMask','glDeleteBuffers','glDeleteFramebuffers','glDeleteProgram','glDeleteRenderbuffers',
 'glDeleteShader','glDeleteTextures','glDepthFunc','glDepthMask','glDisable',
 'glDisableVertexAttribArray','glEnable','glEnableVertexAttribArray','glFramebufferRenderbuffer',
 'glFramebufferTexture2D','glLinkProgram','glRenderbufferStorage','glTexImage2D',
 'glTexParameteri','glUniform3f','glUseProgram','glVertexAttribPointer','glViewport']
macros = '\n'.join('#define '+name+'(...) ((void)0)' for name in noops)
harness = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdint.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>
typedef unsigned GLuint; typedef int GLint; typedef int GLenum; typedef int GLsizei;
typedef unsigned char GLboolean; typedef float GLfloat;
CONSTANTS
MACROS
static int draws, flushes, good_fbo=1, uploads; static size_t upload_bytes;
static void gfx_gl_queue_flush(void) { ++flushes; }
static GLuint menu_target_shader(GLenum t,const char *s) { (void)t; assert(s && strstr(s,"gl_")); return 1; }
#define glCreateProgram() 1u
#define glIsEnabled(...) 1
#define glGetUniformLocation(...) 0
#define glCheckFramebufferStatus(...) (good_fbo ? GL_FRAMEBUFFER_COMPLETE : 0)
#define glBufferData(target,size,data,usage) (uploads++, upload_bytes=(size), (void)(data))
#define glDrawArrays(mode,first,count) (draws += (count))
#define glGenBuffers(n,p) (*(p)=1)
#define glGenTextures(n,p) (*(p)=2)
#define glGenRenderbuffers(n,p) (*(p)=3)
#define glGenFramebuffers(n,p) (*(p)=4)
#define glGetProgramiv(prog,key,p) (*(p)=1)
#define glGetIntegerv(key,p) fake_int((key),(p))
#define glGetBooleanv(key,p) fake_bool((key),(p))
#define glGetFloatv(key,p) fake_float((key),(p))
#define glGetVertexAttribiv(idx,key,p) (*(p)=((key)==GL_VERTEX_ATTRIB_ARRAY_SIZE?3:1))
#define glGetVertexAttribPointerv(idx,key,p) (*(p)=NULL)
static void fake_int(int key,int *p) { if(key==GL_VIEWPORT) {p[0]=5;p[1]=6;p[2]=640;p[3]=480;} else *p=1; }
static void fake_bool(int key,unsigned char *p) { if(key==GL_COLOR_WRITEMASK) memset(p,1,4); else *p=1; }
static void fake_float(int key,float *p) { (void)key; for(int i=0;i<4;i++) p[i]=0; }
#include "gfx_shadow_map.h"
int main(void) {
    float triangles[9]={0,0,0, 1,0,0, 0,1,0}; float center[3]={10,20,30};
    gfx_shadow_map_render(NULL,0,center); assert(!sShadowMap.valid && flushes==1 && draws==0);
    gfx_shadow_map_render(triangles,3,center);
    assert(sShadowMap.valid && draws==3 && uploads==1 && upload_bytes==sizeof(triangles));
    assert(sShadowMap.center[0]==10 && sShadowMap.center[2]==30);
    gfx_shadow_map_render(triangles,3,center); assert(draws==6 && uploads==2);
    gfx_shadow_map_render(NULL,0,center); assert(!sShadowMap.valid);
    gfx_shadow_map_destroy(); assert(!sShadowMap.program && !sShadowMap.framebuffer);
    good_fbo=0; gfx_shadow_map_render(triangles,3,center);
    assert(!sShadowMap.valid && draws==6); gfx_shadow_map_destroy();
}
'''.replace('CONSTANTS',definitions).replace('MACROS',macros)
with tempfile.TemporaryDirectory() as tmp:
    exe=str(Path(tmp)/'test')
    subprocess.run(['cc','-std=c11','-fsanitize=undefined','-I',str(header.parent),'-x','c','-','-o',exe],input=harness.encode(),check=True)
    subprocess.run([exe],check=True)
# The same basis, extent and packed-depth convention must be used in both passes.
shader=(root/'VR/src/pc/gfx/gfx_opengl.c').read_text()
for token in ('-0.35,0.80,0.48','/2400.0','/4000.0','65025.0'):
    assert token in source and token in shader, token
assert 'GL_DEPTH_TEST' in source and 'glFramebufferRenderbuffer' in source
assert 'glDrawArrays(GL_TRIANGLES' in source and 'texture2D(uShadowMap' in shader
pc=(root/'VR/src/pc/gfx/gfx_pc.c').read_text()
assert 'sStereoEye != 1' in pc and 'gfx_opengl_shadow_submit(sShadowVertices' in pc
assert '(rsp.geometry_mode & G_ZBUFFER)' in pc and '(rdp.other_mode_l & Z_UPD)' in pc
assert 'sShadowVertexCount + 3 <= GFX_SHADOW_MAX_VERTICES' in pc
print('Real-time shadow map: mock GPU pass, failure fallback, stereo capture and matching projection: ok')
