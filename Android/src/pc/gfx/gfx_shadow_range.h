#ifndef GFX_SHADOW_RANGE_H
#define GFX_SHADOW_RANGE_H
#include <stdbool.h>
#include <math.h>
// Conservative caster filtering: keep a triangle if its bounding box can
// intersect the capture volume, including very large level polygons whose
// vertices are all outside but whose interior crosses the volume.
static inline bool gfx_shadow_triangle_in_range(const float a[3], const float b[3],
                                                const float c[3], const float center[3], float radius) {
    for (int axis = 0; axis < 3; ++axis) {
        float low = center[axis] - radius, high = center[axis] + radius;
        if ((a[axis] < low && b[axis] < low && c[axis] < low) ||
            (a[axis] > high && b[axis] > high && c[axis] > high)) return false;
    }
    return true;
}
// Anchor the directional shadow map to its own texel grid, not the moving
// camera. This reduces shimmering from sub-texel camera movement. The caster
// and receiver share the same snapped center captured for the previous frame.
static inline void gfx_shadow_stable_center(const float focus[3], float out[3]) {
    const float invL = 1.0f / sqrtf(0.35f*0.35f + 0.80f*0.80f + 0.48f*0.48f);
    const float invR = 1.0f / sqrtf(0.35f*0.35f + 0.48f*0.48f);
    const float l[3] = {-0.35f*invL, 0.80f*invL, 0.48f*invL};
    const float r[3] = {0.48f*invR, 0.0f, 0.35f*invR};
    const float u[3] = {l[1]*r[2]-l[2]*r[1], l[2]*r[0]-l[0]*r[2], l[0]*r[1]-l[1]*r[0]};
    const float step = 9600.0f / 2048.0f;
    if (!isfinite(focus[0]) || !isfinite(focus[1]) || !isfinite(focus[2])) {
        out[0]=out[1]=out[2]=0.0f; return;
    }
    float cr=0.0f, cu=0.0f, cl=0.0f;
    for (int i=0; i<3; ++i) { cr+=focus[i]*r[i]; cu+=focus[i]*u[i]; cl+=focus[i]*l[i]; }
    cr=roundf(cr/step)*step; cu=roundf(cu/step)*step; cl=roundf(cl/step)*step;
    for (int i=0; i<3; ++i) out[i]=cr*r[i]+cu*u[i]+cl*l[i];
}
#endif
