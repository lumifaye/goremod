#ifndef GFX_WET_SHEEN_H
#define GFX_WET_SHEEN_H
#include <math.h>
// Approximate a wet specular lobe in vertex lighting; not a scene reflection.
// All inputs are world-space. Return zero for degenerate/non-finite inputs.
static inline float gfx_wet_sheen(const float p[3], const float n[3], const float eye[3]) {
    float v[3] = {eye[0]-p[0], eye[1]-p[1], eye[2]-p[2]};
    float vl = v[0]*v[0]+v[1]*v[1]+v[2]*v[2];
    float nl = n[0]*n[0]+n[1]*n[1]+n[2]*n[2];
    if (!isfinite(vl) || !isfinite(nl) || vl < 1e-8f || nl < 1e-8f) return 0.0f;
    float vi = 1.0f/sqrtf(vl), ni = 1.0f/sqrtf(nl);
    float vx=v[0]*vi, vy=v[1]*vi, vz=v[2]*vi;
    float nx=n[0]*ni, ny=n[1]*ni, nz=n[2]*ni;
    float facing = fmaxf(0.0f, nx*vx + ny*vy + nz*vz);
    if (facing <= 0.0f) return 0.0f;
    float hx=vx-0.35f, hy=vy+0.80f, hz=vz+0.48f;
    float hl=hx*hx+hy*hy+hz*hz;
    float spec=0.0f;
    if (hl > 1e-8f) spec=powf(fmaxf(0.0f,(nx*hx+ny*hy+nz*hz)/sqrtf(hl)), 20.0f);
    float rim=1.0f-fminf(1.0f,facing);
    return fminf(1.0f, 0.75f*spec+0.15f*rim*rim*rim);
}
#endif
