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

#endif
