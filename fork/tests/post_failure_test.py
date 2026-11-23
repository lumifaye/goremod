"""Run the real fullscreen pass with a mock GL driver, including GLES copy failures."""
from pathlib import Path
import re, subprocess, tempfile
root=Path(__file__).resolve().parents[2]
header=(root/'Android/src/pc/gfx/gfx_experimental_post.h').read_text()
names=sorted(set(re.findall(r'\bGL_[A-Z0-9_]+\b',header)))
defs='\n'.join(f'#define {n} {i+1}' for i,n in enumerate(names) if n!='GL_NO_ERROR')+'\n#define GL_NO_ERROR 0\n'
noops=['glAttachShader','glBindAttribLocation','glLinkProgram','glDeleteShader',
       'glTexParameteri','glDeleteProgram','glDeleteTextures','glDeleteBuffers',
       'glShaderSource','glCompileShader','glViewport','glDepthMask','glColorMask',
       'glDisable','glEnable','glUseProgram','glUniform1i','glUniform1f','glUniform2f',
       'glBufferData','glEnableVertexAttribArray','glDisableVertexAttribArray','glVertexAttribPointer']
macros='\n'.join('#define '+x+'(...) ((void)0)' for x in noops)
harness=r'''
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <string.h>
typedef unsigned GLuint; typedef int GLint; typedef unsigned GLenum; typedef unsigned char GLboolean;
typedef float GLfloat;
DEFS
MACROS
static int error, copies, allocations, draws, copyFail, allocFail, active=GL_TEXTURE0+1, bound0=77;
#define glCreateShader(...) 1u
#define glCreateProgram(...) 1u
#define glGetShaderiv(shader,key,p) (*(p)=1)
#define glGetProgramiv(shader,key,p) (*(p)=1)
#define glGenTextures(n,p) (*(p)=2)
#define glGenBuffers(n,p) (*(p)=3)
#define glGetUniformLocation(...) 0
#define glIsEnabled(...) 1
#define glGetVertexAttribiv(i,k,p) (*(p)=((k)==GL_VERTEX_ATTRIB_ARRAY_SIZE ? 2 : 1))
#define glGetVertexAttribPointerv(i,k,p) (*(p)=NULL)
static int geterr(void) {int ret=error; error=0; return ret;}
#define glGetError() geterr()
static void geti(int key,int *p) {
 if (key==GL_SAMPLE_BUFFERS) *p=0;
 else if (key==GL_MAX_TEXTURE_SIZE) *p=4096;
 else if (key==GL_ACTIVE_TEXTURE) *p=active;
 else if (key==GL_TEXTURE_BINDING_2D) *p=bound0;
 else if (key==GL_VIEWPORT) {p[0]=0;p[1]=0;p[2]=640;p[3]=480;}
 else *p=1;
}
#define glGetIntegerv(k,p) geti(k,p)
static void getb(int key,unsigned char *p) { if(key==GL_COLOR_WRITEMASK) memset(p,1,4); else *p=1; }
#define glGetBooleanv(k,p) getb(k,p)
#define glActiveTexture(t) (active=(t))
#define glBindTexture(t,v) (bound0=(v))
#define glBindBuffer(...) ((void)0)
#define glTexImage2D(...) (allocations++, error=allocFail ? 999 : 0)
#define glCopyTexSubImage2D(...) (copies++, error=copyFail ? 999 : 0)
#define glDrawArrays(...) (draws++)
#include "gfx_experimental_post.h"
int main(void) {
    float sun[2]={0.5f,0.5f};
    sExperimentalPost.program=1; sExperimentalPost.texture=2; sExperimentalPost.buffer=3; sExperimentalPost.attempted=true;
    copyFail=1;
    experimental_post_render(640,480,false,0,sun,false);
    assert(draws==0 && copies==1 && bound0==77 && active==GL_TEXTURE0+1);
    assert(sExperimentalPost.failedWidth==640 && sExperimentalPost.failedHeight==480);
    experimental_post_render(640,480,false,0,sun,false);
    assert(draws==0 && copies==1); // no repeated failed copy each frame
    copyFail=0; experimental_post_render(800,600,false,0,sun,false);
    assert(draws==1 && copies==2 && bound0==77 && active==GL_TEXTURE0+1);
    allocFail=1; experimental_post_render(960,540,false,0,sun,false);
    assert(draws==1 && copies==2 && sExperimentalPost.width==0 && bound0==77 && active==GL_TEXTURE0+1);
    allocFail=0; error=999; experimental_post_render(1024,768,false,0,sun,false);
    assert(draws==2 && copies==3); // unrelated old error doesn't disable effect
    return 0;
}
'''.replace('DEFS',defs).replace('MACROS',macros)
with tempfile.TemporaryDirectory() as tmp:
    exe=str(Path(tmp)/'test')
    subprocess.run(['cc','-std=c11','-fsanitize=undefined','-I',str(root/'Android/src/pc/gfx'),'-x','c','-','-o',exe],input=harness.encode(),check=True)
    subprocess.run([exe],check=True)
print('Post effect: copy/allocation failures preserve scene and GL state; resize retry: ok')
