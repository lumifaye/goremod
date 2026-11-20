/* Host test against the actual fragment and raster paths, not a display mock.
 * Link with --gc-sections so only the CPU rendering code is required. */
#include <assert.h>
#include "../../WiiU/src/pc/gfx/gfx_xbox360.c"
uint8_t gVertexColor[3];
int main(void) {
    struct ShaderProgram shader = {0};
    active = &shader;
    active->f.shader_cmds[3] = SHADER_1;
    viewport(0, 0, W, H); scissor(0, 0, W, H); scale_x = scale_y = 1;
    start(); xbox_font_pass(true);
    // Subpixel triangle at lower right: hits one fine sample, misses the
    // coarse pixel center. Test a cell outside the extent of the depth array
    // at doubled coordinates as well as inclusion in the output.
    float x = 1.f-2.f/W, y = -1.f+2.f/H;
    float tri[] = { x,y,.5,1, x+1.8f/W,y,.5,1, x,y-1.8f/H,.5,1 };
    rasterize(tri,4);
    assert(output_pixel(2*W-2,2*H-2)==0xffffffff);
    assert(output_pixel(2*W-1,2*H-1)==0);
    start(); assert(output_pixel(2*W-2,2*H-2)==0);
    assert(address(-1,4,0)==3 && address(-1,3,0)==2 && address(4,4,1)==3);
    return 0;
}
