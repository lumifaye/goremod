#ifndef GFX_ENHANCED_LIGHTING_H
#define GFX_ENHANCED_LIGHTING_H

#include <math.h>
#include <stdbool.h>

// Transform a normal by the inverse transpose of the model's linear part.
// Cofactors avoid inverting the full 4x4 matrix; preserve orientation for
// mirrored models and reject singular / non-finite scales rather than NaNs.
static inline bool gfx_enhanced_world_normal(const float m[4][4], const float n[3], float out[3]) {
    float c0[3] = {m[1][1]*m[2][2]-m[1][2]*m[2][1], m[1][2]*m[2][0]-m[1][0]*m[2][2], m[1][0]*m[2][1]-m[1][1]*m[2][0]};
    float c1[3] = {m[2][1]*m[0][2]-m[2][2]*m[0][1], m[2][2]*m[0][0]-m[2][0]*m[0][2], m[2][0]*m[0][1]-m[2][1]*m[0][0]};
    float c2[3] = {m[0][1]*m[1][2]-m[0][2]*m[1][1], m[0][2]*m[1][0]-m[0][0]*m[1][2], m[0][0]*m[1][1]-m[0][1]*m[1][0]};
    float det = m[0][0]*c0[0] + m[0][1]*c0[1] + m[0][2]*c0[2];
    if (!isfinite(det) || fabsf(det) < 1e-12f) return false;
    for (int i = 0; i < 3; ++i) out[i] = (n[0]*c0[i] + n[1]*c1[i] + n[2]*c2[i]) * (det < 0 ? -1.0f : 1.0f);
    float length2 = out[0]*out[0] + out[1]*out[1] + out[2]*out[2];
    if (!isfinite(length2) || length2 < 1e-12f) return false;
    float inv = 1.0f / sqrtf(length2);
    for (int i = 0; i < 3; ++i) out[i] *= inv;
    return true;
}
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
