"""Exercise real light-space snapping, edge fade and player metal gating."""
from pathlib import Path
import subprocess, tempfile
root=Path(__file__).resolve().parents[2]
for platform in ('PC','Android','VR'):
    base=root/platform/'src/pc/gfx'
    header=base/('gfx_enhanced_lighting.h' if platform=='VR' else 'gfx_shadow_range.h')
    source=(base/'gfx_pc.c').read_text()
    shader=(base/'gfx_opengl.c').read_text()
    assert 'gfx_shadow_stable_center(gLakituState.focus,sShadowCaptureCenter)' in source
    assert 'shadowFade=smoothstep(0.001,0.035,shadowEdge)*smoothstep(0.0,0.025' in shader
    assert 'mix(0.75,1.0,visibility/9.0),shadowFade' in shader
    assert 'configBetterGraphics && configBetterGraphicsSheen && sPlayerSheen && !gFullbright && sHasInverseCameraMatrix' in source
    assert '(rsp.geometry_mode & G_TEXTURE_GEN)) {' in source and 'float glint = gfx_wet_sheen(metalPos,metalNormal,gLakituState.pos)' in source
    code='''#include <assert.h>\n#include <math.h>\n#include "'''+header.name+'''"\nint main(void) {
    float p[3]={0,0,0}, small[3]={0.1f,0.1f,0.1f}, moved[3]={12,0,0};
    float a[3],b[3],c[3]; gfx_shadow_stable_center(p,a); gfx_shadow_stable_center(small,b); gfx_shadow_stable_center(moved,c);
    for(int i=0;i<3;i++) assert(fabsf(a[i]-b[i])<0.001f);
    assert(fabsf(c[0]-a[0])+fabsf(c[1]-a[1])+fabsf(c[2]-a[2])>1.0f);
    p[0]=NAN; gfx_shadow_stable_center(p,a); for(int i=0;i<3;i++) assert(isfinite(a[i]));
    return 0;
}
'''
    with tempfile.TemporaryDirectory() as tmp:
        exe=str(Path(tmp)/'test')
        subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-fsanitize=undefined','-I',str(base),'-x','c','-','-lm','-o',exe],input=code.encode(),check=True)
        subprocess.run([exe],check=True)
    print(platform, 'shadow stabilization and player-metal gating: ok')
