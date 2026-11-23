"""Validate actual generated desktop/GLES shaders using glslangValidator.

Usage: python3 fork/tests/shadow_glsl_validation.py /path/to/glslangValidator
"""
import ast, re, runpy, subprocess, sys, tempfile
from pathlib import Path
root = Path(__file__).resolve().parents[2]
validator = str(Path(sys.argv[1]).resolve())
ctx = runpy.run_path(str(root/'fork/tests/better_graphics_test.py'))
src = ctx['generator_test']
output = 'FILE *fv=fopen("out.vert","w"); fputs(vs_buf,fv); fclose(fv); FILE *ff=fopen("out.frag","w"); fputs(fs_buf,ff); fclose(ff);'
src = '#include <stdlib.h>\n' + src.replace('    (void)num_floats;', '    '+output+'\n    (void)num_floats;')
src = src[:src.rindex('int main(void) {')] + r'''
int main(int argc, char **argv) {
    struct ColorCombiner c={0}; c.cm.flags=(unsigned)atoi(argv[1]);
    c.shader_commands[0]=SHADER_TEXEL0; c.shader_commands[2]=SHADER_INPUT_1;
    c.shader_commands[4]=SHADER_TEXEL0A; c.shader_commands[6]=SHADER_INPUT_1;
    memcpy(c.shader_commands+8,c.shader_commands,8); test(&c); (void)argc;
}'''
shadow = (root/'VR/src/pc/gfx/gfx_shadow_map.h').read_text()
with tempfile.TemporaryDirectory() as tmp:
    for es in (False, True):
        exe = str(Path(tmp)/'gen')
        subprocess.run(['cc','-std=c11','-Wall','-Werror','-I',str(root/'VR/src/pc/gfx'),*(['-DUSE_GLES'] if es else []),'-x','c','-','-o',exe],input=src.encode(),check=True)
        for flags in (0,1,2,16,64,128,256,384,385,511):
            subprocess.run([exe,str(flags)],cwd=tmp,check=True)
            subprocess.run([validator,'-l','out.vert','out.frag'],cwd=tmp,check=True,stdout=subprocess.DEVNULL)
        for name, suffix in (('vs','vert'),('fs','frag')):
            chunk = shadow.split('snprintf('+name+', sizeof('+name+'), "%s"',1)[1].split(',version);',1)[0]
            text = ''.join(ast.literal_eval(s) for s in re.findall(r'"(?:[^"\\]|\\.)*"',chunk))
            (Path(tmp)/('out.'+suffix)).write_text(('#version 100\nprecision highp float;\n' if es else '#version 120\n')+text)
        subprocess.run([validator,'-l','out.vert','out.frag'],cwd=tmp,check=True,stdout=subprocess.DEVNULL)
        print(('GLES' if es else 'Desktop') + ' receiver variants and caster GLSL compile/link: ok')
