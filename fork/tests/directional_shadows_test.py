"""Exercise the game's actual projected-contact-shadow code with mocked floors."""
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
src = (root/'VR/src/game/shadow.c').read_text()
shadow = src[src.index('struct Shadow {'):src.index('\n};', src.index('struct Shadow {'))+3]
projection = src[src.index('static void project_directional_shadow('):src.index('\n/**\n * Initialize a shadow.')]
init = src[src.index('s8 init_shadow('):src.index('\n/**\n * Given a `vertexNum`', src.index('s8 init_shadow('))]
extrap = src[src.index('f32 extrapolate_vertex_y_position('):src.index('\n/**\n * Given a shadow vertex', src.index('f32 extrapolate_vertex_y_position('))]
coords = src[src.index('void get_vertex_coords('):src.index('\n/**\n * Given a vertex\'s location', src.index('void get_vertex_coords('))]
program = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <math.h>
#define M_PI 3.14159265358979323846
#define SHADOW_WITH_9_VERTS 0
#define SHADOW_WITH_4_VERTS 1
#define SURFACE_BURNING 1
#define TRUE 1
typedef float f32; typedef int8_t s8; typedef int16_t s16; typedef uint8_t u8;
struct FloorGeometry { f32 normalX, normalY, normalZ, originOffset; };
struct { f32 floorLowerLimitShadow; } gLevelValues = {-10000};
static bool configBetterGraphics, gShadowAboveWaterOrLava, gMarioOnIceOrCarpet, sMarioOnFlyingCarpet;
static int sSurfaceTypeBelowShadow;
static void *gEnvironmentRegions;
static struct FloorGeometry floorGeo = {0,1,0,0};
static int queries, missing; static float receiverHeight;
static f32 find_floor_height_and_data(f32 x, f32 y, f32 z, struct FloorGeometry **floor) {
    (void)x; (void)y; (void)z; queries++;
    if (missing && queries > 1) { *floor = NULL; return -11000; }
    *floor = &floorGeo; return queries > 1 ? receiverHeight : 0;
}
#define find_floor_height_and_data 0.4f + find_floor_height_and_data
SHADOW
static f32 get_water_level_below_shadow(struct Shadow *s) { (void)s; return 0; }
static f32 find_water_level(f32 x, f32 z) { (void)x; (void)z; return 50; }
static u8 dim_shadow_with_distance(u8 s, f32 h) { (void)h; return s; }
static f32 scale_shadow_with_distance(f32 s, f32 h) { (void)h; return s; }
static f32 atan2_deg(f32 a, f32 b) { return atan2f(a,b)*180.0f/(float)M_PI; }
PROJECTION
INIT
EXTRAP
COORDS
int main(void) {
    struct Shadow s = {0}; float x,y,z;
    queries=0; configBetterGraphics=false;
    assert(init_shadow(&s, 10, 100, 20, 100, 180)==0);
    assert(queries==1 && !s.directional && s.centerX==10 && s.centerZ==20);
    queries=0; configBetterGraphics=true;
    assert(init_shadow(&s, 10, 100, 20, 100, 180)==0);
    assert(queries==2 && s.directional && s.solidity==180);
    assert(fabsf(s.centerX-(10+99.6f*0.35f/0.8f)) < 0.001f);
    assert(fabsf(s.centerZ-(20-99.6f*0.48f/0.8f)) < 0.001f);
    calculate_vertex_xyz(4,s,&x,&y,&z,SHADOW_WITH_9_VERTS);
    assert(fabsf(x-s.centerX)<0.001f && fabsf(z-s.centerZ)<0.001f);
    assert(fabsf((x-s.parentX)-(s.centerX-10))<0.001f); // draw matrix stays at caster
    queries=0; missing=1; assert(init_shadow(&s,10,100,20,100,180)==0);
    assert(!s.directional && s.centerX==10 && s.centerZ==20);
    missing=0; queries=0; receiverHeight=100; assert(init_shadow(&s,10,100,20,100,180)==0);
    assert(!s.directional); // discontinuous receiver: keep vanilla shadow
    receiverHeight=0; queries=0; gEnvironmentRegions = &floorGeo;
    assert(init_shadow(&s,10,100,20,100,180)==0 && !s.directional); // projected receiver lies under water
    gEnvironmentRegions = NULL; queries=0; sSurfaceTypeBelowShadow=SURFACE_BURNING;
    assert(init_shadow(&s,10,100,20,100,180)==0 && queries==1 && !s.directional);
    sSurfaceTypeBelowShadow=0; queries=0; gMarioOnIceOrCarpet=true;
    assert(init_shadow(&s,10,100,20,100,180)==0 && queries==1 && !s.directional);
    gMarioOnIceOrCarpet=false; queries=0;
    assert(init_shadow(&s,10,1000,20,100,180)==0 && queries==1 && !s.directional);
}
'''.replace('SHADOW\n',shadow+'\n').replace('PROJECTION\n',projection+'\n').replace('INIT\n',init+'\n').replace('EXTRAP\n',extrap+'\n').replace('COORDS\n',coords+'\n')
with tempfile.TemporaryDirectory() as tmp:
    exe = str(Path(tmp)/'shadow')
    subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-fsanitize=undefined','-x','c','-','-lm','-o',exe],input=program.encode(),check=True)
    subprocess.run([exe],check=True)
assert 's.directional ? s.solidity : 200' in src
assert 'gInterpolatingSurfaces = true;' in (root/'VR/src/game/rendering_graph_node.c').read_text()
for platform in ('PC','Android','WiiU'):
    assert 'project_directional_shadow' not in (root/platform/'src/game/shadow.c').read_text()
print('Projected contact shadows: movement, offset, legacy fallback and receiver safety passed')
