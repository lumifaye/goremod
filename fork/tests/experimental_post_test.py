"""Check post-process target wiring and optionally compile its actual GLSL."""
from pathlib import Path
import ast, re, subprocess, sys, tempfile
root = Path(__file__).resolve().parents[2]
headers = [(root / p / 'src/pc/gfx/gfx_experimental_post.h').read_text() for p in ('PC','Android','VR')]
assert headers[0] == headers[1] == headers[2]
h = headers[0]
for p in ('PC','Android','VR'):
    source = (root/p/'src/pc/gfx/gfx_pc.c').read_text()
    assert '!dropped_frame && configBetterGraphics && gfx_rapi == &gfx_opengl_api' in source
    assert 'find_water_level(eye[0], eye[2])' in source
    assert source.index('gfx_rapi->end_frame();', source.index('void gfx_end_frame_render')) < source.index('gfx_opengl_experimental_post(', source.index('void gfx_end_frame_render'))
assert '&& !vr_is_active()' in (root/'VR/src/pc/gfx/gfx_pc.c').read_text()
assert 'if (samples || width>maxTexture || height>maxTexture || !experimental_post_init()) return;' in h
assert 'glGetVertexAttribPointerv' in h and 'glVertexAttribPointer(0,size,type,normalized,stride,pointer)' in h
assert 'glColorMask(colors[0],colors[1],colors[2],colors[3])' in h
assert 'underwater*vec2(sin(' in h and 'vec3 glow=bright(' in h
if len(sys.argv) > 1:
    validator=str(Path(sys.argv[1]).resolve())
    getstrings=lambda s: ''.join(ast.literal_eval(x) for x in re.findall(r'"(?:[^"\\]|\\.)*"',s))
    for es in (False,True):
        # Select the branch as the C preprocessor does; adjacent C strings form one shader.
        branch=h.split('#if defined(USE_GLES) || defined(__ANDROID__)',1)[1].split('#endif',1)[0]
        chosen=branch.split('#else')[0 if es else 1]
        vs=getstrings(chosen.split('const char *vs =',1)[1].split(';\n',1)[0])
        fs_prefix=getstrings(chosen.split('const char *fs =',1)[1])
        tail=h.split('#endif\n',1)[1].split(';\n    GLuint v=',1)[0]
        fs=fs_prefix+getstrings(tail)
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp,'post.vert').write_text(vs)
            Path(tmp,'post.frag').write_text(fs)
            subprocess.run([validator,'-l','post.vert','post.frag'],cwd=tmp,check=True,stdout=subprocess.DEVNULL)
        print(('GLES' if es else 'desktop')+' post shader compile/link: ok')
print('Post-processing gating, target fallback, state restoration and water wiring: ok')
